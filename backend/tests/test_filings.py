"""Filings intelligence tests (spec §19.3). No live network: all SEC HTTP goes
through httpx.MockTransport and the ticker-map disk cache is pointed at tmp_path.
"""

from typing import Iterator

import httpx
import pytest
from fastapi.testclient import TestClient

import app.providers.edgar_filings as edgar_filings_module
from app.api.deps import get_provider_dep
from app.core.config import Settings
from app.main import app
from app.providers.base import DataProvider
from app.providers.edgar_filings import EdgarFilingsProvider
from app.providers.exceptions import CompanyNotFoundError, ProviderError
from app.providers.mock import MockProvider
from app.schemas.company import CompanyDataBundle, SearchResult
from app.services import filings_service

USER_AGENT = "Test Suite test@example.com"

TICKER_MAP = {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}

# 14 recent filings, newest first: 12 are in the §19.3 form set (10-K, 10-Q,
# 8-K, DEF 14A) so the latest-10 cap binds; Form 4 / S-8 must be filtered out.
_FORMS = [
    "10-K", "4", "10-Q", "8-K", "S-8", "DEF 14A", "10-Q",
    "8-K", "10-Q", "8-K", "10-K", "10-Q", "8-K", "DEF 14A",
]
# Descending filing dates ("2025-12-28" .. "2025-12-15"); the newest filing has
# an empty reportDate to check the "" -> None mapping.
SUBMISSIONS = {
    "cik": "320193",
    "filings": {
        "recent": {
            "form": _FORMS,
            "filingDate": [f"2025-12-{(28 - i):02d}" for i in range(len(_FORMS))],
            "reportDate": [""] + [f"2025-11-{(27 - i):02d}" for i in range(1, len(_FORMS))],
            "accessionNumber": [f"0000320193-25-{i:06d}" for i in range(len(_FORMS))],
            "primaryDocument": [f"doc{i}.htm" for i in range(len(_FORMS))],
        }
    },
}


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.host == "www.sec.gov" and request.url.path == "/files/company_tickers.json":
        return httpx.Response(200, json=TICKER_MAP)
    if request.url.host == "data.sec.gov" and request.url.path == "/submissions/CIK0000320193.json":
        assert request.headers.get("User-Agent") == USER_AGENT
        return httpx.Response(200, json=SUBMISSIONS)
    return httpx.Response(404)


def _provider(tmp_path, handler=_handler) -> EdgarFilingsProvider:
    return EdgarFilingsProvider(
        USER_AGENT,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        cache_dir=str(tmp_path),
    )


def _settings(**overrides) -> Settings:
    defaults = dict(sec_edgar_user_agent=USER_AGENT, _env_file=None)
    defaults.update(overrides)
    return Settings(**defaults)


class StubLiveProvider(DataProvider):
    """Non-mock provider stand-in; filings never touch it."""

    name = "stub"

    def search(self, query: str) -> list[SearchResult]:  # pragma: no cover
        raise NotImplementedError

    def get_company(self, ticker: str) -> CompanyDataBundle:  # pragma: no cover
        raise NotImplementedError


# ---------------------------------------------------------------------------
# EdgarFilingsProvider
# ---------------------------------------------------------------------------


def test_form_filter_latest_ten_and_field_mapping(tmp_path) -> None:
    cik, filings = _provider(tmp_path).get_filings("aapl")
    assert cik == "0000320193"
    assert len(filings) == 10  # 12 eligible in the feed, capped at 10
    assert all(f.form in {"10-K", "10-Q", "8-K", "DEF 14A"} for f in filings)
    assert {f.form for f in filings} == {"10-K", "10-Q", "8-K", "DEF 14A"}
    first = filings[0]  # newest-first order preserved from the feed
    assert first.form == "10-K"
    assert first.filed == "2025-12-28"
    assert first.report_date is None  # empty string in the feed -> None
    assert first.accession == "0000320193-25-000000"
    assert first.primary_document == "doc0.htm"


