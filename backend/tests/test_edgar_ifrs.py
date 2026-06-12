"""SecEdgarProvider on IFRS / 20-F filers (foreign private issuers).

Fixture: tests/fixtures/edgar_companyfacts_ifrs_sample.json — real BUD
(Anheuser-Busch InBev) companyfacts trimmed to the FY2024 + FY2025 20-F
entries of the tags the provider maps. The `ifrs-full` taxonomy, 20-F form
acceptance, IFRS tag fallbacks, the Borrowings total-debt rule and the
unit/currency selection are all exercised through the public get_company
path. No live network: all HTTP goes through httpx.MockTransport.
"""

import json
from pathlib import Path
from typing import Any, Callable

import httpx
import pytest

from app.providers.edgar import COMPANYFACTS_URL, TICKER_MAP_URL, SecEdgarProvider

REL_TOL = 1e-6
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
IFRS_FIXTURE = FIXTURES_DIR / "edgar_companyfacts_ifrs_sample.json"

TEST_USER_AGENT = "Test Agent test@example.com"
BUD_CIK = 1668717
TICKER_MAP_PAYLOAD = {
    "0": {"cik_str": BUD_CIK, "ticker": "BUD", "title": "Anheuser-Busch InBev SA/NV"},
}

Handler = Callable[[httpx.Request], httpx.Response]


def _handler(facts_payload: dict[str, Any], cik: int) -> Handler:
    facts_url = COMPANYFACTS_URL.format(cik=cik)

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == TICKER_MAP_URL:
            return httpx.Response(200, json=TICKER_MAP_PAYLOAD)
        if url == facts_url:
            return httpx.Response(200, json=facts_payload)
        return httpx.Response(404, json={"detail": "not found"})

    return handler


def _make_provider(cache_dir: Path, handler: Handler) -> SecEdgarProvider:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return SecEdgarProvider(TEST_USER_AGENT, client=client, cache_dir=cache_dir)


def _bud_provider(tmp_path: Path) -> SecEdgarProvider:
    payload = json.loads(IFRS_FIXTURE.read_text())
    return _make_provider(tmp_path / "cache", _handler(payload, BUD_CIK))


# ---------------------------------------------------------------------------
# BUD 20-F fixture: IFRS tag mapping end to end
# ---------------------------------------------------------------------------


def test_ifrs_20f_maps_all_fields_from_ifrs_full(tmp_path: Path) -> None:
    bundle = _bud_provider(tmp_path).get_company("BUD")

    assert bundle.info.name == "Anheuser-Busch InBev SA/NV"
    assert bundle.info.cik == "0001668717"
    assert bundle.data_source == "SEC EDGAR"
    assert [y.fiscal_year for y in bundle.financials] == [2024, 2025]
    assert bundle.currency == "USD"  # all 20-F facts filed in USD units

    fy2025 = bundle.financials[-1]
    assert fy2025.period_end == "2025-12-31"
    assert fy2025.revenue == pytest.approx(59.320e9, rel=REL_TOL)
    assert fy2025.cost_of_revenue == pytest.approx(26.141e9, rel=REL_TOL)
    # GrossProfit is REPORTED under ifrs-full (not derived).
    assert fy2025.gross_profit == pytest.approx(33.179e9, rel=REL_TOL)
    assert "gross_profit" not in fy2025.derived_fields
    assert fy2025.operating_income == pytest.approx(15.405e9, rel=REL_TOL)
    assert fy2025.depreciation_amortization == pytest.approx(5.652e9, rel=REL_TOL)
    # EBITDA derived = operating income + D&A.
    assert fy2025.ebitda == pytest.approx(21.057e9, rel=REL_TOL)
    assert "ebitda" in fy2025.derived_fields
    # ProfitLossAttributableToOwnersOfParent is not in the fixture, so the
    # ProfitLoss fallback supplies net income.
    assert fy2025.net_income == pytest.approx(8.477e9, rel=REL_TOL)
    assert fy2025.interest_expense == pytest.approx(5.146e9, rel=REL_TOL)  # FinanceCosts
    assert fy2025.tax_expense == pytest.approx(2.850e9, rel=REL_TOL)
    assert fy2025.operating_cash_flow == pytest.approx(14.883e9, rel=REL_TOL)
    assert fy2025.capex == pytest.approx(3.656e9, rel=REL_TOL)
    # FCF derived = OCF - capex.
    assert fy2025.free_cash_flow == pytest.approx(11.227e9, rel=REL_TOL)
    assert "free_cash_flow" in fy2025.derived_fields
    assert fy2025.cash_and_equivalents == pytest.approx(11.638e9, rel=REL_TOL)
    # total_debt from the IFRS "Borrowings" tag (no us-gaap debt tags filed).
    assert fy2025.total_debt == pytest.approx(73.013e9, rel=REL_TOL)
    assert fy2025.current_assets == pytest.approx(24.769e9, rel=REL_TOL)
    assert fy2025.receivables == pytest.approx(6.161e9, rel=REL_TOL)
    assert fy2025.inventory == pytest.approx(5.107e9, rel=REL_TOL)
    assert fy2025.accounts_payable == pytest.approx(25.455e9, rel=REL_TOL)
    # EquityAttributableToOwnersOfParent is not in the fixture -> Equity.
    assert fy2025.total_equity == pytest.approx(97.736e9, rel=REL_TOL)
    assert fy2025.dividends_paid == pytest.approx(4.543e9, rel=REL_TOL)
    assert fy2025.share_buybacks == pytest.approx(2.600e9, rel=REL_TOL)
    # dei cover-page shares land on the latest fiscal year.
    assert fy2025.shares_outstanding == pytest.approx(1_797_199_994, rel=REL_TOL)

    # None of the mapped fields may carry an "unavailable" warning.
    for field in (
        "revenue", "cost_of_revenue", "gross_profit", "operating_income",
        "depreciation_amortization", "net_income", "interest_expense",
        "tax_expense", "operating_cash_flow", "capex", "cash_and_equivalents",
        "total_debt", "current_assets", "receivables", "inventory",
        "accounts_payable", "total_equity", "dividends_paid", "share_buybacks",
        "shares_outstanding",
    ):
        assert f"{field} unavailable from SEC EDGAR" not in bundle.warnings
    assert not any(w.startswith("No annual report facts") for w in bundle.warnings)


