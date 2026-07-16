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
- Operating income (§19.7): periods no operating-income tag covers are derived
  per period as revenue − CostsAndExpenses (else gross_profit −
  OperatingExpenses), recorded in derived_fields with a bundle warning.
- All HTTP: 15s timeout, errors mapped to ProviderError with readable messages.
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

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
# The ticker->CIK/name index is seeded from a committed cache so a cold start
# never depends on a live SEC call (shared cloud IPs get rate-limited). But a
# frozen copy silently hides every company listed since it was captured (e.g. a
# fresh IPO like SK hynix / SKHY in Jul 2026), so refresh it in the background
# once the on-disk copy ages past this TTL. On a refetch failure the stale copy
# is kept — a slightly old index beats a hard failure.
TICKER_MAP_TTL_SECONDS = 3 * 24 * 3600  # 3 days
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
# §19.8 unit exceptions for exactly the per-share and share-count fields:
# eps_basic/eps_diluted accept "<CCY>/shares" (the currency prefix is kept for
# the reporting-currency pass); shares_diluted accepts the bare "shares" unit
# (currency-neutral, exempt from the reporting-currency pass).
_PER_SHARE_UNIT_RE = re.compile(r"^([A-Z]{3})/shares$")
_SHARES_UNIT = "shares"
PER_SHARE_FIELDS = frozenset({"eps_basic", "eps_diluted"})
SHARE_COUNT_FIELDS = frozenset({"shares_diluted"})

# Tag preference lists per spec §5 — merged per period, earlier tags win.
# Each tag resolves from us-gaap first, then ifrs-full; the IFRS tags are
# listed AFTER every us-gaap tag so US filers are unaffected.
TAG_PREFERENCES: dict[str, list[str]] = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        # CRWD-class filers (§19.8) tag only the Including variant.
        "RevenueFromContractWithCustomerIncludingAssessedTax",
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
        "InterestPaidNet",  # cash-flow proxy; some filers (e.g. COHR) tag no IS interest
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
    # ----- extended statement fields (spec §19.8) -----
    # Tag names shared by us-gaap and ifrs-full (Assets, Liabilities,
    # Goodwill, ResearchAndDevelopmentExpense) resolve from either taxonomy
    # via _payload; explicit IFRS tags are listed after every us-gaap tag.
    "research_development": ["ResearchAndDevelopmentExpense"],
    "selling_general_admin": [
        "SellingGeneralAndAdministrativeExpense",
        # else GeneralAndAdministrativeExpense + SellingAndMarketingExpense
        # summed per period (component fallback below, like D&A).
    ],
    "pretax_income": [
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxes"
        "ExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxes"
        "MinorityInterestAndIncomeLossFromEquityMethodInvestments",
    ],
    "eps_basic": ["EarningsPerShareBasic"],  # unit "USD/shares" (§19.8 exception)
    "eps_diluted": ["EarningsPerShareDiluted"],  # unit "USD/shares" (§19.8 exception)
    "shares_diluted": [
        "WeightedAverageNumberOfDilutedSharesOutstanding",  # unit "shares"
    ],
    "stock_based_compensation": ["ShareBasedCompensation"],
    "total_assets": ["Assets"],  # same tag in ifrs-full
    "total_liabilities": ["Liabilities"],  # same tag in ifrs-full
    "goodwill": ["Goodwill"],  # same tag in ifrs-full
    "intangible_assets": [
        "IntangibleAssetsNetExcludingGoodwill",
        "FiniteLivedIntangibleAssetsNet",
    ],
    "ppe_net": [
        "PropertyPlantAndEquipmentNet",
        # IFRS
        "PropertyPlantAndEquipment",
    ],
    "long_term_debt": ["LongTermDebtNoncurrent", "LongTermDebt"],
    "retained_earnings": ["RetainedEarningsAccumulatedDeficit"],
    "investing_cash_flow": [
        "NetCashProvidedByUsedInInvestingActivities",
        # IFRS
        "CashFlowsFromUsedInInvestingActivities",
    ],
    "financing_cash_flow": [
        "NetCashProvidedByUsedInFinancingActivities",
        # IFRS
        "CashFlowsFromUsedInFinancingActivities",
    ],
}
_ABS_VALUE_TAGS = {"InterestIncomeExpenseNet"}

