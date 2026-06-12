"""Providers: mock, EDGAR (fixture-driven), FMP, composite, factory (spec §5, §15).

No live network calls: all EDGAR/FMP HTTP goes through httpx.MockTransport.
"""

import json
from pathlib import Path
from typing import Any, Callable

import httpx
import pytest

from app.core.config import Settings
from app.providers.edgar import (
    COMPANYFACTS_URL,
    OPERATING_INCOME_DERIVED_FROM_OPEX_WARNING,
    OPERATING_INCOME_DERIVED_WARNING,
    TICKER_MAP_URL,
    SecEdgarProvider,
)
from app.providers.exceptions import (
    CompanyNotFoundError,
    ProviderConfigError,
    ProviderError,
)
from app.providers.factory import MOCK_MODE_WARNING, get_provider
from app.providers.fmp import FmpProvider
from app.providers.live import CompositeLiveProvider
from app.providers.mock import MockProvider

REL_TOL = 1e-6
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
EDGAR_FIXTURE = FIXTURES_DIR / "edgar_companyfacts_sample.json"

TEST_USER_AGENT = "Test Agent test@example.com"
FIXTURE_CIK = 1234567
TICKER_MAP_PAYLOAD = {
    "0": {"cik_str": FIXTURE_CIK, "ticker": "FIXT", "title": "Fixture Manufacturing Corp"},
    "1": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
}


# ---------------------------------------------------------------------------
# MockProvider
# ---------------------------------------------------------------------------


def test_mock_search_finds_aapl_by_substring() -> None:
    results = MockProvider().search("app")
    assert "AAPL" in [r.ticker for r in results]
    aapl = next(r for r in results if r.ticker == "AAPL")
    assert aapl.name == "Apple Inc."
    assert aapl.source == "mock"


def test_mock_search_is_case_insensitive_on_ticker_and_name() -> None:
    by_ticker = MockProvider().search("aApL")
    by_name = MockProvider().search("APPLE")
    assert "AAPL" in [r.ticker for r in by_ticker]
    assert "AAPL" in [r.ticker for r in by_name]


def test_mock_search_excludes_testco() -> None:
    provider = MockProvider()
    for query in ("test", "TESTCO", "testco industrials", "t"):
        assert all(r.ticker != "TESTCO" for r in provider.search(query))


def test_mock_search_blank_query_returns_empty() -> None:
    assert MockProvider().search("   ") == []


def test_mock_get_company_testco_loadable_and_case_insensitive() -> None:
    provider = MockProvider()
    bundle = provider.get_company("testco")
    assert bundle.info.ticker == "TESTCO"
    assert bundle.data_source == "Sample data (illustrative figures)"
    assert [y.fiscal_year for y in bundle.financials] == [2021, 2022, 2023, 2024, 2025]
    assert bundle.financials[-1].revenue == pytest.approx(1_000_000_000.0, rel=REL_TOL)


def test_mock_get_company_unknown_ticker_raises() -> None:
    with pytest.raises(CompanyNotFoundError):
        MockProvider().get_company("ZZZZ")


def test_mock_data_path_resolves_from_any_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    bundle = MockProvider().get_company("AAPL")
    assert bundle.info.ticker == "AAPL"


def test_mock_get_company_returns_isolated_copies() -> None:
    provider = MockProvider()
    first = provider.get_company("AAPL")
    first.warnings.append("mutated")
    first.financials[-1].revenue = 1.0
    second = provider.get_company("AAPL")
    assert "mutated" not in second.warnings
    assert second.financials[-1].revenue != 1.0


# ---------------------------------------------------------------------------
# SecEdgarProvider (fixture-driven via MockTransport)
# ---------------------------------------------------------------------------


def _edgar_handler(
    calls: list[str] | None = None,
    *,
    ticker_map_status: int = 200,
    facts_status: int = 200,
) -> Callable[[httpx.Request], httpx.Response]:
    facts_payload = json.loads(EDGAR_FIXTURE.read_text())
    facts_url = COMPANYFACTS_URL.format(cik=FIXTURE_CIK)

    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(str(request.url))
        assert request.headers.get("User-Agent") == TEST_USER_AGENT
        url = str(request.url)
        if url == TICKER_MAP_URL:
            if ticker_map_status != 200:
                return httpx.Response(ticker_map_status, text="error")
            return httpx.Response(200, json=TICKER_MAP_PAYLOAD)
        if url == facts_url:
            if facts_status != 200:
                return httpx.Response(facts_status, text="error")
            return httpx.Response(200, json=facts_payload)
        return httpx.Response(404, json={"detail": "not found"})

    return handler


def _make_edgar(
    cache_dir: Path, handler: Callable[[httpx.Request], httpx.Response]
) -> SecEdgarProvider:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return SecEdgarProvider(TEST_USER_AGENT, client=client, cache_dir=cache_dir)


