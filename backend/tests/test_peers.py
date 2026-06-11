"""Peer comparables tests (spec §19.2).

- Mock-mode E2E through the API: MockProvider.get_peers serves the other
  sample companies; rows and interpolated quartile stats are checked against
  hand-computed values from data/sample/*.json.
- Degraded path: a provider without get_peers and no FMP key -> warning + [].
- FMP source resolution + FmpProvider.get_peers via httpx.MockTransport
  (no live network anywhere).
"""

from typing import Iterator

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_provider_dep
from app.main import app
from app.providers.base import DataProvider
from app.providers.fmp import FmpProvider
from app.providers.mock import MockProvider
from app.schemas.company import CompanyDataBundle, SearchResult
from app.services import peers_service

REL_TOL = 1e-4

_mock_provider = MockProvider()


class NoPeersProvider(DataProvider):
    """Delegates to MockProvider but exposes no get_peers (degraded path)."""

    name = "stub"

    def search(self, query: str) -> list[SearchResult]:
        return _mock_provider.search(query)

    def get_company(self, ticker: str) -> CompanyDataBundle:
        return _mock_provider.get_company(ticker)


@pytest.fixture()
def api(client: TestClient) -> Iterator[TestClient]:
    app.dependency_overrides[get_provider_dep] = lambda: _mock_provider
    yield client
    app.dependency_overrides.pop(get_provider_dep, None)