# §19.8 extended fields are additive/optional: missing tags simply leave the
# field None — they never add "<field> unavailable from SEC EDGAR" warnings
# (which stay scoped to the §5 core field set).
EXTENDED_STATEMENT_FIELDS = frozenset(
    {
        "research_development",
        "selling_general_admin",
        "pretax_income",
        "eps_basic",
        "eps_diluted",
        "shares_diluted",
        "stock_based_compensation",
        "total_assets",
        "total_liabilities",
        "goodwill",
        "intangible_assets",
        "ppe_net",
        "long_term_debt",
        "retained_earnings",
        "investing_cash_flow",
        "financing_cash_flow",
    }
)

# selling_general_admin component fallback (§19.8): when no combined SG&A tag
# is filed (e.g. Microsoft, CrowdStrike), sum the two components per period —
# BOTH must be present for a period to count (a lone G&A would understate).
SGA_COMPONENT_TAGS = [
    "GeneralAndAdministrativeExpense",
    "SellingAndMarketingExpense",
]

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
# an anchor tag is required per period; the other components add when present.
# Anchors are tried in order (§19.8): "Depreciation" (Microsoft-class), else
# "CapitalizedContractCostAmortization" (CrowdStrike-class — CRWD files no
# standard depreciation/D&A flow tag at all, only amortization components;
# its property depreciation lives in a custom extension tag that companyfacts
# does not expose under us-gaap).
DA_COMPONENT_TAGS = [
    "Depreciation",
    "AmortizationOfIntangibleAssets",
    "FinanceLeaseRightOfUseAssetAmortization",
    "CapitalizedContractCostAmortization",
    "CapitalizedComputerSoftwareAmortization1",
    "OtherDepreciationAndAmortization",
    "OperatingLeaseRightOfUseAssetAmortizationExpense",
]
DA_ANCHOR_TAGS = ["Depreciation", "CapitalizedContractCostAmortization"]

# Operating-income derivation inputs (§19.7) for periods no operating-income
# tag covers (e.g. Coherent's FY2025 10-K files CostsAndExpenses but no
# OperatingIncomeLoss): (1) revenue − CostsAndExpenses, else
# (2) gross_profit − OperatingExpenses. Like the D&A component fallback, the
# helper tag maps are captured internally and never become fields themselves.
OPERATING_INCOME_TOTAL_COSTS_TAG = "CostsAndExpenses"
OPERATING_INCOME_OPEX_TAG = "OperatingExpenses"
OPERATING_INCOME_DERIVED_WARNING = (
    "operating_income derived as revenue − total costs and expenses "
    "(no operating income tag filed)"
)
OPERATING_INCOME_DERIVED_FROM_OPEX_WARNING = (
    "operating_income derived as gross profit − operating expenses "
    "(no operating income tag filed)"
)