def test_edgar_requires_user_agent() -> None:
    with pytest.raises(ProviderConfigError):
        SecEdgarProvider("")


def test_edgar_maps_tags_derives_fields_and_warns_on_missing(tmp_path: Path) -> None:
    provider = _make_edgar(tmp_path / "cache", _edgar_handler())
    bundle = provider.get_company("FIXT")

    assert bundle.info.name == "Fixture Manufacturing Corp"
    assert bundle.info.cik == "0001234567"
    assert bundle.data_source == "SEC EDGAR"
    assert [y.fiscal_year for y in bundle.financials] == [2023, 2024]

    fy2024 = bundle.financials[-1]
    assert fy2024.period_end == "2024-12-31"
    # Fallback tags: Revenues (preferred revenue tag absent) and
    # CostOfGoodsAndServicesSold (CostOfRevenue absent).
    assert fy2024.revenue == pytest.approx(500e6, rel=REL_TOL)
    assert fy2024.cost_of_revenue == pytest.approx(300e6, rel=REL_TOL)
    assert fy2024.operating_income == pytest.approx(100e6, rel=REL_TOL)
    assert fy2024.depreciation_amortization == pytest.approx(25e6, rel=REL_TOL)
    assert fy2024.net_income == pytest.approx(60e6, rel=REL_TOL)
    assert fy2024.interest_expense == pytest.approx(10e6, rel=REL_TOL)
    assert fy2024.operating_cash_flow == pytest.approx(110e6, rel=REL_TOL)
    assert fy2024.capex == pytest.approx(30e6, rel=REL_TOL)
    assert fy2024.cash_and_equivalents == pytest.approx(40e6, rel=REL_TOL)
    assert fy2024.current_assets == pytest.approx(120e6, rel=REL_TOL)
    assert fy2024.current_liabilities == pytest.approx(60e6, rel=REL_TOL)
    assert fy2024.total_equity == pytest.approx(250e6, rel=REL_TOL)
    # total_debt = 150m LongTermDebtNoncurrent + 20m DebtCurrent. The fixture
    # also carries LongTermDebtCurrent (18m) which DebtCurrent already includes;
    # it must NOT be added on top (spec §5 non-double-counting rule).
    assert fy2024.total_debt == pytest.approx(170e6, rel=REL_TOL)
    # dei shares: latest entry (2025-01-31) lands on the latest fiscal year.
    assert fy2024.shares_outstanding == pytest.approx(50e6, rel=REL_TOL)

    # Derivations recorded: gross profit, EBITDA, FCF are never tagged in EDGAR.
    assert fy2024.gross_profit == pytest.approx(200e6, rel=REL_TOL)
    assert fy2024.ebitda == pytest.approx(125e6, rel=REL_TOL)
    assert fy2024.free_cash_flow == pytest.approx(80e6, rel=REL_TOL)
    assert set(fy2024.derived_fields) == {"gross_profit", "ebitda", "free_cash_flow"}

    # Missing tag (IncomeTaxExpenseBenefit absent) -> None + spec warning.
    assert fy2024.tax_expense is None
    assert "tax_expense unavailable from SEC EDGAR" in bundle.warnings


def test_edgar_dedupes_by_end_date_preferring_latest_filed(tmp_path: Path) -> None:
    provider = _make_edgar(tmp_path / "cache", _edgar_handler())
    fy2023 = provider.get_company("FIXT").financials[0]
    # FY2023 revenue appears twice for end 2023-12-31: 440m (filed 2024-02-15)
    # and a 450m restatement (filed 2025-02-15). Latest filed must win.
    assert fy2023.revenue == pytest.approx(450e6, rel=REL_TOL)
    assert fy2023.total_debt == pytest.approx(175e6, rel=REL_TOL)
    assert fy2023.ebitda == pytest.approx(107e6, rel=REL_TOL)


def test_edgar_ignores_10q_and_non_annual_periods(tmp_path: Path) -> None:
    provider = _make_edgar(tmp_path / "cache", _edgar_handler())
    revenues = [y.revenue for y in provider.get_company("FIXT").financials]
    # Neither the 10-Q half-year value (240m) nor the quarterly-duration 10-K
    # entry (130m) may leak into annual revenue.
    assert 240e6 not in revenues
    assert 130e6 not in revenues


def test_edgar_ticker_map_cached_in_memory(tmp_path: Path) -> None:
    calls: list[str] = []
    provider = _make_edgar(tmp_path / "cache", _edgar_handler(calls))
    provider.get_company("FIXT")
    provider.get_company("FIXT")
    assert calls.count(TICKER_MAP_URL) == 1