def test_ifrs_20f_dedupes_fy2024_preferring_latest_filed(tmp_path: Path) -> None:
    """FY2024 facts appear in both the 2025- and 2026-filed 20-Fs; the latest
    filed entry must win (real restatements would otherwise leak stale data)."""
    fy2024 = _bud_provider(tmp_path).get_company("BUD").financials[0]
    assert fy2024.revenue == pytest.approx(59.768e9, rel=REL_TOL)
    assert fy2024.total_debt == pytest.approx(72.169e9, rel=REL_TOL)
    assert fy2024.net_income == pytest.approx(7.416e9, rel=REL_TOL)


# ---------------------------------------------------------------------------
# Synthetic IFRS fixtures: non-USD units, 6-K exclusion, Borrowings split
# ---------------------------------------------------------------------------

EUR_CIK = 7654321
EUR_TICKER_MAP = {
    "0": {"cik_str": EUR_CIK, "ticker": "EURX", "title": "Synthetic Europa AG"},
}


def _entry(
    end: str,
    val: float,
    *,
    form: str = "20-F",
    fp: str = "FY",
    start: str | None = "auto",
    filed: str | None = None,
) -> dict[str, Any]:
    e: dict[str, Any] = {
        "end": end,
        "val": val,
        "fy": int(end[:4]),
        "fp": fp,
        "form": form,
        "filed": filed or f"{int(end[:4]) + 1}-03-01",
    }
    if start == "auto":
        e["start"] = f"{int(end[:4])}-01-01"
    elif start is not None:
        e["start"] = start
    return e


