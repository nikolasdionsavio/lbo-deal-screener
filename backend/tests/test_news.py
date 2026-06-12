"""News chain tests (spec §19.6): FMP -> yfinance -> empty + warning.

No live network: FMP goes through httpx.MockTransport and yfinance is a fake
module injected into sys.modules.
"""

import sys
import types
from typing import Iterator

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_provider_dep
from app.core.config import Settings
from app.main import app
from app.providers.base import DataProvider
from app.providers.fmp import FmpProvider
from app.providers.mock import MockProvider
from app.schemas.company import CompanyDataBundle, SearchResult
from app.services import news_service


class StubLiveProvider(DataProvider):
    """Non-mock provider stand-in; the news chain never calls it."""

    name = "stub"

    def search(self, query: str) -> list[SearchResult]:  # pragma: no cover
        raise NotImplementedError

    def get_company(self, ticker: str) -> CompanyDataBundle:  # pragma: no cover
        raise NotImplementedError


def _settings(fmp_api_key: str = "") -> Settings:
    return Settings(fmp_api_key=fmp_api_key, _env_file=None)


def _fmp_with(handler) -> FmpProvider:
    return FmpProvider(
        "test-key", client=httpx.Client(transport=httpx.MockTransport(handler))
    )


def _install_fake_yfinance(
    monkeypatch: pytest.MonkeyPatch,
    news: list | Exception,
    seen_counts: list[int] | None = None,
) -> None:
    class FakeTicker:
        def __init__(self, ticker: str) -> None:
            self.ticker = ticker

        def get_news(self, count: int = 10) -> list:
            if seen_counts is not None:
                seen_counts.append(count)
            if isinstance(news, Exception):
                raise news
            return news

    monkeypatch.setitem(
        sys.modules, "yfinance", types.SimpleNamespace(Ticker=FakeTicker)
    )


def _yf_item(i: int, pub_date: str, *, click_through: bool = False) -> dict:
    url_key = "clickThroughUrl" if click_through else "canonicalUrl"
    return {
        "content": {
            "title": f"Headline {i}",
            url_key: {"url": f"https://news.example.com/{i}"},
            "provider": {"displayName": "Example Wire"},
            "pubDate": pub_date,
            "summary": f"Summary {i}",
        }
    }


FMP_NEWS = [
    {
        "symbol": "AAPL",
        "publishedDate": "2026-06-09 08:00:00",
        "publisher": "Old Wire",
        "title": "Older headline",
        "url": "https://fmp.example.com/older",
        "text": "Older summary.",
    },
    {
        "symbol": "AAPL",
        "publishedDate": "2026-06-10 14:30:00",
        "publisher": "New Wire",
        "title": "Newer headline",
        "url": "https://fmp.example.com/newer",
        "text": "Newer summary.",
    },
    {"symbol": "AAPL", "title": "No URL, must be dropped"},
]


# ---------------------------------------------------------------------------
# FmpProvider.get_news (MockTransport)
# ---------------------------------------------------------------------------


def test_fmp_get_news_returns_records() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/stable/news/stock"
        assert request.url.params.get("symbols") == "AAPL"
        return httpx.Response(200, json=FMP_NEWS)

    records = _fmp_with(handler).get_news("aapl")
    assert records is not None
    assert len(records) == 3


def test_fmp_get_news_restricted_body_returns_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "Error Message": "Restricted Endpoint: this endpoint is not "
                "available on your plan."
            },
        )

    assert _fmp_with(handler).get_news("AAPL") is None


@pytest.mark.parametrize("status", [402, 403])
def test_fmp_get_news_payment_statuses_return_none(status: int) -> None:
    handler = lambda request: httpx.Response(status, json={})  # noqa: E731
    assert _fmp_with(handler).get_news("AAPL") is None


# ---------------------------------------------------------------------------
# news_service chain
# ---------------------------------------------------------------------------


def test_fmp_success_serves_items_sorted_newest_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        news_service,
        "_build_fmp",
        lambda app_settings: _fmp_with(lambda r: httpx.Response(200, json=FMP_NEWS)),
    )
    response = news_service.get_news(
        "AAPL", StubLiveProvider(), app_settings=_settings("test-key")
    )
    assert response.provider == "Financial Modeling Prep"
    assert [i.title for i in response.items] == ["Newer headline", "Older headline"]
    first = response.items[0]
    assert first.url == "https://fmp.example.com/newer"
    assert first.source == "New Wire"
    assert first.published_at == "2026-06-10T14:30:00"  # ISO-normalized
    assert first.summary == "Newer summary."
    assert response.warnings == []


def test_fmp_restricted_body_falls_through_to_yfinance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    restricted = lambda r: httpx.Response(  # noqa: E731
        200, json={"Error Message": "Restricted Endpoint"}
    )
    monkeypatch.setattr(
        news_service, "_build_fmp", lambda app_settings: _fmp_with(restricted)
    )
    _install_fake_yfinance(monkeypatch, [_yf_item(1, "2026-06-10T09:00:00Z")])

    response = news_service.get_news(
        "AAPL", StubLiveProvider(), app_settings=_settings("test-key")
    )
    assert response.provider == "Yahoo Finance (unofficial endpoints, via yfinance)"
    assert [i.title for i in response.items] == ["Headline 1"]
    assert news_service.FMP_RESTRICTED_WARNING in response.warnings