def test_edgar_ticker_map_cached_on_disk(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    _make_edgar(cache_dir, _edgar_handler()).get_company("FIXT")
    assert (cache_dir / "company_tickers.json").is_file()
    # A fresh provider whose transport fails the ticker URL must still resolve
    # the CIK from the on-disk cache.
    second = _make_edgar(cache_dir, _edgar_handler(ticker_map_status=500))
    bundle = second.get_company("FIXT")
    assert bundle.info.cik == "0001234567"


def test_edgar_unknown_ticker_raises_not_found(tmp_path: Path) -> None:
    provider = _make_edgar(tmp_path / "cache", _edgar_handler())
    with pytest.raises(CompanyNotFoundError):
        provider.get_company("ZZZZ")


def test_edgar_http_error_maps_to_provider_error(tmp_path: Path) -> None:
    provider = _make_edgar(tmp_path / "cache", _edgar_handler(facts_status=500))
    with pytest.raises(ProviderError) as excinfo:
        provider.get_company("FIXT")
    assert "HTTP 500" in str(excinfo.value)
    assert "SEC EDGAR" in str(excinfo.value)


def _debt_fact(end: str, val: float) -> dict[str, Any]:
    return {
        "end": end,
        "val": val,
        "fy": int(end[:4]),
        "fp": "FY",
        "form": "10-K",
        "filed": f"{int(end[:4]) + 1}-02-15",
    }


def _debt_tag(*facts: dict[str, Any]) -> dict[str, Any]:
    return {"units": {"USD": list(facts)}}


def test_edgar_total_debt_ignores_ltd_current_when_debt_current_present(
    tmp_path: Path,
) -> None:
    """Fixture has BOTH DebtCurrent and LongTermDebtCurrent for each year; the
    current component must be DebtCurrent alone (no double count)."""
    provider = _make_edgar(tmp_path / "cache", _edgar_handler())
    fy2023, fy2024 = provider.get_company("FIXT").financials
    # 160m + 15m (NOT + 14m LongTermDebtCurrent) and 150m + 20m (NOT + 18m).
    assert fy2023.total_debt == pytest.approx(175e6, rel=REL_TOL)
    assert fy2024.total_debt == pytest.approx(170e6, rel=REL_TOL)


def test_edgar_total_debt_current_component_rule(tmp_path: Path) -> None:
    """§5 rule on synthetic tag maps: DebtCurrent when present, else
    LongTermDebtCurrent + ShortTermBorrowings; fallback LongTermDebt alone."""
    provider = _make_edgar(tmp_path / "cache", _edgar_handler())
    end = "2024-12-31"

    # ELSE branch: no DebtCurrent -> LongTermDebtCurrent + ShortTermBorrowings.
    gaap = {
        "LongTermDebtNoncurrent": _debt_tag(_debt_fact(end, 100e6)),
        "LongTermDebtCurrent": _debt_tag(_debt_fact(end, 10e6)),
        "ShortTermBorrowings": _debt_tag(_debt_fact(end, 5e6)),
    }
    assert provider._total_debt_values(gaap, []) == {end: pytest.approx(115e6)}

    # Both present: DebtCurrent (12m) supersedes the 10m + 5m components.
    gaap["DebtCurrent"] = _debt_tag(_debt_fact(end, 12e6))
    assert provider._total_debt_values(gaap, []) == {end: pytest.approx(112e6)}

    # Fallback: no component tags at all -> LongTermDebt alone.
    fallback_only = {"LongTermDebt": _debt_tag(_debt_fact(end, 90e6))}
    assert provider._total_debt_values(fallback_only, []) == {
        end: pytest.approx(90e6)
    }

    # Nothing present -> empty map + warning.
    warnings: list[str] = []
    assert provider._total_debt_values({}, warnings) == {}
    assert "total_debt unavailable from SEC EDGAR" in warnings


def test_edgar_search_uses_ticker_file(tmp_path: Path) -> None:
    provider = _make_edgar(tmp_path / "cache", _edgar_handler())
    results = provider.search("fixture")
    assert [r.ticker for r in results] == ["FIXT"]
    assert results[0].source == "sec_edgar"
    assert "AAPL" in [r.ticker for r in provider.search("aapl")]


# ---------------------------------------------------------------------------
# FmpProvider (MockTransport)
# ---------------------------------------------------------------------------

FMP_PROFILE = {
    "symbol": "FIXT",
    "companyName": "Fixture Manufacturing Corp",
    "sector": "Industrials",
    "industry": "Industrial Machinery",
    "exchange": "NYSE",
    "exchangeFullName": "New York Stock Exchange",
    "description": "Synthetic fixture company.",
    "cik": "0001234567",
    "price": 25.0,
    "marketCap": 1250000000,
}
FMP_QUOTE = {
    "symbol": "FIXT",
    "name": "Fixture Manufacturing Corp",
    "price": 25.0,
    "marketCap": 1250000000,
    "sharesOutstanding": 50000000,
    "timestamp": 1749600000,  # 2025-06-11 UTC
}
FMP_SEARCH = [
    {
        "symbol": "FIXT",
        "name": "Fixture Manufacturing Corp",
        "currency": "USD",
        "exchangeFullName": "New York Stock Exchange",
        "exchange": "NYSE",
    },
    {
        # Non-US cross-listing: must be filtered out by the provider.
        "symbol": "FIXT.SW",
        "name": "Fixture Manufacturing Corp",
        "currency": "CHF",
        "exchangeFullName": "Swiss Exchange",
        "exchange": "SIX",
    },
]


def _fmp_handler(
    *, status: int = 200, empty: bool = False
) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params.get("apikey") == "test-key"
        if status != 200:
            return httpx.Response(status, json={"Error Message": "denied"})
        path = request.url.path
        if empty:
            return httpx.Response(200, json=[])
        if path == "/stable/profile" and request.url.params.get("symbol") == "FIXT":
            return httpx.Response(200, json=[FMP_PROFILE])
        if path == "/stable/quote" and request.url.params.get("symbol") == "FIXT":
            return httpx.Response(200, json=[FMP_QUOTE])
        if path == "/stable/search-name":
            return httpx.Response(200, json=FMP_SEARCH)
        return httpx.Response(200, json=[])

    return handler


def _make_fmp(handler: Callable[[httpx.Request], httpx.Response]) -> FmpProvider:
    return FmpProvider(
        "test-key", client=httpx.Client(transport=httpx.MockTransport(handler))
    )


def test_fmp_requires_api_key() -> None:
    with pytest.raises(ProviderConfigError):
        FmpProvider(" ")


def test_fmp_profile_maps_to_company_info() -> None:
    profile = _make_fmp(_fmp_handler()).get_profile("fixt")
    assert profile is not None
    assert profile.ticker == "FIXT"
    assert profile.name == "Fixture Manufacturing Corp"
    assert profile.sector == "Industrials"
    assert profile.industry == "Industrial Machinery"
    assert profile.exchange == "NYSE"


def test_fmp_quote_maps_to_market_data() -> None:
    quote = _make_fmp(_fmp_handler()).get_quote("FIXT")
    assert quote is not None
    assert quote.share_price == pytest.approx(25.0, rel=REL_TOL)
    assert quote.market_cap == pytest.approx(1.25e9, rel=REL_TOL)
    assert quote.shares_outstanding == pytest.approx(50e6, rel=REL_TOL)
    assert quote.as_of == "2025-06-11"
    assert quote.source == "Financial Modeling Prep"


def test_fmp_empty_payloads_return_none() -> None:
    provider = _make_fmp(_fmp_handler(empty=True))
    assert provider.get_profile("FIXT") is None
    assert provider.get_quote("FIXT") is None


def test_fmp_search_maps_results() -> None:
    results = _make_fmp(_fmp_handler()).search("fixture")
    assert [r.ticker for r in results] == ["FIXT"]
    assert results[0].exchange == "New York Stock Exchange"
    assert results[0].source == "fmp"


def test_fmp_http_error_maps_to_provider_error() -> None:
    provider = _make_fmp(_fmp_handler(status=401))
    with pytest.raises(ProviderError) as excinfo:
        provider.get_quote("FIXT")
    message = str(excinfo.value)
    assert "Financial Modeling Prep" in message
    assert "test-key" not in message  # never leak the API key


# ---------------------------------------------------------------------------
# CompositeLiveProvider
# ---------------------------------------------------------------------------


def _make_composite(
    tmp_path: Path, *, with_fmp: bool = True, fmp_status: int = 200
) -> CompositeLiveProvider:
    edgar = _make_edgar(tmp_path / "cache", _edgar_handler())
    fmp = _make_fmp(_fmp_handler(status=fmp_status)) if with_fmp else None
    return CompositeLiveProvider(edgar, fmp)


def test_composite_combines_edgar_fundamentals_with_fmp_market(tmp_path: Path) -> None:
    bundle = _make_composite(tmp_path).get_company("FIXT")
    # Fundamentals from EDGAR.
    assert bundle.financials[-1].revenue == pytest.approx(500e6, rel=REL_TOL)
    # Profile fields filled from FMP.
    assert bundle.info.sector == "Industrials"
    assert bundle.info.industry == "Industrial Machinery"
    assert bundle.info.exchange == "NYSE"
    # Market data from FMP.
    assert bundle.market is not None
    assert bundle.market.share_price == pytest.approx(25.0, rel=REL_TOL)
    assert bundle.data_source == "SEC EDGAR + Financial Modeling Prep"


def test_composite_without_fmp_warns_and_keeps_edgar_data(tmp_path: Path) -> None:
    bundle = _make_composite(tmp_path, with_fmp=False).get_company("FIXT")
    assert bundle.market is None
    assert bundle.data_source == "SEC EDGAR"
    assert any(w.startswith("Market data unavailable") for w in bundle.warnings)


def test_composite_fmp_failure_degrades_to_warnings(tmp_path: Path) -> None:
    bundle = _make_composite(tmp_path, fmp_status=500).get_company("FIXT")
    assert bundle.market is None
    assert bundle.financials  # EDGAR fundamentals survive the FMP outage
    assert any(w.startswith("Market data unavailable") for w in bundle.warnings)


def test_composite_search_prefers_fmp_then_falls_back_to_edgar(tmp_path: Path) -> None:
    with_fmp = _make_composite(tmp_path)
    assert [r.source for r in with_fmp.search("fixture")] == ["fmp"]

    no_fmp = _make_composite(tmp_path, with_fmp=False)
    assert [r.source for r in no_fmp.search("fixture")] == ["sec_edgar"]

    broken_fmp = _make_composite(tmp_path, fmp_status=500)
    assert [r.source for r in broken_fmp.search("fixture")] == ["sec_edgar"]


# ---------------------------------------------------------------------------
# Factory (spec §5 mode rules)
# ---------------------------------------------------------------------------


def _settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "data_provider": "auto",
        "sec_edgar_user_agent": "",
        "fmp_api_key": "",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_factory_mock_mode_returns_mock_provider() -> None:
    provider = get_provider(_settings(data_provider="mock", sec_edgar_user_agent="x"))
    assert isinstance(provider, MockProvider)


def test_factory_auto_without_yfinance_or_user_agent_falls_back_to_mock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Spec §5 auto chain: yahoo -> live -> mock. With yfinance unavailable and
    # no SEC_EDGAR_USER_AGENT, auto serves sample data with the mode warning.
    monkeypatch.setattr(
        "app.providers.factory._yfinance_importable", lambda: False
    )
    provider = get_provider(_settings(data_provider="auto"))
    assert isinstance(provider, MockProvider)
    bundle = provider.get_company("TESTCO")
    assert MOCK_MODE_WARNING in bundle.warnings


def test_factory_live_without_user_agent_raises_config_error() -> None:
    with pytest.raises(ProviderConfigError):
        get_provider(_settings(data_provider="live"))


def test_factory_auto_without_yfinance_with_user_agent_returns_live_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.providers.factory._yfinance_importable", lambda: False
    )
    provider = get_provider(
        _settings(data_provider="auto", sec_edgar_user_agent=TEST_USER_AGENT)
    )
    assert isinstance(provider, CompositeLiveProvider)
    assert provider.fmp is None  # no FMP key configured