@pytest.fixture()
def api_no_peers(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    """API whose provider lacks get_peers; FMP key forced empty for determinism."""
    monkeypatch.setattr(peers_service.global_settings, "fmp_api_key", "")
    app.dependency_overrides[get_provider_dep] = NoPeersProvider
    yield client
    app.dependency_overrides.pop(get_provider_dep, None)


# ---------------------------------------------------------------------------
# Mock-mode E2E
# ---------------------------------------------------------------------------


def test_testco_gets_five_sample_peers_with_stats(api: TestClient) -> None:
    resp = api.get("/api/companies/TESTCO/peers")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ticker"] == "TESTCO"
    assert body["peer_source"] == "Sample data (illustrative figures)"
    assert body["as_of"]
    assert [p["ticker"] for p in body["peers"]] == ["AAPL", "DE", "HD", "KO", "MSFT"]
    assert len(body["peers"]) == 5

    # Target row from the §15 TESTCO binding values.
    target = body["target"]
    assert target["ticker"] == "TESTCO"
    assert target["name"] == "Testco Industrials Inc"
    assert target["market_cap"] == pytest.approx(1.35e9, rel=REL_TOL)
    assert target["enterprise_value"] == pytest.approx(1.65e9, rel=REL_TOL)
    assert target["ev_ebitda"] == pytest.approx(6.6, rel=REL_TOL)
    assert target["ev_revenue"] == pytest.approx(1.65, rel=REL_TOL)
    assert target["pe"] == pytest.approx(10.0, rel=REL_TOL)
    assert target["ebitda_margin"] == pytest.approx(0.25, rel=REL_TOL)
    assert target["revenue_growth_yoy"] == pytest.approx(1000 / 950 - 1, rel=REL_TOL)
    assert target["currency"] == "USD"

    # A peer row hand-computed from data/sample/HD.json: EV = 356.4bn market
    # cap + 53.0bn debt - 8.0bn cash; metrics from FY-latest fundamentals.
    hd = next(p for p in body["peers"] if p["ticker"] == "HD")
    assert hd["name"] == "The Home Depot, Inc."
    assert hd["market_cap"] == pytest.approx(356.4e9, rel=REL_TOL)
    assert hd["ev_ebitda"] == pytest.approx(16.124514, rel=REL_TOL)
    assert hd["ebitda_margin"] == pytest.approx(0.157669, rel=REL_TOL)

    # Quartile stats exist for all four §19.2 metrics, computed over peers
    # only. With five peers the interpolated quartiles land on data points:
    # sorted EBITDA margins are HD, DE, KO, AAPL, MSFT.
    assert set(body["stats"]) == {"ev_ebitda", "ev_revenue", "pe", "ebitda_margin"}
    margin_stats = body["stats"]["ebitda_margin"]
    assert margin_stats["min"] == pytest.approx(0.157669, rel=REL_TOL)  # HD
    assert margin_stats["q1"] == pytest.approx(0.208333, rel=REL_TOL)  # DE
    assert margin_stats["median"] == pytest.approx(0.270103, rel=REL_TOL)  # KO
    assert margin_stats["q3"] == pytest.approx(0.347059, rel=REL_TOL)  # AAPL
    assert margin_stats["max"] == pytest.approx(0.548148, rel=REL_TOL)  # MSFT
    assert body["warnings"] == []


def test_hidden_testco_never_appears_as_a_peer(api: TestClient) -> None:
    resp = api.get("/api/companies/AAPL/peers")
    assert resp.status_code == 200
    body = resp.json()
    tickers = [p["ticker"] for p in body["peers"]]
    assert "TESTCO" not in tickers
    assert "AAPL" not in tickers  # never its own peer
    assert tickers == ["DE", "HD", "KO", "MSFT"]


def test_quartiles_are_linearly_interpolated(api: TestClient) -> None:
    """Four peers force interpolation between data points (AAPL's peer set).

    Sorted peer EV/EBITDA: HD 16.124514, DE 17.84, MSFT 23.168919,
    KO 25.419847 -> q1 at position 0.75, median at 1.5, q3 at 2.25.
    """
    body = api.get("/api/companies/AAPL/peers").json()
    stats = body["stats"]["ev_ebitda"]
    assert stats["min"] == pytest.approx(16.124514, rel=REL_TOL)
    assert stats["q1"] == pytest.approx(17.411129, rel=REL_TOL)
    assert stats["median"] == pytest.approx(20.504459, rel=REL_TOL)
    assert stats["q3"] == pytest.approx(23.731651, rel=REL_TOL)
    assert stats["max"] == pytest.approx(25.419847, rel=REL_TOL)


def test_unknown_target_ticker_is_404(api: TestClient) -> None:
    resp = api.get("/api/companies/NOPE/peers")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Degraded path: no peer source at all
# ---------------------------------------------------------------------------


def test_no_peer_source_returns_warning_and_empty(api_no_peers: TestClient) -> None:
    resp = api_no_peers.get("/api/companies/TESTCO/peers")
    assert resp.status_code == 200
    body = resp.json()
    assert body["peers"] == []
    assert body["stats"] == {}
    assert body["peer_source"] is None
    assert peers_service.NO_SOURCE_WARNING in body["warnings"]
    # The target row is still built from its own bundle.
    assert body["target"]["ev_ebitda"] == pytest.approx(6.6, rel=REL_TOL)


# ---------------------------------------------------------------------------
# FmpProvider.get_peers (MockTransport) + FMP fallback resolution
# ---------------------------------------------------------------------------

FMP_PEERS_PAYLOAD = [
    {"symbol": "FIXT", "companyName": "Fixture Manufacturing Corp", "price": 25.0,
     "mktCap": 1_250_000_000},  # the target itself: must be excluded
    {"symbol": "DE", "companyName": "Deere & Company", "price": 450.0,
     "mktCap": 122_400_000_000},
    {"symbol": "HD", "companyName": "The Home Depot, Inc.", "price": 360.0,
     "mktCap": 356_400_000_000},
    {"symbol": None, "companyName": "Broken Record"},  # dropped: no symbol
]


def _fmp_peers_provider() -> FmpProvider:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params.get("apikey") == "test-key"
        assert request.url.path == "/stable/stock-peers"
        assert request.url.params.get("symbol") == "FIXT"
        return httpx.Response(200, json=FMP_PEERS_PAYLOAD)

    return FmpProvider(
        "test-key", client=httpx.Client(transport=httpx.MockTransport(handler))
    )


def test_fmp_get_peers_maps_payload_and_excludes_self() -> None:
    peers = _fmp_peers_provider().get_peers("fixt")
    assert [p["symbol"] for p in peers] == ["DE", "HD"]
    de = peers[0]
    assert de == {
        "symbol": "DE",
        "name": "Deere & Company",
        "price": 450.0,
        "mktCap": 122_400_000_000.0,
    }


def test_fmp_get_peers_empty_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    provider = FmpProvider(
        "test-key", client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    assert provider.get_peers("FIXT") == []


def test_provider_without_get_peers_falls_back_to_fmp(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§19.2 resolution: no provider.get_peers + fmp_api_key set -> FMP source."""

    def fmp_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/stable/stock-peers"
        return httpx.Response(
            200,
            json=[
                {"symbol": "DE", "companyName": "Deere & Company", "price": 450.0,
                 "mktCap": 122_400_000_000},
                {"symbol": "ZZZZ", "companyName": "Not In Samples", "price": 1.0,
                 "mktCap": 1_000_000},  # bundle fetch fails -> skip + warning
            ],
        )

    fmp = FmpProvider(
        "test-key", client=httpx.Client(transport=httpx.MockTransport(fmp_handler))
    )
    monkeypatch.setattr(peers_service.global_settings, "fmp_api_key", "test-key")
    monkeypatch.setattr(peers_service, "_build_fmp", lambda app_settings: fmp)
    app.dependency_overrides[get_provider_dep] = NoPeersProvider
    try:
        resp = client.get("/api/companies/AAPL/peers")
    finally:
        app.dependency_overrides.pop(get_provider_dep, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body["peer_source"] == "Financial Modeling Prep"
    assert [p["ticker"] for p in body["peers"]] == ["DE"]
    # Market cap comes from the peers payload itself (no extra quote calls).
    assert body["peers"][0]["market_cap"] == pytest.approx(122.4e9, rel=REL_TOL)
    # Fundamentals come from the (mock-backed) bundle.
    assert body["peers"][0]["ebitda_margin"] == pytest.approx(0.208333, rel=REL_TOL)
    assert any("ZZZZ" in w and "skipped" in w for w in body["warnings"])