def test_fmp_provider_error_falls_through_with_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        news_service,
        "_build_fmp",
        lambda app_settings: _fmp_with(lambda r: httpx.Response(500)),
    )
    _install_fake_yfinance(monkeypatch, [_yf_item(1, "2026-06-10T09:00:00Z")])

    response = news_service.get_news(
        "AAPL", StubLiveProvider(), app_settings=_settings("test-key")
    )
    assert response.provider == "Yahoo Finance (unofficial endpoints, via yfinance)"
    assert any("Financial Modeling Prep" in w for w in response.warnings)


def test_yfinance_items_parsed_sorted_and_capped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 15 items, deliberately out of order; one uses clickThroughUrl only and
    # one is malformed (no title) and must be dropped.
    raw = [_yf_item(i, f"2026-05-{i:02d}T12:00:00Z") for i in range(1, 15)]
    raw.append(_yf_item(15, "2026-05-15T12:00:00Z", click_through=True))
    raw.append({"content": {"summary": "no title or url"}})
    raw.reverse()  # oldest-first input: the service must re-sort

    seen_counts: list[int] = []
    _install_fake_yfinance(monkeypatch, raw, seen_counts)
    response = news_service.get_news(
        "AAPL", StubLiveProvider(), app_settings=_settings(""), limit=12  # no FMP key
    )
    assert seen_counts == [12]  # §19.8: limit forwarded as get_news(count=...)
    assert response.provider == "Yahoo Finance (unofficial endpoints, via yfinance)"
    assert len(response.items) == 12  # capped at the requested limit
    dates = [i.published_at for i in response.items]
    assert dates == sorted(dates, reverse=True)  # newest first
    newest = response.items[0]
    assert newest.title == "Headline 15"
    assert newest.url == "https://news.example.com/15"  # clickThroughUrl fallback
    assert newest.source == "Example Wire"
    assert newest.summary == "Summary 15"


def test_no_sources_returns_empty_with_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_yfinance(monkeypatch, RuntimeError("boom"))
    response = news_service.get_news(
        "AAPL", StubLiveProvider(), app_settings=_settings("")
    )
    assert response.items == []
    assert response.provider == "none"
    assert news_service.LIVE_ONLY_WARNING in response.warnings
    assert any("Yahoo Finance" in w for w in response.warnings)


# ---------------------------------------------------------------------------
# Route (mock mode)
# ---------------------------------------------------------------------------


@pytest.fixture()
def api(client: TestClient) -> Iterator[TestClient]:
    app.dependency_overrides[get_provider_dep] = MockProvider
    yield client
    app.dependency_overrides.pop(get_provider_dep, None)


def test_news_route_mock_mode(api: TestClient) -> None:
    resp = api.get("/api/companies/TESTCO/news")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ticker"] == "TESTCO"
    assert body["items"] == []
    assert body["provider"] == "none"
    assert body["warnings"] == ["News is available in live mode only."]


def test_news_item_shape(api: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_yfinance(monkeypatch, [_yf_item(1, "2026-06-10T09:00:00Z")])
    response = news_service.get_news(
        "AAPL", StubLiveProvider(), app_settings=_settings("")
    )
    item = response.items[0].model_dump()
    assert set(item) == {"title", "url", "source", "published_at", "summary"}


# ---------------------------------------------------------------------------
# §19.8 limit param (1..60, default 30, clamped)
# ---------------------------------------------------------------------------


def test_limit_clamped_and_forwarded_to_fmp(monkeypatch: pytest.MonkeyPatch) -> None:
    seen_limits: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_limits.append(request.url.params.get("limit"))
        return httpx.Response(200, json=FMP_NEWS)

    monkeypatch.setattr(
        news_service, "_build_fmp", lambda app_settings: _fmp_with(handler)
    )
    settings = _settings("test-key")
    news_service.get_news("AAPL", StubLiveProvider(), app_settings=settings, limit=999)
    news_service.get_news("AAPL", StubLiveProvider(), app_settings=settings, limit=-5)
    news_service.get_news("AAPL", StubLiveProvider(), app_settings=settings)
    assert seen_limits == ["60", "1", "30"]  # clamped high, clamped low, default


def test_limit_clamped_for_yfinance_count(monkeypatch: pytest.MonkeyPatch) -> None:
    seen_counts: list[int] = []
    _install_fake_yfinance(monkeypatch, [], seen_counts)
    news_service.get_news(
        "AAPL", StubLiveProvider(), app_settings=_settings(""), limit=200
    )
    assert seen_counts == [60]


def test_news_route_accepts_limit_param(api: TestClient) -> None:
    # Mock mode short-circuits before any source, but the route must accept
    # (and clamp, not reject) any integer limit.
    for limit in (1, 30, 60, 999, -3):
        resp = api.get(f"/api/companies/TESTCO/news?limit={limit}")
        assert resp.status_code == 200
        assert resp.json()["items"] == []
