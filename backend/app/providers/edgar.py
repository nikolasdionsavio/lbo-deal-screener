"""SecEdgarProvider: fundamentals from SEC EDGAR companyfacts (spec §5).

- Ticker -> CIK via https://www.sec.gov/files/company_tickers.json, cached
  in memory and on disk under backend/data/cache/.
- Fundamentals via https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json.
- Annual fact selection: ``form == "10-K"`` and ``fp == "FY"``; duration facts
  must span a roughly annual period (10-K filings also contain quarterly
  periods); values are deduped by ``end`` date preferring the latest ``filed``
  (so restatements in later filings win). Fiscal year label = calendar year of
  the period end date.
- Missing tags -> field None + warning "<field> unavailable from SEC EDGAR".
- All HTTP: 15s timeout, errors mapped to ProviderError with readable messages.
"""

from __future__ import annotations

import json
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from app.normalization import normalize_financials
from app.providers.base import DataProvider
from app.providers.exceptions import (
    CompanyNotFoundError,
    ProviderConfigError,
    ProviderError,
)
from app.schemas.company import CompanyDataBundle, CompanyInfo, SearchResult
from app.schemas.financials import FiscalYearFinancials

_BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CACHE_DIR = _BACKEND_DIR / "data" / "cache"
TICKER_MAP_CACHE_FILENAME = "company_tickers.json"

TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

TIMEOUT_SECONDS = 15.0
_MIN_ANNUAL_PERIOD_DAYS = 300  # excludes quarterly periods reported inside 10-Ks
_MAX_YEARS = 5
_MAX_SEARCH_RESULTS = 20

# us-gaap tag preference lists per spec §5 — first tag with annual data wins.
TAG_PREFERENCES: dict[str, list[str]] = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ],
    "cost_of_revenue": [
        "CostOfRevenue",
        "CostOfGoodsAndServicesSold",
        "CostOfGoodsSold",
    ],
    "operating_income": ["OperatingIncomeLoss"],
    "depreciation_amortization": [
        "DepreciationDepletionAndAmortization",
        "DepreciationAmortizationAndAccretionNet",
        "DepreciationAndAmortization",
    ],
    "net_income": ["NetIncomeLoss"],
    "interest_expense": [
        "InterestExpense",
        "InterestExpenseDebt",
        "InterestIncomeExpenseNet",  # taken as absolute value
    ],
    "tax_expense": ["IncomeTaxExpenseBenefit"],
    "operating_cash_flow": [
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    ],
    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
    ],
    "cash_and_equivalents": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    ],
    "current_assets": ["AssetsCurrent"],
    "current_liabilities": ["LiabilitiesCurrent"],
    "total_equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
}
_ABS_VALUE_TAGS = {"InterestIncomeExpenseNet"}

# total_debt (spec §5): LongTermDebtNoncurrent + a current component, where the
# current component is DebtCurrent when present, ELSE LongTermDebtCurrent +
# ShortTermBorrowings — DebtCurrent already includes the other two for filers
# that report both, so summing all tags would double-count.
TOTAL_DEBT_NONCURRENT_TAG = "LongTermDebtNoncurrent"
TOTAL_DEBT_CURRENT_TAG = "DebtCurrent"
TOTAL_DEBT_CURRENT_COMPONENT_TAGS = ["LongTermDebtCurrent", "ShortTermBorrowings"]
TOTAL_DEBT_FALLBACK_TAG = "LongTermDebt"
SHARES_TAG = "EntityCommonStockSharesOutstanding"  # dei taxonomy, latest value


def _select_annual_values(tag_payload: dict[str, Any], tag: str) -> dict[str, float]:
    """Return {period_end: value} for 10-K FY facts, deduped preferring latest filed."""
    entries = tag_payload.get("units", {}).get("USD", [])
    best: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if entry.get("form") != "10-K" or entry.get("fp") != "FY":
            continue
        end = entry.get("end")
        val = entry.get("val")
        if not end or val is None:
            continue
        start = entry.get("start")
        if start:
            try:
                span = (date.fromisoformat(end) - date.fromisoformat(start)).days
            except ValueError:
                continue
            if span < _MIN_ANNUAL_PERIOD_DAYS:
                continue
        current = best.get(end)
        if current is None or str(entry.get("filed") or "") > str(current.get("filed") or ""):
            best[end] = entry
    values = {end: float(entry["val"]) for end, entry in best.items()}
    if tag in _ABS_VALUE_TAGS:
        values = {end: abs(v) for end, v in values.items()}
    return values