def test_factory_live_with_user_agent_and_key_wires_fmp() -> None:
    provider = get_provider(
        _settings(
            data_provider="live",
            sec_edgar_user_agent=TEST_USER_AGENT,
            fmp_api_key="test-key",
        )
    )
    assert isinstance(provider, CompositeLiveProvider)
    assert isinstance(provider.fmp, FmpProvider)


def test_edgar_retries_transient_429(monkeypatch, tmp_path) -> None:
    """A 429 followed by success must be retried, not surfaced as an error."""
    import app.providers.edgar as edgar_mod

    monkeypatch.setattr(edgar_mod.time, "sleep", lambda _s: None)
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429, json={})
        return httpx.Response(200, json={"0": {"cik_str": 1, "ticker": "X", "title": "X Corp"}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = SecEdgarProvider("test agent@example.com", client=client, cache_dir=tmp_path)
    assert provider._ticker_map()["0"]["ticker"] == "X"
    assert calls["n"] == 3


def test_edgar_da_component_fallback_sums_split_tags(tmp_path) -> None:
    """Filers with no combined D&A tag (e.g. MSFT) get components summed per year."""
    entry = lambda end, val: {  # noqa: E731 - terse fixture builder
        "form": "10-K", "fp": "FY", "start": str(int(end[:4]) - 1) + end[4:],
        "end": end, "val": val, "filed": end,
    }
    gaap = {
        "Depreciation": {"units": {"USD": [entry("2025-06-30", 22.0e9), entry("2024-06-30", 15.2e9)]}},
        "AmortizationOfIntangibleAssets": {"units": {"USD": [entry("2025-06-30", 6.0e9)]}},
        "FinanceLeaseRightOfUseAssetAmortization": {"units": {"USD": [entry("2025-06-30", 3.408e9)]}},
    }
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404)))
    provider = SecEdgarProvider("test agent@example.com", client=client, cache_dir=tmp_path)
    values, anchor_used = provider._sum_component_values(
        gaap, ["Depreciation", "AmortizationOfIntangibleAssets", "FinanceLeaseRightOfUseAssetAmortization"],
        anchors=["Depreciation"],
    )
    assert anchor_used == "Depreciation"
    assert values["2025-06-30"] == pytest.approx(31.408e9)
    assert values["2024-06-30"] == pytest.approx(15.2e9)  # missing components just absent
    # no anchor -> empty
    assert provider._sum_component_values(
        {"AmortizationOfIntangibleAssets": gaap["AmortizationOfIntangibleAssets"]},
        ["Depreciation", "AmortizationOfIntangibleAssets"], anchors=["Depreciation"],
    ) == ({}, None)
    # §19.8 second anchor (CRWD-class: no Depreciation tag at all) — the
    # amortization components sum, anchored on CapitalizedContractCostAmortization.
    crwd_gaap = {
        "CapitalizedContractCostAmortization": {"units": {"USD": [entry("2026-01-31", 449.413e6)]}},
        "AmortizationOfIntangibleAssets": {"units": {"USD": [entry("2026-01-31", 31.233e6)]}},
        "CapitalizedComputerSoftwareAmortization1": {"units": {"USD": [entry("2026-01-31", 79.6e6)]}},
    }
    values, anchor_used = provider._sum_component_values(
        crwd_gaap,
        ["Depreciation", "AmortizationOfIntangibleAssets",
         "FinanceLeaseRightOfUseAssetAmortization",
         "CapitalizedContractCostAmortization",
         "CapitalizedComputerSoftwareAmortization1"],
        anchors=["Depreciation", "CapitalizedContractCostAmortization"],
    )
    assert anchor_used == "CapitalizedContractCostAmortization"
    assert values["2026-01-31"] == pytest.approx(560.246e6)