def test_exact_document_url_construction(tmp_path) -> None:
    _cik, filings = _provider(tmp_path).get_filings("AAPL")
    first = filings[0]
    # int(cik) (no zero padding) + accession without dashes + primaryDocument.
    assert first.url == (
        "https://www.sec.gov/Archives/edgar/data/320193/"
        "000032019325000000/doc0.htm"
    )


def test_unknown_ticker_raises_company_not_found(tmp_path) -> None:
    with pytest.raises(CompanyNotFoundError):
        _provider(tmp_path).get_filings("TESTCO")


def test_429_retry_then_success(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(edgar_filings_module.time, "sleep", lambda _s: None)
    submission_calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/files/company_tickers.json":
            return httpx.Response(200, json=TICKER_MAP)
        submission_calls["n"] += 1
        if submission_calls["n"] == 1:
            return httpx.Response(429)
        return httpx.Response(200, json=SUBMISSIONS)

    _cik, filings = _provider(tmp_path, handler).get_filings("AAPL")
    assert submission_calls["n"] == 2
    assert len(filings) == 10


def test_persistent_429_maps_to_provider_error(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(edgar_filings_module.time, "sleep", lambda _s: None)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/files/company_tickers.json":
            return httpx.Response(200, json=TICKER_MAP)
        return httpx.Response(429)

    with pytest.raises(ProviderError) as excinfo:
        _provider(tmp_path, handler).get_filings("AAPL")
    assert "rate limiting" in str(excinfo.value)


# ---------------------------------------------------------------------------
# filings_service
# ---------------------------------------------------------------------------


def test_service_returns_filings_for_us_filer(tmp_path) -> None:
    response = filings_service.get_filings(
        "AAPL",
        StubLiveProvider(),
        app_settings=_settings(),
        filings_provider=_provider(tmp_path),
    )
    assert response.ticker == "AAPL"
    assert response.cik == "0000320193"
    assert response.source == "SEC EDGAR"
    assert len(response.filings) == 10
    assert response.warnings == []


def test_service_unresolvable_ticker_returns_empty_with_warning(tmp_path) -> None:
    response = filings_service.get_filings(
        "TESTCO",
        StubLiveProvider(),
        app_settings=_settings(),
        filings_provider=_provider(tmp_path),
    )
    assert response.cik is None
    assert response.filings == []
    assert response.warnings == [filings_service.LIVE_ONLY_WARNING]


def test_service_without_user_agent_short_circuits() -> None:
    response = filings_service.get_filings(
        "AAPL", StubLiveProvider(), app_settings=_settings(sec_edgar_user_agent="")
    )
    assert response.filings == []
    assert response.warnings == [filings_service.LIVE_ONLY_WARNING]


def test_memo_helper_swallows_provider_failures(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def exploding(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/files/company_tickers.json":
            return httpx.Response(200, json=TICKER_MAP)
        return httpx.Response(500)

    monkeypatch.setattr(
        filings_service,
        "_build_filings_provider",
        lambda app_settings: _provider(tmp_path, exploding),
    )
    # EDGAR HTTP 500 -> ProviderError inside -> swallowed -> None (best-effort).
    assert (
        filings_service.get_filings_for_memo(
            "AAPL", StubLiveProvider(), app_settings=_settings()
        )
        is None
    )


def test_memo_helper_returns_empty_in_mock_mode() -> None:
    assert (
        filings_service.get_filings_for_memo(
            "TESTCO", MockProvider(), app_settings=_settings()
        )
        == []
    )


# ---------------------------------------------------------------------------
# Route (mock mode): 200 + empty + warning, no network
# ---------------------------------------------------------------------------


@pytest.fixture()
def api(client: TestClient) -> Iterator[TestClient]:
    app.dependency_overrides[get_provider_dep] = MockProvider
    yield client
    app.dependency_overrides.pop(get_provider_dep, None)


def test_filings_route_mock_mode(api: TestClient) -> None:
    resp = api.get("/api/companies/TESTCO/filings")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ticker"] == "TESTCO"
    assert body["cik"] is None
    assert body["filings"] == []
    assert body["source"] == "SEC EDGAR"
    assert body["warnings"] == ["Filings are available in live mode for US filers only."]
