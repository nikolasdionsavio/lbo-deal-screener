"""GET /api/companies/{ticker}/statements (spec §19.7).

Mock-mode endpoint shape (TESTCO: 5 years descending, three statement groups,
derived_fields passed through, hand-checkable values) plus the max_years
duck-typing: providers accepting the keyword are asked for up to 15 years
directly; MockProvider lacks it and falls back to the regular bundle.
"""

from datetime import datetime, timezone
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_provider_dep
from app.main import app
from app.providers.base import DataProvider
from app.providers.mock import MockProvider
from app.schemas.company import CompanyDataBundle, CompanyInfo, SearchResult
from app.schemas.financials import FiscalYearFinancials

REL_TOL = 1e-6

INCOME_KEYS = {
    "revenue",
    "cost_of_revenue",
    "gross_profit",
    "research_development",
    "selling_general_admin",
    "operating_income",
    "depreciation_amortization",
    "ebitda",
    "interest_expense",
    "pretax_income",
    "tax_expense",
    "net_income",
    "eps_basic",
    "eps_diluted",
    "shares_diluted",
}
BALANCE_KEYS = {
    "cash_and_equivalents",
    "receivables",
    "inventory",
    "current_assets",
    "ppe_net",
    "goodwill",
    "intangible_assets",
    "total_assets",
    "accounts_payable",
    "current_liabilities",
    "long_term_debt",
    "total_debt",
    "total_liabilities",
    "retained_earnings",
    "total_equity",
}
CASH_FLOW_KEYS = {
    "stock_based_compensation",
    "operating_cash_flow",
    "capex",
    "free_cash_flow",
    "investing_cash_flow",
    "dividends_paid",
    "share_buybacks",
    "financing_cash_flow",
}

_mock_provider = MockProvider()


class _MaxYearsProvider(DataProvider):
    """EDGAR-like provider: get_company accepts the §19.7 max_years keyword."""

    name = "fake_edgar"

    def __init__(self, available_years: int = 12) -> None:
        self.available_years = available_years
        self.seen_max_years: list[int] = []

    def search(self, query: str) -> list[SearchResult]:
        return []

    def get_company(self, ticker: str, max_years: int = 5) -> CompanyDataBundle:
        self.seen_max_years.append(max_years)
        first = 2026 - min(self.available_years, max_years)
        years = [
            FiscalYearFinancials(
                fiscal_year=fy,
                period_end=f"{fy}-12-31",
                revenue=float(fy) * 1e6,
                operating_income=100e6,
                depreciation_amortization=10e6,
                ebitda=110e6,
                derived_fields=["operating_income", "ebitda"],
            )
            for fy in range(first, 2026)  # ascending, like real providers
        ]
        return CompanyDataBundle(
            info=CompanyInfo(ticker=ticker.upper(), name="Fake EDGAR Corp"),
            market=None,
            financials=years,
            currency="USD",
            data_source="SEC EDGAR",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            warnings=["operating_income derived as revenue − total costs "
                      "and expenses (no operating income tag filed)"],
        )


@pytest.fixture()
def api(client: TestClient) -> Iterator[TestClient]:
    """conftest client (in-memory SQLite) + MockProvider dependency override."""
    app.dependency_overrides[get_provider_dep] = lambda: _mock_provider
    yield client
    app.dependency_overrides.pop(get_provider_dep, None)


def test_statements_mock_shape_five_years_descending(api: TestClient) -> None:
    resp = api.get("/api/companies/TESTCO/statements")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ticker"] == "TESTCO"
    assert body["currency"] == "USD"
    assert body["data_source"] == "Sample data (illustrative figures)"
    assert body["fetched_at"]
    assert body["warnings"] == []
    # MockProvider returns its 5 years, DESCENDING fiscal_year.
    assert [y["fiscal_year"] for y in body["years"]] == [2025, 2024, 2023, 2022, 2021]
    for year in body["years"]:
        assert set(year) == {
            "fiscal_year",
            "period_end",
            "derived_fields",
            "income_statement",
            "balance_sheet",
            "cash_flow",
        }
        assert set(year["income_statement"]) == INCOME_KEYS
        assert set(year["balance_sheet"]) == BALANCE_KEYS
        assert set(year["cash_flow"]) == CASH_FLOW_KEYS
        # TESTCO states every field directly; nothing is derived.
        assert year["derived_fields"] == []


def test_statements_testco_values_spot_checked(api: TestClient) -> None:
    body = api.get("/api/companies/testco/statements").json()  # case-insensitive
    fy2025 = body["years"][0]
    assert fy2025["period_end"] == "2025-12-31"
    income = fy2025["income_statement"]
    assert income["revenue"] == pytest.approx(1_000_000_000.0, rel=REL_TOL)
    assert income["cost_of_revenue"] == pytest.approx(600e6, rel=REL_TOL)
    assert income["gross_profit"] == pytest.approx(400e6, rel=REL_TOL)
    assert income["operating_income"] == pytest.approx(200e6, rel=REL_TOL)
    assert income["ebitda"] == pytest.approx(250e6, rel=REL_TOL)
    assert income["net_income"] == pytest.approx(135e6, rel=REL_TOL)
    balance = fy2025["balance_sheet"]
    assert balance["cash_and_equivalents"] == pytest.approx(100e6, rel=REL_TOL)
    assert balance["receivables"] == pytest.approx(120e6, rel=REL_TOL)
    assert balance["total_debt"] == pytest.approx(400e6, rel=REL_TOL)
    assert balance["total_equity"] == pytest.approx(500e6, rel=REL_TOL)
    cash_flow = fy2025["cash_flow"]
    assert cash_flow["operating_cash_flow"] == pytest.approx(230e6, rel=REL_TOL)
    assert cash_flow["capex"] == pytest.approx(50e6, rel=REL_TOL)
    assert cash_flow["free_cash_flow"] == pytest.approx(180e6, rel=REL_TOL)
    assert cash_flow["dividends_paid"] == pytest.approx(30e6, rel=REL_TOL)
    assert cash_flow["share_buybacks"] == pytest.approx(50e6, rel=REL_TOL)
    # Oldest year last (descending order).
    fy2021 = body["years"][-1]
    assert fy2021["fiscal_year"] == 2021
    assert fy2021["income_statement"]["revenue"] == pytest.approx(800e6, rel=REL_TOL)


def test_statements_unknown_ticker_404(api: TestClient) -> None:
    assert api.get("/api/companies/ZZZZ/statements").status_code == 404


def test_statements_max_years_provider_gets_15_and_derived_fields_pass_through(
    client: TestClient,
) -> None:
    """Providers accepting max_years are asked for STATEMENTS_MAX_YEARS (15)
    directly; per-year derived_fields and bundle warnings pass through."""
    provider = _MaxYearsProvider(available_years=12)
    app.dependency_overrides[get_provider_dep] = lambda: provider
    try:
        body = client.get("/api/companies/FAKE/statements").json()
    finally:
        app.dependency_overrides.pop(get_provider_dep, None)
    assert provider.seen_max_years == [15]
    # All 12 available years, descending (>5 — not capped by the bundle default).
    assert [y["fiscal_year"] for y in body["years"]] == list(range(2025, 2013, -1))
    assert body["years"][0]["derived_fields"] == ["operating_income", "ebitda"]
    assert any("operating_income derived" in w for w in body["warnings"])