def test_edgar_merges_partial_history_across_preference_tags(tmp_path) -> None:
    """A preferred tag with stale partial history must not shadow later tags
    for the periods it misses (e.g. MSFT CostOfRevenue vs CostOfGoodsAndServicesSold)."""
    entry = lambda end, val: {  # noqa: E731
        "form": "10-K", "fp": "FY", "start": str(int(end[:4]) - 1) + end[4:],
        "end": end, "val": val, "filed": end,
    }
    facts = {
        "facts": {
            "us-gaap": {
                "Revenues": {"units": {"USD": [entry("2024-06-30", 100.0), entry("2025-06-30", 120.0)]}},
                # Preferred cost tag stops in 2024; the fallback covers 2025.
                "CostOfRevenue": {"units": {"USD": [entry("2024-06-30", 60.0)]}},
                "CostOfGoodsAndServicesSold": {"units": {"USD": [entry("2024-06-30", 999.0), entry("2025-06-30", 70.0)]}},
            },
            "dei": {},
        },
        "entityName": "Merge Test Corp",
    }
    tickmap = {"0": {"cik_str": 1, "ticker": "MRG", "title": "Merge Test Corp"}}

    def handler(request: httpx.Request) -> httpx.Response:
        if "company_tickers" in str(request.url):
            return httpx.Response(200, json=tickmap)
        return httpx.Response(200, json=facts)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = SecEdgarProvider("test agent@example.com", client=client, cache_dir=tmp_path)
    bundle = provider.get_company("MRG")
    by_year = {y.fiscal_year: y for y in bundle.financials}
    assert by_year[2024].cost_of_revenue == 60.0   # preferred tag wins where present
    assert by_year[2025].cost_of_revenue == 70.0   # fallback fills the gap
    assert any("assembled from multiple SEC tags" in w for w in bundle.warnings)


