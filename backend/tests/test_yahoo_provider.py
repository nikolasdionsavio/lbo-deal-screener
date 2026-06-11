"""YahooProvider / YahooCompositeProvider / factory / cache refresh (spec §4, §5).

No live network: yfinance is replaced by small fake Ticker/Search classes and
inline pandas DataFrames; the EDGAR side reuses the httpx.MockTransport
fixture wiring from tests.test_providers.
"""

import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.db.models  # noqa: F401  (register tables on Base.metadata)
from app.core.config import Settings
from app.crud.companies import MARKET_NOT_CACHED_WARNING, upsert_company
from app.db.base import Base
from app.providers.base import DataProvider
from app.providers.exceptions import (
    CompanyNotFoundError,
    ProviderConfigError,
    ProviderError,
)
from app.providers.factory import get_provider
from app.providers.yahoo import (
    DATA_SOURCE,
    UNOFFICIAL_ENDPOINTS_WARNING,
    YahooProvider,
)
from app.providers.yahoo_composite import COMBINED_DATA_SOURCE, YahooCompositeProvider
from app.schemas.company import CompanyDataBundle, MarketData, SearchResult
from app.services import company_service
from tests.test_providers import TEST_USER_AGENT, _edgar_handler, _make_edgar

REL_TOL = 1e-6

# ---------------------------------------------------------------------------
# Fake yfinance objects (inline pandas DataFrames as fixtures)
# ---------------------------------------------------------------------------

_FY2024 = pd.Timestamp("2024-12-28")
_FY2025 = pd.Timestamp("2025-12-27")
_COLUMNS = [_FY2025, _FY2024]  # yfinance returns newest-first columns


def _frame(rows: dict[str, list[float | None]]) -> pd.DataFrame:
    return pd.DataFrame.from_dict(rows, orient="index", columns=_COLUMNS)


# Income statement: includes the preferred labels, but NO "Gross Profit" row
# (derived by normalization) and NO "Interest Expense" row (missing-row warning).
_INCOME = _frame(
    {
        "Total Revenue": [1_000e6, 900e6],
        "Cost Of Revenue": [600e6, 540e6],
        "Operating Income": [200e6, 180e6],
        "Tax Provision": [45e6, 40e6],
        "Net Income": [135e6, 120e6],
    }
)

# Cashflow: D&A and OCF only present under their FALLBACK labels; capex is
# negative as Yahoo reports it (must be stored positive).
_CASHFLOW = _frame(
    {
        "Depreciation And Amortization": [50e6, 45e6],
        "Cash Flow From Continuing Operating Activities": [230e6, 205e6],
        "Capital Expenditure": [-50e6, -45e6],
    }
)

# Balance sheet: total equity only under its fallback label "Common Stock Equity".
_BALANCE = _frame(
    {
        "Cash And Cash Equivalents": [100e6, 90e6],
        "Total Debt": [400e6, 420e6],
        "Current Assets": [300e6, 280e6],
        "Current Liabilities": [150e6, 140e6],
        "Common Stock Equity": [500e6, 460e6],
    }
)

_BASE_INFO: dict[str, Any] = {
    "longName": "Fake Industrials Inc",
    "sector": "Industrials",
    "industry": "Industrial Machinery",
    "exchange": "NYQ",
    "fullExchangeName": "NYSE",
    "longBusinessSummary": "A synthetic fake company for tests.",
    "currency": "USD",
    "financialCurrency": "USD",
    "currentPrice": 13.5,
    "marketCap": 1_350e6,
    "sharesOutstanding": 100e6,
}


def _ticker_data(info: dict[str, Any] | None = None, **overrides: Any) -> dict[str, Any]:
    data = {
        "income_stmt": _INCOME,
        "balance_sheet": _BALANCE,
        "cashflow": _CASHFLOW,
        "info": dict(_BASE_INFO) if info is None else info,
    }
    data.update(overrides)
    return data


class YFRateLimitError(Exception):
    """Mimics yfinance.exceptions.YFRateLimitError (matched by class name)."""


class FakeTicker:
    registry: dict[str, dict[str, Any]] = {}

    def __init__(self, symbol: str) -> None:
        self._data = self.registry.get(symbol.upper(), {})

    def _get(self, key: str) -> Any:
        value = self._data.get(key)
        if isinstance(value, Exception):
            raise value
        return value

    @property
    def income_stmt(self) -> Any:
        return self._get("income_stmt")

    @property
    def balance_sheet(self) -> Any:
        return self._get("balance_sheet")

    @property
    def cashflow(self) -> Any:
        return self._get("cashflow")

    @property
    def info(self) -> Any:
        return self._get("info")

    @property
    def fast_info(self) -> Any:
        return self._get("fast_info")


