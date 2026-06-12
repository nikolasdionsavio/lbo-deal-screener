"""SecEdgarProvider: fundamentals from SEC EDGAR companyfacts (spec §5).

- Ticker -> CIK via https://www.sec.gov/files/company_tickers.json, cached
  in memory and on disk under backend/data/cache/.
- Fundamentals via https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json.
- Annual fact selection: ``form`` in ANNUAL_FORMS (10-K, 20-F, 40-F and their
  amendments — foreign private issuers file 20-F/40-F, never 10-K) and
  ``fp == "FY"``; duration facts must span a roughly annual period (annual
  filings also contain quarterly periods); values are deduped by ``end`` date
  preferring the latest ``filed`` (so restatements in later filings win).
  Interim forms (10-Q, 6-K) are always excluded. Fiscal year label = calendar
  year of the period end date.
- Taxonomies: each tag resolves from ``us-gaap`` first, then ``ifrs-full``
  (foreign private issuers report under IFRS). The per-field preference lists
  put every us-gaap tag before the IFRS ones, so US filers are unaffected.
- Units: per tag, prefer "USD"; else the single monetary unit present; else
  the monetary unit with the most annual periods (with a warning). The bundle
  reporting currency is the dominant unit across populated fields; fields
  reported in a non-dominant unit are dropped with a warning (no FX
  conversion in the MVP).
- Missing tags -> field None + warning "<field> unavailable from SEC EDGAR".
- All HTTP: 15s timeout, errors mapped to ProviderError with readable messages.
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter
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
_MIN_ANNUAL_PERIOD_DAYS = 300  # excludes quarterly periods reported inside annual filings
_MAX_YEARS = 5
_MAX_SEARCH_RESULTS = 20

# Annual-report forms (plus amendments). Foreign private issuers file 20-F
# (IFRS) or 40-F (Canadian MJDS) instead of 10-K. Interim forms (10-Q, 6-K)
# are never accepted.
ANNUAL_FORMS = {"10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A"}

# Monetary units in companyfacts are plain ISO currency codes ("USD", "EUR");
# non-monetary units ("shares", "USD/shares", "pure") never carry financials.
_MONETARY_UNIT_RE = re.compile(r"^[A-Z]{3}$")

# Tag preference lists per spec §5 — merged per period, earlier tags win.
# Each tag resolves from us-gaap first, then ifrs-full; the IFRS tags are
# listed AFTER every us-gaap tag so US filers are unaffected.
TAG_PREFERENCES: dict[str, list[str]] = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        # IFRS
        "Revenue",
        "RevenueFromContractsWithCustomers",
    ],
    "cost_of_revenue": [
        "CostOfRevenue",
        "CostOfGoodsAndServicesSold",
        "CostOfGoodsSold",
        # IFRS
        "CostOfSales",
    ],
    "gross_profit": ["GrossProfit"],  # same tag name in us-gaap and ifrs-full
    "operating_income": [
        "OperatingIncomeLoss",
        # IFRS
        "ProfitLossFromOperatingActivities",
    ],
    "depreciation_amortization": [
        "DepreciationDepletionAndAmortization",
        "DepreciationAmortizationAndAccretionNet",
        "DepreciationAndAmortization",
        # IFRS
        "DepreciationAndAmortisationExpense",
        "AdjustmentsForDepreciationAndAmortisationExpense",
    ],
    "net_income": [
        "NetIncomeLoss",
        # IFRS
        "ProfitLossAttributableToOwnersOfParent",
        "ProfitLoss",
    ],
    "interest_expense": [
        "InterestExpense",
        "InterestExpenseDebt",
        "InterestAndDebtExpense",
        "InterestExpenseNonoperating",
        "InterestIncomeExpenseNet",  # taken as absolute value
        "InterestPaid",  # cash-flow proxy; last resort for filers with no IS tag
        # IFRS
        "FinanceCosts",
        "InterestPaidClassifiedAsOperatingActivities",
    ],
    "tax_expense": [
        "IncomeTaxExpenseBenefit",
        # IFRS
        "IncomeTaxExpenseContinuingOperations",
        "AdjustmentsForIncomeTaxExpense",
    ],
    "operating_cash_flow": [
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
        # IFRS
        "CashFlowsFromUsedInOperatingActivities",
    ],
    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
        # IFRS
        "PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",
        "PurchaseOfPropertyPlantAndEquipment",
    ],
    # Cash outflows reported positive in companyfacts; stored positive (§19.1).
    "dividends_paid": [
        "PaymentsOfDividends",
        "PaymentsOfDividendsCommonStock",
        # IFRS
        "DividendsPaidClassifiedAsFinancingActivities",
        "DividendsPaid",
    ],
    "share_buybacks": [
        "PaymentsForRepurchaseOfCommonStock",
        # IFRS
        "PurchaseOfTreasuryShares",
        "PaymentsToAcquireOrRedeemEntitysShares",
    ],
    "receivables": [
        "AccountsReceivableNetCurrent",
        "ReceivablesNetCurrent",
        # IFRS
        "TradeAndOtherCurrentReceivables",
    ],
    "inventory": [
        "InventoryNet",
        # IFRS
        "Inventories",
    ],
    "accounts_payable": [
        "AccountsPayableCurrent",
        "AccountsPayableAndAccruedLiabilitiesCurrent",
        # IFRS
        "TradeAndOtherCurrentPayables",
    ],
    "cash_and_equivalents": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        # IFRS
        "CashAndCashEquivalents",
    ],
    "current_assets": [
        "AssetsCurrent",
        # IFRS
        "CurrentAssets",
    ],
    "current_liabilities": [
        "LiabilitiesCurrent",
        # IFRS
        "CurrentLiabilities",
    ],
    "total_equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        # IFRS
        "EquityAttributableToOwnersOfParent",
        "Equity",
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
# IFRS total debt (only after the us-gaap rule yields nothing): "Borrowings"
# alone, else NoncurrentBorrowings + CurrentBorrowings summed per period.
IFRS_BORROWINGS_TAG = "Borrowings"
IFRS_BORROWINGS_COMPONENT_TAGS = ["NoncurrentBorrowings", "CurrentBorrowings"]
SHARES_TAG = "EntityCommonStockSharesOutstanding"  # dei taxonomy, latest value

# D&A component fallback when no combined tag is filed (e.g. Microsoft):
# Depreciation is the required anchor; amortization components add when present.
DA_COMPONENT_TAGS = [
    "Depreciation",
    "AmortizationOfIntangibleAssets",
    "FinanceLeaseRightOfUseAssetAmortization",
]


def _select_annual_values(
    tag_payload: dict[str, Any], tag: str, warnings: list[str] | None = None
) -> tuple[dict[str, float], str | None]:
    """Return ({period_end: value}, unit) for annual-report FY facts.

    Facts must come from an ANNUAL_FORMS filing with ``fp == "FY"``; duration
    facts must span >= 300 days (annual filings also embed quarterly periods);
    values are deduped by ``end`` preferring the latest ``filed``.

    Unit selection: prefer "USD"; else the single monetary unit present; else
    the monetary unit with the most annual periods (recording a warning when a
    warnings list is supplied). Returns ({}, None) when no monetary unit has
    annual data.
    """
    per_unit: dict[str, dict[str, dict[str, Any]]] = {}
    for unit, entries in (tag_payload.get("units") or {}).items():
        if not _MONETARY_UNIT_RE.match(unit):
            continue
        best: dict[str, dict[str, Any]] = {}
        for entry in entries:
            if entry.get("form") not in ANNUAL_FORMS or entry.get("fp") != "FY":
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
        if best:
            per_unit[unit] = best

    if not per_unit:
        return {}, None
    if "USD" in per_unit:
        unit = "USD"
    elif len(per_unit) == 1:
        unit = next(iter(per_unit))
    else:
        unit = sorted(per_unit, key=lambda u: (-len(per_unit[u]), u))[0]
        if warnings is not None:
            warnings.append(
                f"{tag} reported in multiple currencies "
                f"({', '.join(sorted(per_unit))}); using {unit} "
                "(most annual periods)."
            )
    values = {end: float(entry["val"]) for end, entry in per_unit[unit].items()}
    if tag in _ABS_VALUE_TAGS:
        values = {end: abs(v) for end, v in values.items()}
    return values, unit


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
        facts = facts_doc.get("facts", {})
        gaap = facts.get("us-gaap") or {}
        ifrs = facts.get("ifrs-full") or {}
        warnings: list[str] = []

        def _payload(tag: str) -> dict[str, Any] | None:
            # Taxonomy resolution order: us-gaap first, then ifrs-full. A
            # filer populates (essentially) one of the two, and the shared
            # tag names (e.g. GrossProfit) must keep preferring us-gaap so
            # US filers are unaffected.
            return gaap.get(tag) or ifrs.get(tag) or None

        field_maps: dict[str, dict[str, float]] = {}
        field_units: dict[str, str | None] = {}
        for field, tags in TAG_PREFERENCES.items():
            # Merge per period across the preference list: earlier tags win for
            # any period they cover, later tags only fill periods the earlier
            # ones miss. A single first-tag-wins rule fails on filers whose
            # preferred tag has stale partial history (e.g. Microsoft's
            # CostOfRevenue stops years before CostOfGoodsAndServicesSold).
            values: dict[str, float] = {}
            unit: str | None = None
            contributing: list[str] = []
            for tag in tags:
                payload = _payload(tag)
                if not payload:
                    continue
                tag_values, tag_unit = _select_annual_values(payload, tag, warnings)
                if not tag_values:
                    continue
                if unit is not None and tag_unit != unit:
                    # Never mix currencies inside one field's history.
                    warnings.append(
                        f"{field}: tag {tag} reported in {tag_unit} while "
                        f"earlier tags use {unit}; skipping it."
                    )
                    continue
                added = {end: v for end, v in tag_values.items() if end not in values}
                if added:
                    values.update(added)
                    contributing.append(tag)
                    unit = unit or tag_unit
            if len(contributing) > 1:
                warnings.append(
                    f"{field} assembled from multiple SEC tags "
                    f"({', '.join(contributing)}); periods may not be like-for-like."
                )
            if not values and field == "depreciation_amortization":
                # Some filers (e.g. Microsoft) report no combined D&A tag and
                # split it across components instead; sum them per year when
                # the depreciation component exists.
                values = self._sum_component_values(gaap, DA_COMPONENT_TAGS, anchor=DA_COMPONENT_TAGS[0])
                if values:
                    _anchor, unit = _select_annual_values(
                        gaap[DA_COMPONENT_TAGS[0]], DA_COMPONENT_TAGS[0]
                    )
            if not values:
                warnings.append(f"{field} unavailable from SEC EDGAR")
            field_maps[field] = values
            field_units[field] = unit

        debt_values, debt_unit = self._total_debt_values_with_unit(
            gaap, ifrs, warnings
        )
        field_maps["total_debt"] = debt_values
        field_units["total_debt"] = debt_unit

        currency = self._apply_reporting_currency(field_maps, field_units, warnings)

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
            warnings.append(
                "No annual report facts (10-K/20-F/40-F) found on SEC EDGAR "
                "for this company."
            )

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
            currency=currency,
            data_source="SEC EDGAR",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            warnings=warnings,
        )

    @staticmethod
    def _apply_reporting_currency(
        field_maps: dict[str, dict[str, float]],
        field_units: dict[str, str | None],
        warnings: list[str],
    ) -> str:
        """Pick the bundle reporting currency and drop off-currency fields.

        The reporting currency is the dominant unit across populated fields
        (ties prefer USD, then alphabetical). Fields reported in any other
        unit are dropped with a warning — there is no FX conversion in the
        MVP, so mixing them would corrupt derived figures. Defaults to "USD"
        (the legacy assumption) when nothing is populated.
        """
        populated = {
            field: unit
            for field, unit in field_units.items()
            if field_maps.get(field) and unit
        }
        if not populated:
            return "USD"
        counts = Counter(populated.values())
        dominant = sorted(counts, key=lambda u: (-counts[u], u != "USD", u))[0]
        for field, unit in populated.items():
            if unit != dominant:
                warnings.append(
                    f"{field} dropped: reported in {unit} while the bundle "
                    f"reporting currency is {dominant} (no FX conversion)."
                )
                field_maps[field] = {}
        return dominant

    # ----- field helpers -----

    def _sum_component_values(
        self, gaap: dict[str, Any], tags: list[str], *, anchor: str
    ) -> dict[str, float]:
        """Per-period sum of component tags; empty unless the anchor tag has data.

        Used for D&A when no combined tag is filed: the depreciation component
        must exist for a period to count, amortization components are additive.
        """
        component_values: dict[str, dict[str, float]] = {}
        for tag in tags:
            if gaap.get(tag):
                values, _unit = _select_annual_values(gaap[tag], tag)
                if values:
                    component_values[tag] = values
        anchor_values = component_values.get(anchor, {})
        if not anchor_values:
            return {}
        return {
            end: sum(values[end] for values in component_values.values() if end in values)
            for end in anchor_values
        }

    def _total_debt_values(
        self, gaap: dict[str, Any], warnings: list[str], ifrs: dict[str, Any] | None = None
    ) -> dict[str, float]:
        """Per-period total debt (values only); see _total_debt_values_with_unit."""
        values, _unit = self._total_debt_values_with_unit(gaap, ifrs or {}, warnings)
        return values

    def _total_debt_values_with_unit(
        self, gaap: dict[str, Any], ifrs: dict[str, Any], warnings: list[str]
    ) -> tuple[dict[str, float], str | None]:
        """Per-period total debt with the §5 non-double-counting current rule.

        us-gaap first; only when the whole us-gaap rule (including the
        LongTermDebt fallback) yields nothing, the IFRS rule applies:
        "Borrowings" alone, else NoncurrentBorrowings + CurrentBorrowings
        summed per period.
        """

        def _values(
            source: dict[str, Any], tag: str
        ) -> tuple[dict[str, float], str | None]:
            payload = source.get(tag)
            if not payload:
                return {}, None
            return _select_annual_values(payload, tag, warnings)

        noncurrent, nc_unit = _values(gaap, TOTAL_DEBT_NONCURRENT_TAG)
        debt_current, dc_unit = _values(gaap, TOTAL_DEBT_CURRENT_TAG)
        current_components: list[dict[str, float]] = []
        component_units: list[str | None] = []
        for tag in TOTAL_DEBT_CURRENT_COMPONENT_TAGS:
            values, unit = _values(gaap, tag)
            current_components.append(values)
            component_units.append(unit)

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
            unit = next(
                (u for u in [nc_unit, dc_unit, *component_units] if u), None
            )
            return totals, unit

        fallback, fb_unit = _values(gaap, TOTAL_DEBT_FALLBACK_TAG)
        if fallback:
            return fallback, fb_unit

        # IFRS filers (20-F): Borrowings alone, else the noncurrent + current
        # split summed per period.
        borrowings, b_unit = _values(ifrs, IFRS_BORROWINGS_TAG)
        if borrowings:
            return borrowings, b_unit
        ifrs_noncurrent, inc_unit = _values(ifrs, IFRS_BORROWINGS_COMPONENT_TAGS[0])
        ifrs_current, ic_unit = _values(ifrs, IFRS_BORROWINGS_COMPONENT_TAGS[1])
        ends = set(ifrs_noncurrent) | set(ifrs_current)
        if ends:
            totals = {
                end: ifrs_noncurrent.get(end, 0.0) + ifrs_current.get(end, 0.0)
                for end in ends
            }
            return totals, inc_unit or ic_unit

        warnings.append("total_debt unavailable from SEC EDGAR")
        return {}, None

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