def test_fmp_search_finds_ticker_via_symbol_endpoint() -> None:
    """'nvda'-style ticker queries must hit search-symbol, not just search-name."""
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params.get("apikey") == "test-key"
        if request.url.path == "/stable/search-symbol":
            return httpx.Response(200, json=[{
                "symbol": "NVDA", "name": "NVIDIA Corporation",
                "exchange": "NASDAQ", "exchangeFullName": "NASDAQ Global Select",
            }])
        if request.url.path == "/stable/search-name":
            return httpx.Response(200, json=[
                {"symbol": "NVDA", "name": "NVIDIA Corporation",
                 "exchange": "NASDAQ", "exchangeFullName": "NASDAQ Global Select"},
                {"symbol": "NVD", "name": "Other Corp", "exchange": "NYSE",
                 "exchangeFullName": "New York Stock Exchange"},
            ])
        return httpx.Response(200, json=[])

    results = _make_fmp(handler).search("nvda")
    assert [r.ticker for r in results] == ["NVDA", "NVD"]  # deduped, symbol hit first


# ---------------------------------------------------------------------------
# §19.7 COHR-class tag fixes: operating-income derivation, InterestPaidNet,
# FMP 429 retry, max_years year-selection cap
# ---------------------------------------------------------------------------


def _annual_fact(end: str, val: float) -> dict[str, Any]:
    """An annual 10-K duration fact (start one year before end)."""
    return {
        "start": str(int(end[:4]) - 1) + end[4:],
        "end": end,
        "val": val,
        "fy": int(end[:4]),
        "fp": "FY",
        "form": "10-K",
        "filed": f"{int(end[:4])}-08-15",
    }