def make_provider(
    tickers: dict[str, dict[str, Any]],
    search_quotes: list[dict[str, Any]] | None = None,
) -> YahooProvider:
    class _Search:
        def __init__(self, query: str, max_results: int = 8, **kwargs: Any) -> None:
            self.quotes = list(search_quotes or [])

    ticker_cls = type("FakeTickerBound", (FakeTicker,), {"registry": dict(tickers)})
    module = types.SimpleNamespace(Ticker=ticker_cls, Search=_Search)
    return YahooProvider(yf_module=module)


# ---------------------------------------------------------------------------
# Fundamentals mapping
# ---------------------------------------------------------------------------


def test_yahoo_row_mapping_with_fallback_labels_and_derivations() -> None:
    bundle = make_provider({"FAKE": _ticker_data()}).get_company("FAKE")

    assert bundle.data_source == DATA_SOURCE
    assert UNOFFICIAL_ENDPOINTS_WARNING in bundle.warnings
    assert [y.fiscal_year for y in bundle.financials] == [2024, 2025]

    latest = bundle.financials[-1]
    assert latest.period_end == "2025-12-27"  # fiscal year = column end-date year
    assert latest.revenue == pytest.approx(1_000e6, rel=REL_TOL)
    assert latest.cost_of_revenue == pytest.approx(600e6, rel=REL_TOL)
    assert latest.operating_income == pytest.approx(200e6, rel=REL_TOL)
    assert latest.tax_expense == pytest.approx(45e6, rel=REL_TOL)
    assert latest.net_income == pytest.approx(135e6, rel=REL_TOL)
    # Fallback labels: D&A, OCF and total equity were only present under
    # second-preference row labels.
    assert latest.depreciation_amortization == pytest.approx(50e6, rel=REL_TOL)
    assert latest.operating_cash_flow == pytest.approx(230e6, rel=REL_TOL)
    assert latest.total_equity == pytest.approx(500e6, rel=REL_TOL)
    # Capex reported negative by Yahoo, stored positive.
    assert latest.capex == pytest.approx(50e6, rel=REL_TOL)
    assert latest.cash_and_equivalents == pytest.approx(100e6, rel=REL_TOL)
    assert latest.total_debt == pytest.approx(400e6, rel=REL_TOL)

    # §4 normalization after mapping: gross profit, EBITDA, FCF derived.
    assert latest.gross_profit == pytest.approx(400e6, rel=REL_TOL)
    assert latest.ebitda == pytest.approx(250e6, rel=REL_TOL)
    assert latest.free_cash_flow == pytest.approx(180e6, rel=REL_TOL)
    assert {"gross_profit", "ebitda", "free_cash_flow"} <= set(latest.derived_fields)


def test_yahoo_missing_row_warnings() -> None:
    bundle = make_provider({"FAKE": _ticker_data()}).get_company("FAKE")
    # "Interest Expense" row absent -> None + warning; "Gross Profit" row
    # absent -> warned as unavailable, then derived by normalization.
    assert bundle.financials[-1].interest_expense is None
    assert "interest_expense unavailable from Yahoo Finance" in bundle.warnings
    assert "gross_profit unavailable from Yahoo Finance" in bundle.warnings


def test_yahoo_total_debt_component_fallback() -> None:
    balance = _frame(
        {
            "Long Term Debt": [300e6, 320e6],
            "Current Debt": [100e6, 100e6],
            "Cash And Cash Equivalents": [100e6, 90e6],
        }
    )
    bundle = make_provider(
        {"FAKE": _ticker_data(balance_sheet=balance)}
    ).get_company("FAKE")
    assert bundle.financials[-1].total_debt == pytest.approx(400e6, rel=REL_TOL)

    # No debt rows at all -> None + warning.
    no_debt = _frame({"Cash And Cash Equivalents": [100e6, 90e6]})
    bundle = make_provider(
        {"FAKE": _ticker_data(balance_sheet=no_debt)}
    ).get_company("FAKE")
    assert bundle.financials[-1].total_debt is None
    assert "total_debt unavailable from Yahoo Finance" in bundle.warnings