def _tag(units: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    return {"units": units}


def _eur_facts() -> dict[str, Any]:
    """EUR-reporting 20-F filer, with 6-K interims that must be excluded and
    the NoncurrentBorrowings + CurrentBorrowings total-debt split."""
    return {
        "cik": EUR_CIK,
        "entityName": "Synthetic Europa AG",
        "facts": {
            "dei": {
                "EntityCommonStockSharesOutstanding": _tag(
                    {"shares": [_entry("2025-12-31", 10e6, start=None)]}
                )
            },
            "ifrs-full": {
                "Revenue": _tag(
                    {
                        "EUR": [
                            _entry("2025-12-31", 800e6),
                            # 6-K interim (half-year): excluded by form.
                            _entry(
                                "2025-06-30", 350e6, form="6-K", fp="Q2",
                                start="2025-01-01",
                            ),
                        ]
                    }
                ),
                "CostOfSales": _tag({"EUR": [_entry("2025-12-31", 500e6)]}),
                "ProfitLossFromOperatingActivities": _tag(
                    {"EUR": [_entry("2025-12-31", 120e6)]}
                ),
                "ProfitLoss": _tag({"EUR": [_entry("2025-12-31", 80e6)]}),
                "CashAndCashEquivalents": _tag(
                    {"EUR": [_entry("2025-12-31", 60e6, start=None)]}
                ),
                # No "Borrowings": the noncurrent + current split must be summed.
                "NoncurrentBorrowings": _tag(
                    {"EUR": [_entry("2025-12-31", 200e6, start=None)]}
                ),
                "CurrentBorrowings": _tag(
                    {"EUR": [_entry("2025-12-31", 50e6, start=None)]}
                ),
            },
        },
    }


def _eur_provider(tmp_path: Path, facts: dict[str, Any]) -> SecEdgarProvider:
    facts_url = COMPANYFACTS_URL.format(cik=EUR_CIK)

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == TICKER_MAP_URL:
            return httpx.Response(200, json=EUR_TICKER_MAP)
        if url == facts_url:
            return httpx.Response(200, json=facts)
        return httpx.Response(404, json={"detail": "not found"})

    return _make_provider(tmp_path / "cache", handler)


def test_ifrs_eur_units_selected_and_bundle_currency_eur(tmp_path: Path) -> None:
    bundle = _eur_provider(tmp_path, _eur_facts()).get_company("EURX")
    assert bundle.currency == "EUR"
    assert [y.fiscal_year for y in bundle.financials] == [2025]
    fy2025 = bundle.financials[0]
    assert fy2025.revenue == pytest.approx(800e6, rel=REL_TOL)
    assert fy2025.cost_of_revenue == pytest.approx(500e6, rel=REL_TOL)
    assert fy2025.gross_profit == pytest.approx(300e6, rel=REL_TOL)  # derived
    assert fy2025.net_income == pytest.approx(80e6, rel=REL_TOL)
    # 6-K interim revenue (350m) must not leak into any annual row.
    assert all(y.revenue != pytest.approx(350e6) for y in bundle.financials)


def test_ifrs_total_debt_from_borrowings_split_when_no_combined_tag(
    tmp_path: Path,
) -> None:
    bundle = _eur_provider(tmp_path, _eur_facts()).get_company("EURX")
    assert bundle.financials[0].total_debt == pytest.approx(250e6, rel=REL_TOL)
    assert "total_debt unavailable from SEC EDGAR" not in bundle.warnings


def test_ifrs_20fa_amendment_accepted_and_wins_by_filed_date(tmp_path: Path) -> None:
    facts = _eur_facts()
    facts["facts"]["ifrs-full"]["Revenue"]["units"]["EUR"].append(
        _entry("2025-12-31", 810e6, form="20-F/A", filed="2026-09-01")
    )
    bundle = _eur_provider(tmp_path, facts).get_company("EURX")
    assert bundle.financials[0].revenue == pytest.approx(810e6, rel=REL_TOL)


def test_ifrs_minority_usd_field_dropped_with_warning(tmp_path: Path) -> None:
    """A single USD-only tag in an otherwise EUR bundle is dropped (no FX
    conversion); the warning names the field and both units."""
    facts = _eur_facts()
    facts["facts"]["ifrs-full"]["FinanceCosts"] = _tag(
        {"USD": [_entry("2025-12-31", 30e6)]}
    )
    bundle = _eur_provider(tmp_path, facts).get_company("EURX")
    assert bundle.currency == "EUR"  # dominant unit across populated fields
    assert bundle.financials[0].interest_expense is None
    assert any(
        "interest_expense" in w and "USD" in w and "EUR" in w
        for w in bundle.warnings
    )


def test_ifrs_multi_currency_tag_prefers_usd(tmp_path: Path) -> None:
    """A tag filed in several currencies uses USD when present (and is then
    subject to the dominant-currency drop rule like any other field)."""
    facts = _eur_facts()
    facts["facts"]["ifrs-full"]["DividendsPaidClassifiedAsFinancingActivities"] = _tag(
        {
            "EUR": [_entry("2025-12-31", 40e6)],
            "USD": [_entry("2025-12-31", 44e6)],
        }
    )
    bundle = _eur_provider(tmp_path, facts).get_company("EURX")
    # USD was preferred for the tag, then dropped against the EUR-dominant
    # bundle rather than silently mixed in.
    assert bundle.currency == "EUR"
    assert bundle.financials[0].dividends_paid is None
    assert any(
        "dividends_paid" in w and "USD" in w and "EUR" in w for w in bundle.warnings
    )


def test_ifrs_multi_currency_tag_without_usd_uses_most_periods_and_warns(
    tmp_path: Path,
) -> None:
    """No USD unit: the monetary unit with the most annual periods wins and
    the multi-currency selection is warned about."""
    facts = _eur_facts()
    facts["facts"]["ifrs-full"]["DividendsPaidClassifiedAsFinancingActivities"] = _tag(
        {
            "EUR": [_entry("2024-12-31", 38e6), _entry("2025-12-31", 40e6)],
            "GBP": [_entry("2025-12-31", 35e6)],
        }
    )
    bundle = _eur_provider(tmp_path, facts).get_company("EURX")
    assert any(
        "DividendsPaidClassifiedAsFinancingActivities" in w
        and "multiple currencies" in w
        for w in bundle.warnings
    )
    by_year = {y.fiscal_year: y for y in bundle.financials}
    assert by_year[2025].dividends_paid == pytest.approx(40e6, rel=REL_TOL)
    assert by_year[2024].dividends_paid == pytest.approx(38e6, rel=REL_TOL)