def _usd_tag(*facts: dict[str, Any]) -> dict[str, Any]:
    return {"units": {"USD": list(facts)}}


def _synthetic_edgar(tmp_path: Path, gaap: dict[str, Any]) -> SecEdgarProvider:
    """SecEdgarProvider over synthetic us-gaap facts for ticker SYN."""
    tickmap = {"0": {"cik_str": 777, "ticker": "SYN", "title": "Synthetic Corp"}}
    facts = {"facts": {"us-gaap": gaap, "dei": {}}, "entityName": "Synthetic Corp"}

    def handler(request: httpx.Request) -> httpx.Response:
        if "company_tickers" in str(request.url):
            return httpx.Response(200, json=tickmap)
        return httpx.Response(200, json=facts)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return SecEdgarProvider(TEST_USER_AGENT, client=client, cache_dir=tmp_path / "cache")


# COHR-class FY2025 facts: no OperatingIncomeLoss, GrossProfit, CostOfRevenue
# or InterestExpense; CostsAndExpenses and InterestPaidNet ARE filed.
_COHR_LIKE_GAAP: dict[str, Any] = {
    "RevenueFromContractWithCustomerExcludingAssessedTax": _usd_tag(
        _annual_fact("2025-06-30", 5.810115e9)
    ),
    "CostsAndExpenses": _usd_tag(_annual_fact("2025-06-30", 5.715934e9)),
    "CostOfGoodsAndServicesSold": _usd_tag(_annual_fact("2025-06-30", 3.766793e9)),
    "DepreciationAndAmortization": _usd_tag(_annual_fact("2025-06-30", 5.53598e8)),
    "InterestPaidNet": _usd_tag(_annual_fact("2025-06-30", 2.56704e8)),
    "NetIncomeLoss": _usd_tag(_annual_fact("2025-06-30", -0.064e9)),
}


def test_edgar_operating_income_derived_from_costs_and_expenses(tmp_path: Path) -> None:
    """No operating-income tag + CostsAndExpenses -> per-period derivation,
    derived_fields entry, the §19.7 warning, and EBITDA derives on top."""
    bundle = _synthetic_edgar(tmp_path, _COHR_LIKE_GAAP).get_company("SYN")
    (fy2025,) = bundle.financials
    assert fy2025.fiscal_year == 2025
    # operating_income = revenue - CostsAndExpenses.
    assert fy2025.operating_income == pytest.approx(94.181e6, rel=REL_TOL)
    assert "operating_income" in fy2025.derived_fields
    # EBITDA then derives normally from the derived operating income.
    assert fy2025.ebitda == pytest.approx(94.181e6 + 553.598e6, rel=REL_TOL)
    assert "ebitda" in fy2025.derived_fields
    # Exact §19.7 warning text, and no contradictory "unavailable" warning.
    assert (
        "operating_income derived as revenue − total costs and expenses "
        "(no operating income tag filed)"
    ) in bundle.warnings
    assert OPERATING_INCOME_DERIVED_WARNING in bundle.warnings
    assert "operating_income unavailable from SEC EDGAR" not in bundle.warnings


def test_edgar_interest_paid_net_fallback(tmp_path: Path) -> None:
    """InterestPaidNet fills periods the income-statement tags miss (COHR
    files no InterestExpense at all in FY2025) without overriding them."""
    bundle = _synthetic_edgar(tmp_path, _COHR_LIKE_GAAP).get_company("SYN")
    assert bundle.financials[-1].interest_expense == pytest.approx(
        2.56704e8, rel=REL_TOL
    )
    # interest_expense is reported (cash proxy), not derived.
    assert "interest_expense" not in bundle.financials[-1].derived_fields

    # Per-period merge: a real IS tag keeps its periods, InterestPaidNet only
    # fills the gaps (999m sentinel must never override 15m).
    gaap = dict(_COHR_LIKE_GAAP)
    gaap["InterestExpense"] = _usd_tag(_annual_fact("2024-06-30", 15e6))
    gaap["InterestPaidNet"] = _usd_tag(
        _annual_fact("2024-06-30", 999e6), _annual_fact("2025-06-30", 2.56704e8)
    )
    bundle = _synthetic_edgar(tmp_path / "merge", gaap).get_company("SYN")
    by_year = {y.fiscal_year: y for y in bundle.financials}
    assert by_year[2024].interest_expense == pytest.approx(15e6, rel=REL_TOL)
    assert by_year[2025].interest_expense == pytest.approx(2.56704e8, rel=REL_TOL)
    assert any(
        "interest_expense assembled from multiple SEC tags" in w
        for w in bundle.warnings
    )