# ---------------------------------------------------------------------------
# Market data, GBp normalization, market-cap cross-check, currencies
# ---------------------------------------------------------------------------


def test_yahoo_gbp_pence_normalization() -> None:
    info = dict(_BASE_INFO)
    info.update(
        {
            "currency": "GBp",
            "financialCurrency": "GBP",
            "currentPrice": 250.0,  # pence
            "sharesOutstanding": 7e9,
            "marketCap": 17.5e9,  # Yahoo reports GBP pounds for LSE market cap
        }
    )
    bundle = make_provider({"TSCO.L": _ticker_data(info=info)}).get_company("TSCO.L")
    market = bundle.market
    assert market is not None
    assert market.share_price == pytest.approx(2.50, rel=REL_TOL)
    assert market.currency == "GBP"
    assert market.market_cap == pytest.approx(17.5e9, rel=REL_TOL)
    assert bundle.currency == "GBP"  # financialCurrency


def test_yahoo_market_cap_cross_check_within_tolerance_keeps_reported() -> None:
    info = dict(_BASE_INFO)
    info["marketCap"] = 1_360e6  # within 5% of 13.5 x 100m = 1,350m
    bundle = make_provider({"FAKE": _ticker_data(info=info)}).get_company("FAKE")
    assert bundle.market is not None
    assert bundle.market.market_cap == pytest.approx(1_360e6, rel=REL_TOL)
    assert not any("market cap differs" in w.lower() for w in bundle.warnings)


def test_yahoo_market_cap_cross_check_replaces_reported_when_off() -> None:
    info = dict(_BASE_INFO)
    info["marketCap"] = 2_000e6  # >5% away from computed 1,350m
    bundle = make_provider({"FAKE": _ticker_data(info=info)}).get_company("FAKE")
    assert bundle.market is not None
    assert bundle.market.market_cap == pytest.approx(1_350e6, rel=REL_TOL)
    assert any(
        "market cap differs from share price" in w.lower() for w in bundle.warnings
    )


def test_yahoo_currency_mismatch_detected_and_profile_ev_suppressed() -> None:
    # Quoted in pence (-> GBP) but reporting in USD: EV must be suppressed
    # with the exact spec §4 warning; market cap stays visible.
    info = dict(_BASE_INFO)
    info.update(
        {
            "currency": "GBp",
            "financialCurrency": "USD",
            "currentPrice": 250.0,
            "sharesOutstanding": 100e6,
            "marketCap": 250e6,
        }
    )
    bundle = make_provider({"MIX.L": _ticker_data(info=info)}).get_company("MIX.L")
    assert bundle.market is not None and bundle.market.currency == "GBP"
    assert bundle.currency == "USD"

    profile = company_service.build_profile(bundle)
    assert profile.currency == "USD"
    assert profile.enterprise_value is None
    assert profile.market_cap is not None  # shown but flagged
    assert (
        "Quote currency (GBP) differs from reporting currency (USD); "
        "mixed currency multiples suppressed (no FX conversion in MVP)"
    ) in profile.warnings


def test_yahoo_profile_ev_computed_when_currencies_match() -> None:
    bundle = make_provider({"FAKE": _ticker_data()}).get_company("FAKE")
    profile = company_service.build_profile(bundle)
    assert profile.currency == "USD"
    # EV = 1,350m market cap + (400m debt - 100m cash) = 1,650m.
    assert profile.enterprise_value == pytest.approx(1_650e6, rel=REL_TOL)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


def test_yahoo_search_filters_to_equities_and_caps_at_eight() -> None:
    quotes = [
        {
            "symbol": "TSCO.L",
            "shortname": "Tesco PLC",
            "exchDisp": "London",
            "quoteType": "EQUITY",
        },
        {
            "symbol": "TSCOX",
            "shortname": "Some Fund",
            "exchDisp": "NASDAQ",
            "quoteType": "MUTUALFUND",
        },
        {"shortname": "No Symbol", "quoteType": "EQUITY"},
    ] + [
        {
            "symbol": f"EQ{i}",
            "shortname": f"Equity {i}",
            "exchDisp": "NYSE",
            "quoteType": "EQUITY",
        }
        for i in range(10)
    ]
    results = make_provider({}, search_quotes=quotes).search("tesco")
    assert len(results) == 8  # top 8 equities only
    assert results[0] == SearchResult(
        ticker="TSCO.L", name="Tesco PLC", exchange="London", source="yahoo"
    )
    assert all("TSCOX" != r.ticker for r in results)


