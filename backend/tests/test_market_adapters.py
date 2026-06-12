"""Market-data adapters: Polygon, Alpha Vantage, Tiingo, the keyless Yahoo
quote tail + the live chain (spec §19.4).

No live network calls: all HTTP goes through httpx.MockTransport and yfinance
is replaced by a fake module. Every error path asserts the API key never
leaks into ProviderError messages.
"""

import types
from typing import Any, Callable

import httpx
import pytest

from app.core.config import Settings
from app.providers.alphavantage import AlphaVantageProvider
from app.providers.exceptions import ProviderConfigError, ProviderError
from app.providers.factory import get_provider
from app.providers.fmp import FmpProvider
from app.providers.live import CompositeLiveProvider
from app.providers.polygon import PolygonProvider
from app.providers.tiingo import TiingoProvider
from app.providers.yahoo import DATA_SOURCE as YAHOO_DATA_SOURCE
from app.providers.yahoo_quote import YahooQuoteProvider
from app.schemas.company import CompanyDataBundle, CompanyInfo

REL_TOL = 1e-6
TEST_KEY = "test-key"
Handler = Callable[[httpx.Request], httpx.Response]


def _client(handler: Handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


# ---------------------------------------------------------------------------
# PolygonProvider
# ---------------------------------------------------------------------------

POLYGON_PREV = {
    "ticker": "FIXT",
    "queryCount": 1,
    "resultsCount": 1,
    "adjusted": True,
    # t is in milliseconds: 2025-06-11 UTC.
    "results": [{"T": "FIXT", "c": 25.0, "o": 24.5, "t": 1749600000000}],
    "status": "OK",
}
POLYGON_REFERENCE = {
    "results": {
        "ticker": "FIXT",
        "name": "Fixture Manufacturing Corp",
        "market_cap": 1250000000,
        "weighted_shares_outstanding": 50000000,
    },
    "status": "OK",
}


def _polygon_handler(
    calls: list[str] | None = None,
    *,
    prev_status: int = 200,
    ref_status: int = 200,
    empty: bool = False,
) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(request.url.path)
        assert request.url.params.get("apiKey") == TEST_KEY
        if request.url.path == "/v2/aggs/ticker/FIXT/prev":
            if prev_status != 200:
                return httpx.Response(prev_status, json={"status": "ERROR"})
            if empty:
                return httpx.Response(
                    200, json={"resultsCount": 0, "results": [], "status": "OK"}
                )
            return httpx.Response(200, json=POLYGON_PREV)
        if request.url.path == "/v3/reference/tickers/FIXT":
            if ref_status != 200:
                return httpx.Response(ref_status, json={"status": "ERROR"})
            return httpx.Response(200, json=POLYGON_REFERENCE)
        return httpx.Response(404, json={"status": "NOT_FOUND"})

    return handler


def _make_polygon(handler: Handler) -> PolygonProvider:
    return PolygonProvider(TEST_KEY, client=_client(handler))


def test_polygon_requires_api_key() -> None:
    with pytest.raises(ProviderConfigError):
        PolygonProvider(" ")


def test_polygon_quote_combines_prev_close_and_reference_data() -> None:
    quote = _make_polygon(_polygon_handler()).get_quote("fixt")
    assert quote is not None
    assert quote.share_price == pytest.approx(25.0, rel=REL_TOL)
    assert quote.market_cap == pytest.approx(1.25e9, rel=REL_TOL)
    assert quote.shares_outstanding == pytest.approx(50e6, rel=REL_TOL)
    assert quote.as_of == "2025-06-11"
    assert quote.source == "Polygon.io"
    assert quote.currency == "USD"


def test_polygon_reference_failure_degrades_to_quote_only() -> None:
    quote = _make_polygon(_polygon_handler(ref_status=500)).get_quote("FIXT")
    assert quote is not None
    assert quote.share_price == pytest.approx(25.0, rel=REL_TOL)
    assert quote.market_cap is None
    assert quote.shares_outstanding is None
    assert quote.source == "Polygon.io"


def test_polygon_empty_results_return_none() -> None:
    provider = _make_polygon(_polygon_handler(empty=True))
    assert provider.get_quote("FIXT") is None


def test_polygon_http_error_maps_to_provider_error_without_key() -> None:
    provider = _make_polygon(_polygon_handler(prev_status=401))
    with pytest.raises(ProviderError) as excinfo:
        provider.get_quote("FIXT")
    message = str(excinfo.value)
    assert "Polygon" in message
    assert "401" in message
    assert TEST_KEY not in message  # never leak the API key


# ---------------------------------------------------------------------------
# AlphaVantageProvider
# ---------------------------------------------------------------------------

AV_QUOTE = {
    "Global Quote": {
        "01. symbol": "FIXT",
        "05. price": "25.0000",
        "07. latest trading day": "2025-06-11",
    }
}
AV_OVERVIEW = {
    "Symbol": "FIXT",
    "MarketCapitalization": "1250000000",
    "SharesOutstanding": "50000000",
}
AV_RATE_LIMIT_NOTE = {
    "Note": "Thank you for using Alpha Vantage! Our standard API rate limit is "
    "25 requests per day."
}


def _av_handler(
    calls: list[str] | None = None,
    *,
    quote_status: int = 200,
    quote_payload: dict[str, Any] | None = None,
    overview_status: int = 200,
    overview_payload: dict[str, Any] | None = None,
) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        function = request.url.params.get("function")
        if calls is not None:
            calls.append(str(function))
        assert request.url.params.get("apikey") == TEST_KEY
        if function == "GLOBAL_QUOTE":
            if quote_status != 200:
                return httpx.Response(quote_status, json={})
            payload = AV_QUOTE if quote_payload is None else quote_payload
            return httpx.Response(200, json=payload)
        if function == "OVERVIEW":
            if overview_status != 200:
                return httpx.Response(overview_status, json={})
            payload = AV_OVERVIEW if overview_payload is None else overview_payload
            return httpx.Response(200, json=payload)
        return httpx.Response(404, json={})

    return handler


def _make_av(handler: Handler) -> AlphaVantageProvider:
    return AlphaVantageProvider(TEST_KEY, client=_client(handler))


def test_alphavantage_requires_api_key() -> None:
    with pytest.raises(ProviderConfigError):
        AlphaVantageProvider(" ")


def test_alphavantage_quote_combines_global_quote_and_overview() -> None:
    quote = _make_av(_av_handler()).get_quote("fixt")
    assert quote is not None
    assert quote.share_price == pytest.approx(25.0, rel=REL_TOL)
    assert quote.market_cap == pytest.approx(1.25e9, rel=REL_TOL)
    assert quote.shares_outstanding == pytest.approx(50e6, rel=REL_TOL)
    assert quote.as_of == "2025-06-11"
    assert quote.source == "Alpha Vantage"
    assert quote.currency == "USD"


def test_alphavantage_rate_limit_note_returns_none_without_overview_call() -> None:
    calls: list[str] = []
    provider = _make_av(_av_handler(calls, quote_payload=AV_RATE_LIMIT_NOTE))
    assert provider.get_quote("FIXT") is None
    assert calls == ["GLOBAL_QUOTE"]  # OVERVIEW only after a successful quote


def test_alphavantage_information_body_returns_none() -> None:
    payload = {"Information": "API key detected, but the request was throttled."}
    provider = _make_av(_av_handler(quote_payload=payload))
    assert provider.get_quote("FIXT") is None


def test_alphavantage_empty_global_quote_returns_none() -> None:
    calls: list[str] = []
    provider = _make_av(_av_handler(calls, quote_payload={"Global Quote": {}}))
    assert provider.get_quote("FIXT") is None
    assert calls == ["GLOBAL_QUOTE"]


def test_alphavantage_overview_failure_degrades_to_quote_only() -> None:
    quote = _make_av(_av_handler(overview_status=500)).get_quote("FIXT")
    assert quote is not None
    assert quote.share_price == pytest.approx(25.0, rel=REL_TOL)
    assert quote.market_cap is None
    assert quote.shares_outstanding is None


def test_alphavantage_overview_rate_limit_degrades_to_quote_only() -> None:
    quote = _make_av(
        _av_handler(overview_payload=AV_RATE_LIMIT_NOTE)
    ).get_quote("FIXT")
    assert quote is not None
    assert quote.share_price == pytest.approx(25.0, rel=REL_TOL)
    assert quote.market_cap is None


def test_alphavantage_http_error_maps_to_provider_error_without_key() -> None:
    provider = _make_av(_av_handler(quote_status=401))
    with pytest.raises(ProviderError) as excinfo:
        provider.get_quote("FIXT")
    message = str(excinfo.value)
    assert "Alpha Vantage" in message
    assert "401" in message
    assert TEST_KEY not in message  # never leak the API key


# ---------------------------------------------------------------------------
# TiingoProvider
# ---------------------------------------------------------------------------

TIINGO_META = {
    "ticker": "FIXT",
    "name": "Fixture Manufacturing Corp",
    "exchangeCode": "NYSE",
}
TIINGO_PRICES = [{"date": "2025-06-11T00:00:00.000Z", "close": 25.0, "adjClose": 25.0}]


def _tiingo_handler(
    *,
    status: int = 200,
    meta_status: int = 200,
    empty_prices: bool = False,
) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == f"Token {TEST_KEY}"
        if status != 200:
            return httpx.Response(status, json={"detail": "denied"})
        if request.url.path == "/tiingo/daily/fixt":
            if meta_status != 200:
                return httpx.Response(meta_status, json={"detail": "Not found."})
            return httpx.Response(200, json=TIINGO_META)
        if request.url.path == "/tiingo/daily/fixt/prices":
            return httpx.Response(200, json=[] if empty_prices else TIINGO_PRICES)
        return httpx.Response(404, json={"detail": "Not found."})

    return handler


def _make_tiingo(handler: Handler) -> TiingoProvider:
    return TiingoProvider(TEST_KEY, client=_client(handler))


def test_tiingo_requires_api_key() -> None:
    with pytest.raises(ProviderConfigError):
        TiingoProvider(" ")


def test_tiingo_quote_is_price_only_with_token_header() -> None:
    quote = _make_tiingo(_tiingo_handler()).get_quote("FIXT")
    assert quote is not None
    assert quote.share_price == pytest.approx(25.0, rel=REL_TOL)
    assert quote.market_cap is None  # the daily endpoints carry no cap/shares
    assert quote.shares_outstanding is None
    assert quote.as_of == "2025-06-11"
    assert quote.source == "Tiingo"
    assert quote.currency == "USD"


def test_tiingo_unknown_ticker_404_returns_none() -> None:
    provider = _make_tiingo(_tiingo_handler(meta_status=404))
    assert provider.get_quote("FIXT") is None


def test_tiingo_empty_price_history_returns_none() -> None:
    provider = _make_tiingo(_tiingo_handler(empty_prices=True))
    assert provider.get_quote("FIXT") is None


def test_tiingo_http_error_maps_to_provider_error_without_key() -> None:
    provider = _make_tiingo(_tiingo_handler(status=401))
    with pytest.raises(ProviderError) as excinfo:
        provider.get_quote("FIXT")
    message = str(excinfo.value)
    assert "Tiingo" in message
    assert "401" in message
    assert TEST_KEY not in message  # never leak the API key


# ---------------------------------------------------------------------------
# YahooQuoteProvider (keyless tail; fake yfinance module, no network)
# ---------------------------------------------------------------------------


class _FakeYfTicker:
    registry: dict[str, Any] = {}

    def __init__(self, symbol: str) -> None:
        data = self.registry.get(symbol.upper())
        if isinstance(data, Exception):
            raise data
        self._data = data or {}

    @property
    def fast_info(self) -> Any:
        value = self._data.get("fast_info")
        if isinstance(value, Exception):
            raise value
        return value

    @property
    def info(self) -> Any:
        value = self._data.get("info")
        if isinstance(value, Exception):
            raise value
        return value


def _make_yahoo_quote(registry: dict[str, Any]) -> YahooQuoteProvider:
    ticker_cls = type("_BoundTicker", (_FakeYfTicker,), {"registry": dict(registry)})
    return YahooQuoteProvider(yf_module=types.SimpleNamespace(Ticker=ticker_cls))


def _fast(price: float, currency: str = "USD") -> types.SimpleNamespace:
    return types.SimpleNamespace(
        last_price=price, market_cap=1.25e9, shares=50e6, currency=currency
    )


def test_yahoo_quote_happy_path_via_fast_info() -> None:
    provider = _make_yahoo_quote({"FIXT": {"fast_info": _fast(25.0)}})
    quote = provider.get_quote("fixt")
    assert quote is not None
    assert quote.share_price == pytest.approx(25.0, rel=REL_TOL)
    assert quote.market_cap == pytest.approx(1.25e9, rel=REL_TOL)
    assert quote.shares_outstanding == pytest.approx(50e6, rel=REL_TOL)
    assert quote.currency == "USD"
    assert quote.source == YAHOO_DATA_SOURCE
    assert provider.name == "yahoo_quote"


def test_yahoo_quote_normalizes_gbp_pence() -> None:
    provider = _make_yahoo_quote(
        {"TSCO.L": {"fast_info": _fast(250.0, currency="GBp")}}
    )
    quote = provider.get_quote("TSCO.L")
    assert quote is not None
    assert quote.share_price == pytest.approx(2.50, rel=REL_TOL)
    assert quote.currency == "GBP"


def test_yahoo_quote_falls_back_to_info_when_fast_info_empty() -> None:
    info = {"currentPrice": 25.0, "marketCap": 1.25e9,
            "sharesOutstanding": 50e6, "currency": "USD"}
    provider = _make_yahoo_quote({"FIXT": {"fast_info": None, "info": info}})
    quote = provider.get_quote("FIXT")
    assert quote is not None
    assert quote.share_price == pytest.approx(25.0, rel=REL_TOL)
    assert quote.source == YAHOO_DATA_SOURCE


def test_yahoo_quote_failure_returns_none() -> None:
    # Non-transport yfinance failures (unknown symbol quirks) -> None.
    provider = _make_yahoo_quote({"FIXT": ValueError("boom")})
    assert provider.get_quote("FIXT") is None
    # No quote data at all -> None.
    assert _make_yahoo_quote({}).get_quote("FIXT") is None


def test_yahoo_quote_missing_yfinance_returns_none() -> None:
    # The tail is always in the chain; a missing optional dependency must
    # degrade to "no quote", not an error. _import_yfinance raises
    # ProviderConfigError, which get_quote swallows.
    provider = YahooQuoteProvider()

    def _raise() -> Any:
        raise ProviderConfigError("yfinance is not installed")

    provider._yahoo._yf = _raise  # type: ignore[method-assign]
    assert provider.get_quote("FIXT") is None


# ---------------------------------------------------------------------------
# CompositeLiveProvider market-data chain (FMP -> Polygon -> AV -> Tiingo)
# ---------------------------------------------------------------------------

FMP_QUOTE_PAYLOAD = [
    {
        "symbol": "FIXT",
        "price": 25.0,
        "marketCap": 1250000000,
        "sharesOutstanding": 50000000,
        "timestamp": 1749600000,  # 2025-06-11 UTC
    }
]


class _StubEdgar:
    """Fundamentals stand-in: the chain tests only exercise market data."""

    def get_company(self, ticker: str, max_years: int = 5) -> CompanyDataBundle:
        return CompanyDataBundle(
            info=CompanyInfo(ticker=ticker.upper(), name="Fixture Manufacturing Corp"),
            data_source="SEC EDGAR",
            fetched_at="2025-06-11T00:00:00+00:00",
        )

    def search(self, query: str) -> list:
        return []


def _fmp_handler(*, status: int = 200) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        if status != 200:
            return httpx.Response(status, json={"Error Message": "denied"})
        if request.url.path == "/stable/quote":
            return httpx.Response(200, json=FMP_QUOTE_PAYLOAD)
        return httpx.Response(200, json=[])  # profile/search: empty

    return handler


def _make_fmp(*, status: int = 200) -> FmpProvider:
    return FmpProvider(TEST_KEY, client=_client(_fmp_handler(status=status)))


def test_chain_fmp_wins_when_it_has_a_quote_and_later_adapters_stay_idle() -> None:
    polygon_calls: list[str] = []
    composite = CompositeLiveProvider(
        _StubEdgar(),
        _make_fmp(),
        [_make_polygon(_polygon_handler(polygon_calls))],
    )
    bundle = composite.get_company("FIXT")
    assert bundle.market is not None
    assert bundle.market.source == "Financial Modeling Prep"
    assert bundle.data_source == "SEC EDGAR + Financial Modeling Prep"
    assert polygon_calls == []  # first non-None quote short-circuits the chain


def test_chain_polygon_wins_when_fmp_fails_and_failure_becomes_warning() -> None:
    composite = CompositeLiveProvider(
        _StubEdgar(),
        _make_fmp(status=500),
        [_make_polygon(_polygon_handler())],
    )
    bundle = composite.get_company("FIXT")
    assert bundle.market is not None
    assert bundle.market.source == "Polygon.io"
    assert bundle.market.share_price == pytest.approx(25.0, rel=REL_TOL)
    assert bundle.data_source == "SEC EDGAR + Polygon.io"
    assert any(
        w.startswith("Market data unavailable") and "FMP" in w
        for w in bundle.warnings
    )
    assert all(TEST_KEY not in w for w in bundle.warnings)


def test_chain_av_rate_limit_falls_through_to_tiingo() -> None:
    composite = CompositeLiveProvider(
        _StubEdgar(),
        None,
        [
            _make_av(_av_handler(quote_payload=AV_RATE_LIMIT_NOTE)),
            _make_tiingo(_tiingo_handler()),
        ],
    )
    bundle = composite.get_company("FIXT")
    assert bundle.market is not None
    assert bundle.market.source == "Tiingo"
    assert bundle.data_source == "SEC EDGAR + Tiingo"


def test_chain_all_adapters_failing_leaves_market_none_with_warnings() -> None:
    composite = CompositeLiveProvider(
        _StubEdgar(),
        _make_fmp(status=500),
        [
            _make_polygon(_polygon_handler(prev_status=500)),
            _make_av(_av_handler(quote_status=500)),
            _make_tiingo(_tiingo_handler(status=500)),
        ],
    )
    bundle = composite.get_company("FIXT")
    assert bundle.market is None
    assert bundle.data_source == "SEC EDGAR"
    market_warnings = [
        w for w in bundle.warnings if w.startswith("Market data unavailable")
    ]
    assert len(market_warnings) == 4  # one per failing adapter
    for provider_name in ("FMP", "Polygon", "Alpha Vantage", "Tiingo"):
        assert any(provider_name in w for w in market_warnings)
    assert all(TEST_KEY not in w for w in bundle.warnings)


def test_chain_tiingo_only_configuration_works() -> None:
    composite = CompositeLiveProvider(
        _StubEdgar(), None, [_make_tiingo(_tiingo_handler())]
    )
    bundle = composite.get_company("FIXT")
    assert bundle.market is not None
    assert bundle.market.source == "Tiingo"
    assert bundle.market.share_price == pytest.approx(25.0, rel=REL_TOL)
    assert bundle.data_source == "SEC EDGAR + Tiingo"


def test_chain_yahoo_quote_tail_wins_when_fmp_plan_gates_the_quote() -> None:
    """The ADR scenario: FMP free plan answers HTTP 402 (ProviderError), the
    keyless yfinance tail still delivers the quote."""
    composite = CompositeLiveProvider(
        _StubEdgar(),
        _make_fmp(status=402),
        [_make_yahoo_quote({"BUD": {"fast_info": _fast(61.5)}})],
    )
    bundle = composite.get_company("BUD")
    assert bundle.market is not None
    assert bundle.market.source == YAHOO_DATA_SOURCE
    assert bundle.market.share_price == pytest.approx(61.5, rel=REL_TOL)
    assert bundle.market.currency == "USD"
    assert bundle.data_source == f"SEC EDGAR + {YAHOO_DATA_SOURCE}"
    assert any(
        w.startswith("Market data unavailable") and "402" in w
        for w in bundle.warnings
    )


def test_chain_yahoo_quote_tail_failure_keeps_market_none() -> None:
    composite = CompositeLiveProvider(
        _StubEdgar(),
        _make_fmp(status=402),
        [_make_yahoo_quote({})],  # tail has no quote either
    )
    bundle = composite.get_company("BUD")
    assert bundle.market is None
    assert bundle.data_source == "SEC EDGAR"


def test_refresh_market_walks_the_same_chain() -> None:
    composite = CompositeLiveProvider(
        _StubEdgar(),
        _make_fmp(status=500),
        [_make_polygon(_polygon_handler())],
    )
    quote = composite.refresh_market("FIXT")
    assert quote is not None
    assert quote.source == "Polygon.io"


def test_refresh_market_returns_none_when_every_adapter_fails() -> None:
    composite = CompositeLiveProvider(
        _StubEdgar(),
        _make_fmp(status=500),
        [_make_tiingo(_tiingo_handler(status=500))],
    )
    assert composite.refresh_market("FIXT") is None


# ---------------------------------------------------------------------------
# Factory wiring (settings keys -> chain membership and order)
# ---------------------------------------------------------------------------


def _settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "data_provider": "live",
        "sec_edgar_user_agent": "Test Agent test@example.com",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_factory_wires_configured_adapters_in_chain_order() -> None:
    provider = get_provider(
        _settings(
            fmp_api_key="fk",
            polygon_api_key="pk",
            alphavantage_api_key="ak",
            tiingo_api_key="tk",
        )
    )
    assert isinstance(provider, CompositeLiveProvider)
    # The keyless yfinance tail is always present, always last.
    assert [type(a) for a in provider.market_adapters] == [
        FmpProvider,
        PolygonProvider,
        AlphaVantageProvider,
        TiingoProvider,
        YahooQuoteProvider,
    ]


def test_factory_skips_unconfigured_adapters_but_keeps_keyless_tail() -> None:
    provider = get_provider(_settings(tiingo_api_key="tk"))
    assert isinstance(provider, CompositeLiveProvider)
    assert provider.fmp is None
    assert [type(a) for a in provider.market_adapters] == [
        TiingoProvider,
        YahooQuoteProvider,
    ]


def test_factory_keyless_tail_present_with_no_keys_at_all() -> None:
    provider = get_provider(_settings())
    assert isinstance(provider, CompositeLiveProvider)
    assert [type(a) for a in provider.market_adapters] == [YahooQuoteProvider]