def test_edgar_operating_income_derivation_only_fills_missing_periods(
    tmp_path: Path,
) -> None:
    """A filed OperatingIncomeLoss period is never overwritten; only the
    period the tag misses is derived (and only that row is marked derived)."""
    gaap = {
        "Revenues": _usd_tag(
            _annual_fact("2024-06-30", 4.0e9), _annual_fact("2025-06-30", 5.0e9)
        ),
        "OperatingIncomeLoss": _usd_tag(_annual_fact("2024-06-30", 0.8e9)),
        "CostsAndExpenses": _usd_tag(
            _annual_fact("2024-06-30", 999e9),  # sentinel: must not be used
            _annual_fact("2025-06-30", 4.7e9),
        ),
    }
    bundle = _synthetic_edgar(tmp_path, gaap).get_company("SYN")
    by_year = {y.fiscal_year: y for y in bundle.financials}
    assert by_year[2024].operating_income == pytest.approx(0.8e9, rel=REL_TOL)
    assert "operating_income" not in by_year[2024].derived_fields
    assert by_year[2025].operating_income == pytest.approx(0.3e9, rel=REL_TOL)
    assert "operating_income" in by_year[2025].derived_fields
    assert OPERATING_INCOME_DERIVED_WARNING in bundle.warnings


def test_edgar_operating_income_opex_fallback(tmp_path: Path) -> None:
    """Without CostsAndExpenses the derivation falls back to gross_profit −
    OperatingExpenses, with its own warning."""
    gaap = {
        "Revenues": _usd_tag(_annual_fact("2025-12-31", 500e6)),
        "GrossProfit": _usd_tag(_annual_fact("2025-12-31", 200e6)),
        "OperatingExpenses": _usd_tag(_annual_fact("2025-12-31", 120e6)),
    }
    bundle = _synthetic_edgar(tmp_path, gaap).get_company("SYN")
    (fy2025,) = bundle.financials
    assert fy2025.operating_income == pytest.approx(80e6, rel=REL_TOL)
    assert "operating_income" in fy2025.derived_fields
    assert OPERATING_INCOME_DERIVED_FROM_OPEX_WARNING in bundle.warnings
    assert OPERATING_INCOME_DERIVED_WARNING not in bundle.warnings


def test_edgar_no_derivation_inputs_keeps_unavailable_warning(tmp_path: Path) -> None:
    """No operating-income tag and no derivation inputs -> None + the spec
    'unavailable' warning, never the derived warning."""
    gaap = {"Revenues": _usd_tag(_annual_fact("2025-12-31", 500e6))}
    bundle = _synthetic_edgar(tmp_path, gaap).get_company("SYN")
    assert bundle.financials[-1].operating_income is None
    assert "operating_income unavailable from SEC EDGAR" in bundle.warnings
    assert OPERATING_INCOME_DERIVED_WARNING not in bundle.warnings


def test_edgar_max_years_caps_at_year_selection(tmp_path: Path) -> None:
    """get_company keeps the 5-year default; max_years widens (or narrows)
    the window at year-selection (§19.7 statements path asks for 15)."""
    gaap = {
        "Revenues": _usd_tag(
            *[_annual_fact(f"{fy}-12-31", fy * 1e6) for fy in range(2019, 2026)]
        )
    }
    provider = _synthetic_edgar(tmp_path, gaap)
    default_years = provider.get_company("SYN").financials
    assert [y.fiscal_year for y in default_years] == [2021, 2022, 2023, 2024, 2025]
    full_years = provider.get_company("SYN", max_years=15).financials
    assert [y.fiscal_year for y in full_years] == list(range(2019, 2026))
    assert [y.fiscal_year for y in provider.get_company("SYN", max_years=2).financials] == [
        2024,
        2025,
    ]


def test_fmp_retries_transient_429(monkeypatch: pytest.MonkeyPatch) -> None:
    """A 429 followed by success must be retried (2s/4s backoff), mirroring
    the EDGAR retry; time.sleep is monkeypatched, never actually slept."""
    import app.providers.fmp as fmp_mod

    sleeps: list[float] = []
    monkeypatch.setattr(fmp_mod.time, "sleep", sleeps.append)
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params.get("apikey") == "test-key"
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429, json={})
        return httpx.Response(200, json=[FMP_QUOTE])

    quote = _make_fmp(handler).get_quote("FIXT")
    assert quote is not None
    assert quote.share_price == pytest.approx(25.0, rel=REL_TOL)
    assert calls["n"] == 3
    assert sleeps == [2.0, 4.0]


def test_fmp_429_exhausted_raises_readable_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.providers.fmp as fmp_mod

    monkeypatch.setattr(fmp_mod.time, "sleep", lambda _s: None)
    provider = _make_fmp(lambda request: httpx.Response(429, json={}))
    with pytest.raises(ProviderError) as excinfo:
        provider.get_quote("FIXT")
    message = str(excinfo.value)
    assert "HTTP 429" in message
    assert "test-key" not in message  # never leak the API key