def test_yahoo_search_blank_query_returns_empty() -> None:
    assert make_provider({}).search("   ") == []


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


def test_yahoo_unknown_symbol_raises_not_found() -> None:
    empty = {
        "income_stmt": pd.DataFrame(),
        "balance_sheet": pd.DataFrame(),
        "cashflow": pd.DataFrame(),
        "info": {"trailingPegRatio": None},
    }
    provider = make_provider({"ZZZZ": empty})
    with pytest.raises(CompanyNotFoundError):
        provider.get_company("ZZZZ")
    with pytest.raises(CompanyNotFoundError):
        provider.get_company("NOTINREGISTRY")


def test_yahoo_rate_limit_raises_provider_error() -> None:
    limited = _ticker_data(
        income_stmt=YFRateLimitError("Too Many Requests. Rate limited.")
    )
    provider = make_provider({"FAKE": limited})
    with pytest.raises(ProviderError) as excinfo:
        provider.get_company("FAKE")
    assert not isinstance(excinfo.value, CompanyNotFoundError)
    assert "rate limited" in str(excinfo.value).lower()


# ---------------------------------------------------------------------------
# YahooCompositeProvider: EDGAR enrichment (reuses the EDGAR fixture wiring)
# ---------------------------------------------------------------------------


def _fixt_yahoo_provider() -> YahooProvider:
    info = dict(_BASE_INFO)
    info.update({"longName": "Fixture Manufacturing Corp", "currentPrice": 25.0,
                 "marketCap": 1_250e6, "sharesOutstanding": 50e6})
    return make_provider({"FIXT": _ticker_data(info=info)})


def test_composite_us_ticker_merges_edgar_fundamentals(tmp_path: Path) -> None:
    edgar = _make_edgar(tmp_path / "cache", _edgar_handler())
    provider = YahooCompositeProvider(_fixt_yahoo_provider(), edgar)
    bundle = provider.get_company("FIXT")

    assert bundle.data_source == COMBINED_DATA_SOURCE
    assert bundle.currency == "USD"
    # Fundamentals from EDGAR (fixture FY2024 revenue 500m, not Yahoo's 1,000m).
    assert bundle.financials[-1].revenue == pytest.approx(500e6, rel=REL_TOL)
    assert bundle.info.cik == "0001234567"
    # Market/profile from Yahoo.
    assert bundle.market is not None
    assert bundle.market.share_price == pytest.approx(25.0, rel=REL_TOL)
    assert bundle.info.sector == "Industrials"
    # EDGAR warnings carried over; the unofficial-endpoints warning retained.
    assert UNOFFICIAL_ENDPOINTS_WARNING in bundle.warnings
    assert "tax_expense unavailable from SEC EDGAR" in bundle.warnings


def test_composite_edgar_failure_falls_back_to_yahoo_fundamentals(
    tmp_path: Path,
) -> None:
    edgar = _make_edgar(tmp_path / "cache", _edgar_handler(facts_status=500))
    provider = YahooCompositeProvider(_fixt_yahoo_provider(), edgar)
    bundle = provider.get_company("FIXT")

    assert bundle.data_source == DATA_SOURCE  # pure Yahoo
    assert bundle.financials[-1].revenue == pytest.approx(1_000e6, rel=REL_TOL)
    assert any(
        w.startswith("SEC EDGAR fundamentals unavailable") for w in bundle.warnings
    )


def test_composite_non_us_ticker_uses_yahoo_entirely(tmp_path: Path) -> None:
    calls: list[str] = []
    edgar = _make_edgar(tmp_path / "cache", _edgar_handler(calls))
    info = dict(_BASE_INFO)
    info.update({"currency": "GBp", "financialCurrency": "GBP", "currentPrice": 250.0})
    yahoo = make_provider({"TSCO.L": _ticker_data(info=info)})
    bundle = YahooCompositeProvider(yahoo, edgar).get_company("TSCO.L")
    assert bundle.data_source == DATA_SOURCE
    assert bundle.currency == "GBP"
    assert calls == []  # EDGAR never touched for suffixed tickers


def test_composite_without_edgar_uses_yahoo_for_us_tickers() -> None:
    provider = YahooCompositeProvider(make_provider({"FAKE": _ticker_data()}), None)
    bundle = provider.get_company("FAKE")
    assert bundle.data_source == DATA_SOURCE
    assert bundle.financials[-1].revenue == pytest.approx(1_000e6, rel=REL_TOL)