def _select_annual_values(
    tag_payload: dict[str, Any],
    tag: str,
    warnings: list[str] | None = None,
    *,
    unit_kind: str = "monetary",
) -> tuple[dict[str, float], str | None]:
    """Return ({period_end: value}, unit) for annual-report FY facts.

    Facts must come from an ANNUAL_FORMS filing with ``fp == "FY"``; duration
    facts must span >= 300 days (annual filings also embed quarterly periods);
    values are deduped by ``end`` preferring the latest ``filed``.

    ``unit_kind`` (§19.8 exceptions): "monetary" (default) accepts plain ISO
    currency units; "per_share" accepts "<CCY>/shares" units (eps fields) and
    reports the currency prefix as the unit so the reporting-currency pass
    applies; "shares" accepts the bare "shares" unit (share counts) and
    reports unit None (currency-neutral).

    Unit selection: prefer "USD" (or "USD/shares"); else the single accepted
    unit present; else the accepted unit with the most annual periods
    (recording a warning when a warnings list is supplied). Returns ({}, None)
    when no accepted unit has annual data.
    """

    def _accept(unit: str) -> bool:
        if unit_kind == "per_share":
            return _PER_SHARE_UNIT_RE.match(unit) is not None
        if unit_kind == "shares":
            return unit == _SHARES_UNIT
        return _MONETARY_UNIT_RE.match(unit) is not None

    preferred_unit = "USD/shares" if unit_kind == "per_share" else "USD"

    per_unit: dict[str, dict[str, dict[str, Any]]] = {}
    for unit, entries in (tag_payload.get("units") or {}).items():
        if not _accept(unit):
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
    if preferred_unit in per_unit:
        unit = preferred_unit
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
    if unit_kind == "per_share":
        # Report the currency prefix ("USD" from "USD/shares") so the bundle
        # reporting-currency pass treats eps like any monetary field.
        match = _PER_SHARE_UNIT_RE.match(unit)
        return values, match.group(1) if match else unit
    if unit_kind == "shares":
        return values, None  # share counts are currency-neutral
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
        # Lazily built, lowercased search index: (ticker, title, cik,
        # ticker_lower, title_lower). Built once from the in-memory ticker map
        # so every autocomplete keystroke is a pure in-memory comparison pass
        # (~1ms over ~10k US filers) with zero network calls. CIK is the
        # tie-break for name matches (lower CIK = earlier SEC registrant, a
        # free proxy for the more established / better-known company).
        self._search_index_cache: list[tuple[str, str, int, str, str]] | None = None

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
        cached: dict[str, Any] | None = None
        cached_fresh = False
        if cache_file.is_file():
            try:
                cached = json.loads(cache_file.read_text(encoding="utf-8"))
                age = time.time() - cache_file.stat().st_mtime
                cached_fresh = age < TICKER_MAP_TTL_SECONDS
            except (ValueError, OSError):
                cached = None  # corrupt/unreadable -> refetch
        if cached is not None and cached_fresh:
            self._ticker_map_mem = cached
            return cached
        # Missing, corrupt, or stale past the TTL: refetch. If SEC is unreachable
        # but a stale copy is still on disk, keep serving it — a slightly old
        # index beats a hard failure for every search.
        try:
            data = self._request_json(TICKER_MAP_URL, what="SEC EDGAR ticker list")
        except ProviderError:
            if cached is not None:
                self._ticker_map_mem = cached
                return cached
            raise
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

    def _search_index(self) -> list[tuple[str, str, int, str, str]]:
        """Cached (ticker, title, cik, ticker_lower, title_lower) list."""
        if self._search_index_cache is None:
            index: list[tuple[str, str, int, str, str]] = []
            for rec in self._ticker_map().values():
                ticker = str(rec.get("ticker", ""))
                if not ticker:
                    continue
                title = str(rec.get("title", ""))
                try:
                    cik = int(rec.get("cik_str", 0))
                except (TypeError, ValueError):
                    cik = 0
                index.append((ticker, title, cik, ticker.lower(), title.lower()))
            self._search_index_cache = index
        return self._search_index_cache

    def search(self, query: str) -> list[SearchResult]:
        """Instant local ticker/name search over the bundled SEC ticker file.

        No network call: the autocomplete dropdown must feel immediate, so
        results come from the in-memory index of ~10k US filers. Ranking, best
        first: exact ticker, ticker prefix, name starts-with, ticker substring,
        name word-start or substring. Ticker buckets break ties by ticker
        length then alpha (the primary listing over warrants/preferreds like
        AAPLW / JPM-PC); name buckets break ties by CIK ascending (the more
        established registrant first).
        """
        q = query.strip().lower()
        if not q:
            return []
        # Each entry kept as (ticker, title, cik) within its bucket.
        exact: list[tuple[str, str, int]] = []
        t_prefix: list[tuple[str, str, int]] = []
        n_prefix: list[tuple[str, str, int]] = []
        t_contains: list[tuple[str, str, int]] = []
        n_other: list[tuple[str, str, int]] = []
        for ticker, title, cik, tl, nl in self._search_index():
            entry = (ticker, title, cik)
            if tl == q:
                exact.append(entry)
            elif tl.startswith(q):
                t_prefix.append(entry)
            elif nl.startswith(q):
                n_prefix.append(entry)
            elif q in tl:
                t_contains.append(entry)
            elif f" {q}" in nl or q in nl:
                n_other.append(entry)

        by_ticker = lambda e: (len(e[0]), e[0])
        by_cik = lambda e: e[2]
        ordered = (
            sorted(exact, key=by_ticker)
            + sorted(t_prefix, key=by_ticker)
            + sorted(n_prefix, key=by_cik)
            + sorted(t_contains, key=by_ticker)
            + sorted(n_other, key=by_cik)
        )
        return [
            SearchResult(ticker=t, name=n, exchange=None, source=self.name)
            for t, n, _cik in ordered[:_MAX_SEARCH_RESULTS]
        ]

    def get_company(self, ticker: str, max_years: int = _MAX_YEARS) -> CompanyDataBundle:
        """Company bundle from companyfacts (spec §5).

        ``max_years`` caps the returned fiscal years at year-selection (§19.7):
        the regular bundle keeps the 5-year default everywhere; the statements
        endpoint asks for up to 15.
        """
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
        derived_operating_income: dict[str, str] = {}  # period end -> derivation route
        for field, tags in TAG_PREFERENCES.items():
            # Merge per period across the preference list: earlier tags win for
            # any period they cover, later tags only fill periods the earlier
            # ones miss. A single first-tag-wins rule fails on filers whose
            # preferred tag has stale partial history (e.g. Microsoft's
            # CostOfRevenue stops years before CostOfGoodsAndServicesSold).
            unit_kind = (
                "per_share"
                if field in PER_SHARE_FIELDS
                else "shares"
                if field in SHARE_COUNT_FIELDS
                else "monetary"
            )
            values: dict[str, float] = {}
            unit: str | None = None
            contributing: list[str] = []
            for tag in tags:
                payload = _payload(tag)
                if not payload:
                    continue
                tag_values, tag_unit = _select_annual_values(
                    payload, tag, warnings, unit_kind=unit_kind
                )
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
            if field == "depreciation_amortization":
                # Some filers (e.g. Microsoft, CrowdStrike) report no combined
                # D&A tag and split it across components instead; others (e.g.
                # Marvell) file a combined tag with stale partial history that
                # stops years before the components do. Sum the components per
                # year when an anchor component exists (§19.8 anchor order)
                # and fill ONLY the periods the combined tags missed —
                # combined-tag values are never overwritten.
                component_sums, anchor_used = self._sum_component_values(
                    gaap, DA_COMPONENT_TAGS, anchors=DA_ANCHOR_TAGS
                )
                if component_sums and anchor_used is not None:
                    _anchor, component_unit = _select_annual_values(
                        gaap[anchor_used], anchor_used
                    )
                    if unit is not None and component_unit != unit:
                        # Never mix currencies inside one field's history.
                        warnings.append(
                            f"{field}: component tags reported in "
                            f"{component_unit} while earlier tags use {unit}; "
                            "skipping them."
                        )
                    else:
                        added = {
                            end: v
                            for end, v in component_sums.items()
                            if end not in values
                        }
                        if added:
                            values.update(added)
                            contributing.append(
                                f"components anchored on {anchor_used}"
                            )
                            unit = unit or component_unit
            if len(contributing) > 1:
                warnings.append(
                    f"{field} assembled from multiple SEC tags "
                    f"({', '.join(contributing)}); periods may not be like-for-like."
                )
            if not values and field == "selling_general_admin":
                # §19.8 component fallback: G&A + S&M summed per period when
                # no combined SG&A tag is filed; both components required.
                values, unit = self._sum_required_components(
                    gaap, SGA_COMPONENT_TAGS
                )
            if field == "operating_income":
                # §19.7 per-period derivation for periods no operating-income
                # tag covers; periods the preferred tags already fill are
                # never overwritten. Relies on dict order: revenue and
                # gross_profit precede operating_income in TAG_PREFERENCES.
                extra, unit, routes = self._derive_missing_operating_income(
                    values, unit, field_maps, field_units, _payload
                )
                if extra:
                    values.update(extra)
                    derived_operating_income.update(routes)
            if not values and field not in EXTENDED_STATEMENT_FIELDS:
                # §19.8 extended fields are optional and never warn; the §5
                # core fields keep their per-field unavailability warning.
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
            if end in derived_operating_income and end in field_maps["operating_income"]:
                # The currency pass may have dropped the whole field; only
                # periods that kept their derived value are marked derived.
                row.derived_fields.append("operating_income")
            rows_by_year[fiscal_year] = row
        years = [rows_by_year[fy] for fy in sorted(rows_by_year)][-max(1, max_years):]

        derived_routes = {
            derived_operating_income[row.period_end]
            for row in years
            if row.period_end in derived_operating_income
            and "operating_income" in row.derived_fields
        }
        if "total_costs" in derived_routes:
            warnings.append(OPERATING_INCOME_DERIVED_WARNING)
        if "opex" in derived_routes:
            warnings.append(OPERATING_INCOME_DERIVED_FROM_OPEX_WARNING)

        shares = self._latest_shares(facts_doc)
        if shares is None:
            warnings.append("shares_outstanding unavailable from SEC EDGAR")
        elif years:
            years[-1].shares_outstanding = shares

        normalize_financials(years)
        if not years:
            # No annual-report XBRL on file — e.g. a company that has only just
            # IPO'd and not yet filed a first 10-K/20-F (SK hynix / SKHY, listed
            # Jul 2026, is the canonical case). Every per-field "<x> unavailable"
            # warning is then just noise, so drop the whole set and lead with one
            # plain-language explanation: the UI shows a designed empty state
            # rather than a wall of twenty apologies.
            warnings[:] = [
                w for w in warnings if not w.endswith("unavailable from SEC EDGAR")
            ]
            warnings.insert(
                0,
                "No annual report (10-K or 20-F) is on file with the SEC yet, so "
                "financial statements are not available here. A newly listed "
                "company appears in full once it files its first annual report.",
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
        self, gaap: dict[str, Any], tags: list[str], *, anchors: list[str]
    ) -> tuple[dict[str, float], str | None]:
        """Per-period sum of component tags, anchored (§5, §19.8).

        Used for D&A when no combined tag is filed: the first anchor tag (in
        ``anchors`` order) with data fixes the periods; the other components
        are additive where present. Returns ({}, None) when no anchor has
        data, else (per-period sums, anchor tag used).
        """
        component_values: dict[str, dict[str, float]] = {}
        for tag in tags:
            if gaap.get(tag):
                values, _unit = _select_annual_values(gaap[tag], tag)
                if values:
                    component_values[tag] = values
        for anchor in anchors:
            anchor_values = component_values.get(anchor, {})
            if not anchor_values:
                continue
            sums = {
                end: sum(
                    values[end]
                    for values in component_values.values()
                    if end in values
                )
                for end in anchor_values
            }
            return sums, anchor
        return {}, None

    def _sum_required_components(
        self, gaap: dict[str, Any], tags: list[str]
    ) -> tuple[dict[str, float], str | None]:
        """Per-period sum requiring EVERY component tag (§19.8 SG&A fallback).

        Periods only count when all components report them in one shared
        unit; otherwise the sum would understate (e.g. G&A without S&M).
        """
        maps: list[dict[str, float]] = []
        unit: str | None = None
        for tag in tags:
            payload = gaap.get(tag)
            if not payload:
                return {}, None
            values, tag_unit = _select_annual_values(payload, tag)
            if not values:
                return {}, None
            if unit is None:
                unit = tag_unit
            elif tag_unit != unit:
                return {}, None  # never mix currencies inside one field
            maps.append(values)
        ends = set(maps[0])
        for values in maps[1:]:
            ends &= set(values)
        return {end: sum(m[end] for m in maps) for end in sorted(ends)}, unit

    @staticmethod
    def _derive_missing_operating_income(
        existing: dict[str, float],
        existing_unit: str | None,
        field_maps: dict[str, dict[str, float]],
        field_units: dict[str, str | None],
        payload: Callable[[str], dict[str, Any] | None],
    ) -> tuple[dict[str, float], str | None, dict[str, str]]:
        """Per-period operating-income derivation (spec §19.7).

        Only fills periods the operating-income tags miss:
        (1) revenue − CostsAndExpenses, else (2) gross_profit −
        OperatingExpenses. Returns (derived values, field unit, {period end:
        route}). Currencies are never mixed: a derived period must match the
        unit the field already carries, and both derivation inputs must agree.
        """
        derived: dict[str, float] = {}
        routes: dict[str, str] = {}
        unit = existing_unit

        def _tag_values(tag: str) -> tuple[dict[str, float], str | None]:
            tag_payload = payload(tag)
            if not tag_payload:
                return {}, None
            return _select_annual_values(tag_payload, tag)

        total_costs, total_costs_unit = _tag_values(OPERATING_INCOME_TOTAL_COSTS_TAG)
        opex, opex_unit = _tag_values(OPERATING_INCOME_OPEX_TAG)

        inputs = [
            ("total_costs", field_maps.get("revenue", {}),
             field_units.get("revenue"), total_costs, total_costs_unit),
            ("opex", field_maps.get("gross_profit", {}),
             field_units.get("gross_profit"), opex, opex_unit),
        ]
        for route, minuend, minuend_unit, subtrahend, subtrahend_unit in inputs:
            for end, value in minuend.items():
                if end in existing or end in derived or end not in subtrahend:
                    continue
                if minuend_unit and subtrahend_unit and minuend_unit != subtrahend_unit:
                    continue  # inputs reported in different currencies
                candidate_unit = minuend_unit or subtrahend_unit
                if unit is not None and candidate_unit != unit:
                    continue  # never mix currencies inside one field's history
                derived[end] = value - subtrahend[end]
                routes[end] = route
                unit = unit or candidate_unit
        return derived, unit, routes

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