class SecEdgarProvider(DataProvider):
    name = "sec_edgar"

    def __init__(
        self,
        user_agent: str,
        *,
        client: httpx.Client | None = None,
        cache_dir: Path | str | None = None,
    ) -> None:
        if not user_agent or not user_agent.strip():
            raise ProviderConfigError(
                "SEC_EDGAR_USER_AGENT is required for SEC EDGAR requests "
                "(e.g. 'Your Name your.email@example.com')."
            )
        self.user_agent = user_agent.strip()
        self._client = client or httpx.Client(timeout=TIMEOUT_SECONDS)
        self._cache_dir = Path(cache_dir) if cache_dir is not None else DEFAULT_CACHE_DIR
        self._ticker_map_mem: dict[str, Any] | None = None

    # ----- HTTP -----

    def _request_json(self, url: str, *, what: str) -> Any:
        headers = {"User-Agent": self.user_agent}
        # SEC rate-limits aggressively by IP (shared cloud egress IPs especially);
        # 429s are usually transient, so retry briefly before failing.
        attempts = 3
        for attempt in range(1, attempts + 1):
            try:
                response = self._client.get(url, headers=headers, timeout=TIMEOUT_SECONDS)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status == 404:
                    raise CompanyNotFoundError(
                        f"{what}: not found on SEC EDGAR (HTTP 404)."
                    ) from exc
                if status == 429 and attempt < attempts:
                    time.sleep(attempt * 2.0)
                    continue
                if status == 429:
                    raise ProviderError(
                        f"{what} failed: SEC EDGAR is rate limiting requests "
                        "(HTTP 429). Try again in a minute."
                    ) from exc
                raise ProviderError(
                    f"{what} failed: SEC EDGAR returned HTTP {status}."
                ) from exc
            except httpx.HTTPError as exc:
                raise ProviderError(
                    f"{what} failed: could not reach SEC EDGAR "
                    f"({exc.__class__.__name__})."
                ) from exc
            except ValueError as exc:
                raise ProviderError(
                    f"{what} failed: SEC EDGAR returned invalid JSON."
                ) from exc
        raise ProviderError(f"{what} failed: SEC EDGAR retries exhausted.")

    # ----- ticker -> CIK map (memory + disk cache) -----

    def _ticker_map(self) -> dict[str, Any]:
        if self._ticker_map_mem is not None:
            return self._ticker_map_mem
        cache_file = self._cache_dir / TICKER_MAP_CACHE_FILENAME
        if cache_file.is_file():
            try:
                self._ticker_map_mem = json.loads(cache_file.read_text(encoding="utf-8"))
                return self._ticker_map_mem
            except (ValueError, OSError):
                pass  # corrupt/unreadable cache -> refetch
        data = self._request_json(TICKER_MAP_URL, what="SEC EDGAR ticker list")
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps(data), encoding="utf-8")
        except OSError:
            pass  # disk cache is best-effort
        self._ticker_map_mem = data
        return data

    def _resolve_cik(self, ticker: str) -> tuple[int, str]:
        wanted = ticker.strip().upper()
        for record in self._ticker_map().values():
            if str(record.get("ticker", "")).upper() == wanted:
                return int(record["cik_str"]), str(record.get("title", wanted))
        raise CompanyNotFoundError(
            f"Ticker '{ticker}' not found in the SEC EDGAR company list."
        )

    # ----- DataProvider interface -----

    def search(self, query: str) -> list[SearchResult]:
        q = query.strip().lower()
        if not q:
            return []
        results: list[SearchResult] = []
        for record in self._ticker_map().values():
            ticker = str(record.get("ticker", ""))
            title = str(record.get("title", ""))
            if q in ticker.lower() or q in title.lower():
                results.append(
                    SearchResult(ticker=ticker, name=title, exchange=None, source=self.name)
                )
                if len(results) >= _MAX_SEARCH_RESULTS:
                    break
        return results

    def get_company(self, ticker: str) -> CompanyDataBundle:
        cik, title = self._resolve_cik(ticker)
        facts_doc = self._request_json(
            COMPANYFACTS_URL.format(cik=cik),
            what=f"SEC EDGAR company facts for {ticker.upper()}",
        )
        gaap = facts_doc.get("facts", {}).get("us-gaap", {})
        warnings: list[str] = []

        field_maps: dict[str, dict[str, float]] = {}
        for field, tags in TAG_PREFERENCES.items():
            values: dict[str, float] = {}
            for tag in tags:
                payload = gaap.get(tag)
                if not payload:
                    continue
                values = _select_annual_values(payload, tag)
                if values:
                    break
            if not values:
                warnings.append(f"{field} unavailable from SEC EDGAR")
            field_maps[field] = values

        field_maps["total_debt"] = self._total_debt_values(gaap, warnings)

        rows_by_year: dict[int, FiscalYearFinancials] = {}
        all_ends = sorted({end for values in field_maps.values() for end in values})
        for end in all_ends:  # ascending: a later end wins a same-year collision
            fiscal_year = int(end[:4])
            row = FiscalYearFinancials(fiscal_year=fiscal_year, period_end=end)
            for field, values in field_maps.items():
                if end in values:
                    setattr(row, field, values[end])
            rows_by_year[fiscal_year] = row
        years = [rows_by_year[fy] for fy in sorted(rows_by_year)][-_MAX_YEARS:]

        shares = self._latest_shares(facts_doc)
        if shares is None:
            warnings.append("shares_outstanding unavailable from SEC EDGAR")
        elif years:
            years[-1].shares_outstanding = shares

        normalize_financials(years)
        if not years:
            warnings.append("No annual 10-K facts found on SEC EDGAR for this company.")

        info = CompanyInfo(
            ticker=ticker.strip().upper(),
            name=str(facts_doc.get("entityName") or title),
            cik=f"{cik:010d}",
            # sector/industry/exchange are not in companyfacts; the composite
            # live provider fills them from FMP when available.
        )
        return CompanyDataBundle(
            info=info,
            market=None,
            financials=years,
            data_source="SEC EDGAR",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            warnings=warnings,
        )

    # ----- field helpers -----

    def _total_debt_values(
        self, gaap: dict[str, Any], warnings: list[str]
    ) -> dict[str, float]:
        """Per-period total debt with the §5 non-double-counting current rule."""

        def _values(tag: str) -> dict[str, float]:
            payload = gaap.get(tag)
            return _select_annual_values(payload, tag) if payload else {}

        noncurrent = _values(TOTAL_DEBT_NONCURRENT_TAG)
        debt_current = _values(TOTAL_DEBT_CURRENT_TAG)
        current_components = [_values(tag) for tag in TOTAL_DEBT_CURRENT_COMPONENT_TAGS]

        ends = set(noncurrent) | set(debt_current)
        ends.update(end for values in current_components for end in values)
        if ends:
            totals: dict[str, float] = {}
            for end in ends:
                parts: list[float] = []
                if end in noncurrent:
                    parts.append(noncurrent[end])
                if end in debt_current:
                    # DebtCurrent supersedes LongTermDebtCurrent + ShortTermBorrowings.
                    parts.append(debt_current[end])
                else:
                    parts.extend(m[end] for m in current_components if end in m)
                totals[end] = sum(parts)
            return totals

        fallback = gaap.get(TOTAL_DEBT_FALLBACK_TAG)
        if fallback:
            values = _select_annual_values(fallback, TOTAL_DEBT_FALLBACK_TAG)
            if values:
                return values
        warnings.append("total_debt unavailable from SEC EDGAR")
        return {}

    @staticmethod
    def _latest_shares(facts_doc: dict[str, Any]) -> float | None:
        payload = facts_doc.get("facts", {}).get("dei", {}).get(SHARES_TAG, {})
        entries = payload.get("units", {}).get("shares", [])
        latest: dict[str, Any] | None = None
        for entry in entries:
            if entry.get("val") is None or not entry.get("end"):
                continue
            if latest is None or str(entry["end"]) > str(latest["end"]):
                latest = entry
        return float(latest["val"]) if latest else None