# ---------------------------------------------------------------------------
# Factory (spec §5 yahoo/auto rules)
# ---------------------------------------------------------------------------


def _settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "data_provider": "auto",
        "sec_edgar_user_agent": "",
        "fmp_api_key": "",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_factory_yahoo_mode_returns_yahoo_composite() -> None:
    provider = get_provider(_settings(data_provider="yahoo"))
    assert isinstance(provider, YahooCompositeProvider)
    assert provider.edgar is None  # no user agent configured


def test_factory_yahoo_mode_wires_edgar_when_user_agent_set() -> None:
    provider = get_provider(
        _settings(data_provider="yahoo", sec_edgar_user_agent=TEST_USER_AGENT)
    )
    assert isinstance(provider, YahooCompositeProvider)
    assert provider.edgar is not None


def test_factory_yahoo_mode_without_yfinance_raises_config_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.providers.factory._yfinance_importable", lambda: False
    )
    with pytest.raises(ProviderConfigError):
        get_provider(_settings(data_provider="yahoo"))


def test_factory_auto_prefers_yahoo_when_yfinance_importable() -> None:
    provider = get_provider(_settings(data_provider="auto"))
    assert isinstance(provider, YahooCompositeProvider)


# ---------------------------------------------------------------------------
# §11 cache-hit market refresh via the provider hook
# ---------------------------------------------------------------------------


class _CacheOnlyProvider(DataProvider):
    """Provider stub: get_company must never be called on a fresh cache hit."""

    name = "stub"

    def __init__(self, quote: MarketData | None) -> None:
        self.quote = quote
        self.refresh_calls: list[str] = []
        self.get_company_calls = 0

    def search(self, query: str) -> list[SearchResult]:
        return []

    def get_company(self, ticker: str) -> CompanyDataBundle:
        self.get_company_calls += 1
        raise AssertionError("get_company must not be called on a cache hit")

    def refresh_market(self, ticker: str) -> MarketData | None:
        self.refresh_calls.append(ticker)
        return self.quote


@pytest.fixture()
def db_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()


def test_cache_hit_uses_refresh_market_hook_and_keeps_currency(
    db_session: Session, testco_bundle: CompanyDataBundle
) -> None:
    testco_bundle.fetched_at = datetime.now(timezone.utc).isoformat()  # fresh cache
    testco_bundle.currency = "GBP"  # prove the cache round-trips the currency
    upsert_company(db_session, testco_bundle)

    quote = MarketData(
        share_price=14.25,
        market_cap=1_425e6,
        shares_outstanding=100e6,
        as_of="2026-06-11",
        source=DATA_SOURCE,
        currency="GBP",
    )
    provider = _CacheOnlyProvider(quote)
    bundle = company_service.get_bundle("TESTCO", db_session, provider)

    assert provider.refresh_calls == ["TESTCO"]
    assert provider.get_company_calls == 0
    assert bundle.currency == "GBP"
    assert bundle.market is not None
    assert bundle.market.share_price == pytest.approx(14.25, rel=REL_TOL)
    assert MARKET_NOT_CACHED_WARNING not in bundle.warnings


def test_cache_hit_with_no_refresh_result_keeps_warning(
    db_session: Session, testco_bundle: CompanyDataBundle
) -> None:
    testco_bundle.fetched_at = datetime.now(timezone.utc).isoformat()  # fresh cache
    upsert_company(db_session, testco_bundle)
    provider = _CacheOnlyProvider(None)
    bundle = company_service.get_bundle("TESTCO", db_session, provider)
    assert bundle.market is None
    assert MARKET_NOT_CACHED_WARNING in bundle.warnings


def test_yahoo_refresh_market_uses_fast_info_with_gbp_normalization() -> None:
    fast = types.SimpleNamespace(
        last_price=250.0, market_cap=17.5e9, shares=7e9, currency="GBp"
    )
    provider = make_provider({"TSCO.L": {"fast_info": fast}})
    quote = provider.refresh_market("TSCO.L")
    assert quote is not None
    assert quote.share_price == pytest.approx(2.50, rel=REL_TOL)
    assert quote.currency == "GBP"
    assert quote.market_cap == pytest.approx(17.5e9, rel=REL_TOL)
    assert quote.source == DATA_SOURCE
