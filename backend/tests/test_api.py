"""API layer tests (spec §12, §15): every endpoint via TestClient.

Provider is overridden with MockProvider (dependency override on
get_provider_dep); the DB is the conftest in-memory SQLite per client.
"""

from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.deps import get_provider_dep
from app.db.models import LboOutputRecord
from app.main import app
from app.providers.mock import MockProvider
from app.schemas.memo import MEMO_SECTION_KEYS

REL_TOL = 1e-6

_mock_provider = MockProvider()

# §15 hand-check LBO assumptions for TESTCO.
LBO_ASSUMPTIONS = {
    "entry_multiple": 8.0,
    "debt_multiple": 4.0,
    "revenue_growth": [0.05] * 5,
    "ebitda_margin": [0.25] * 5,
    "capex_pct_revenue": 0.05,
    "nwc_pct_revenue": 0.02,
    "tax_rate": 0.25,
    "interest_rate": 0.08,
    "mandatory_repayment_pct": 0.05,
    "exit_multiple": 8.0,
    "holding_period": 5,
}


@pytest.fixture()
def api(client: TestClient) -> Iterator[TestClient]:
    """conftest client (in-memory SQLite) + MockProvider dependency override."""
    app.dependency_overrides[get_provider_dep] = lambda: _mock_provider
    yield client
    app.dependency_overrides.pop(get_provider_dep, None)


def _auth_headers(
    api: TestClient,
    email: str = "user@example.com",
    password: str = "password123",
) -> dict[str, str]:
    resp = api.post(
        "/api/auth/register", json={"email": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ---------------------------------------------------------------------------
# Health + search
# ---------------------------------------------------------------------------


def test_health(api: TestClient) -> None:
    resp = api.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert isinstance(body["provider"], str)


def test_search_finds_aapl(api: TestClient) -> None:
    resp = api.get("/api/search", params={"q": "app"})
    assert resp.status_code == 200
    results = resp.json()
    assert "AAPL" in [r["ticker"] for r in results]
    aapl = next(r for r in results if r["ticker"] == "AAPL")
    assert aapl["name"] == "Apple Inc."
    assert {"ticker", "name", "exchange", "source"} <= set(aapl)


def test_search_never_returns_testco(api: TestClient) -> None:
    for q in ("test", "TESTCO", "testco industrials", "t"):
        resp = api.get("/api/search", params={"q": q})
        assert resp.status_code == 200
        assert all(r["ticker"] != "TESTCO" for r in resp.json())


# ---------------------------------------------------------------------------
# Profile / financials / KPIs (§15 headline values)
# ---------------------------------------------------------------------------


def test_profile_testco_headline_values(api: TestClient) -> None:
    resp = api.get("/api/companies/TESTCO/profile")
    assert resp.status_code == 200
    p = resp.json()
    assert p["ticker"] == "TESTCO"
    assert p["name"] == "Testco Industrials Inc"
    assert p["latest_fiscal_year"] == 2025
    assert p["share_price"] == pytest.approx(13.50, rel=REL_TOL)
    assert p["market_cap"] == pytest.approx(1350e6, rel=REL_TOL)
    assert p["net_debt"] == pytest.approx(300e6, rel=REL_TOL)
    assert p["enterprise_value"] == pytest.approx(1650e6, rel=REL_TOL)
    assert p["revenue"] == pytest.approx(1000e6, rel=REL_TOL)
    assert p["ebitda"] == pytest.approx(250e6, rel=REL_TOL)
    assert p["net_income"] == pytest.approx(135e6, rel=REL_TOL)
    assert p["free_cash_flow"] == pytest.approx(180e6, rel=REL_TOL)
    assert p["cash"] == pytest.approx(100e6, rel=REL_TOL)
    assert p["total_debt"] == pytest.approx(400e6, rel=REL_TOL)
    assert p["data_source"] == "Sample data (illustrative figures)"
    assert p["data_as_of"]


def test_profile_ticker_is_case_insensitive(api: TestClient) -> None:
    resp = api.get("/api/companies/testco/profile")
    assert resp.status_code == 200
    assert resp.json()["ticker"] == "TESTCO"


def test_profile_unknown_ticker_404(api: TestClient) -> None:
    resp = api.get("/api/companies/ZZZZ/profile")
    assert resp.status_code == 404
    assert resp.json()["detail"]


def test_financials_testco(api: TestClient) -> None:
    resp = api.get("/api/companies/TESTCO/financials")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ticker"] == "TESTCO"
    assert [y["fiscal_year"] for y in body["years"]] == [
        2021, 2022, 2023, 2024, 2025,
    ]
    assert body["years"][-1]["revenue"] == pytest.approx(1000e6, rel=REL_TOL)
    assert body["data_source"] == "Sample data (illustrative figures)"
    assert body["fetched_at"]


def test_kpis_testco_headline_values(api: TestClient) -> None:
    resp = api.get("/api/companies/TESTCO/kpis")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ticker"] == "TESTCO"
    kpis = {k["key"]: k for k in body["kpis"]}
    assert kpis["ebitda_margin"]["value"] == pytest.approx(0.25, rel=REL_TOL)
    assert kpis["fcf_conversion"]["value"] == pytest.approx(0.72, rel=REL_TOL)
    assert kpis["net_debt_to_ebitda"]["value"] == pytest.approx(1.2, rel=REL_TOL)
    assert kpis["interest_coverage"]["value"] == pytest.approx(12.5, rel=REL_TOL)
    assert kpis["current_ratio"]["value"] == pytest.approx(2.0, rel=REL_TOL)
    assert kpis["capex_pct_revenue"]["value"] == pytest.approx(0.05, rel=REL_TOL)
    assert kpis["revenue_growth_yoy"]["value"] == pytest.approx(
        1000 / 950 - 1, rel=REL_TOL
    )
    assert kpis["revenue_cagr_3y"]["value"] == pytest.approx(
        (1000 / 850) ** (1 / 3) - 1, rel=REL_TOL
    )
    # Traceability + series presence.
    assert kpis["ebitda_margin"]["formula"]
    assert kpis["ebitda_margin"]["inputs"]
    assert "revenue" in body["series"]
    assert "ebitda_margin" in body["series"]


# ---------------------------------------------------------------------------
# Valuation
# ---------------------------------------------------------------------------


def test_valuation_default_multiples(api: TestClient) -> None:
    resp = api.post("/api/companies/TESTCO/valuation", json={})
    assert resp.status_code == 200
    body = resp.json()
    # §15: TESTCO EV/EBITDA 6.6x rounds to base 6.5x; low/high = base ∓ 2.
    assert body["assumptions"] == {"low": 4.5, "base": 6.5, "high": 8.5}
    cases = {c["case"]: c for c in body["range"]}
    assert set(cases) == {"low", "base", "high"}
    for case in cases.values():
        multiple = case["multiple"]
        assert case["implied_ev"] == pytest.approx(multiple * 250e6, rel=REL_TOL)
        assert case["implied_equity"] == pytest.approx(
            multiple * 250e6 - 300e6, rel=REL_TOL
        )
        assert case["implied_share_price"] == pytest.approx(
            (multiple * 250e6 - 300e6) / 100e6, rel=REL_TOL
        )
    multiples = {m["key"]: m for m in body["multiples"]}
    assert multiples["ev_ebitda"]["value"] == pytest.approx(6.6, rel=REL_TOL)


def test_valuation_custom_multiples(api: TestClient) -> None:
    resp = api.post(
        "/api/companies/TESTCO/valuation",
        json={"low": 5.0, "base": 7.0, "high": 9.0},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["assumptions"] == {"low": 5.0, "base": 7.0, "high": 9.0}
    base = next(c for c in body["range"] if c["case"] == "base")
    assert base["implied_ev"] == pytest.approx(7.0 * 250e6, rel=REL_TOL)
    assert base["implied_equity"] == pytest.approx(
        7.0 * 250e6 - 300e6, rel=REL_TOL
    )


# ---------------------------------------------------------------------------
# LBO defaults + LBO run
# ---------------------------------------------------------------------------


def test_lbo_defaults_testco(api: TestClient) -> None:
    resp = api.get("/api/companies/TESTCO/lbo/defaults")
    assert resp.status_code == 200
    body = resp.json()
    a = body["assumptions"]
    assert a["entry_multiple"] == pytest.approx(6.5, rel=REL_TOL)
    assert a["exit_multiple"] == pytest.approx(6.5, rel=REL_TOL)
    assert a["holding_period"] == 5
    assert len(a["revenue_growth"]) == 5
    assert len(a["ebitda_margin"]) == 5
    assert a["debt_multiple"] < a["entry_multiple"]
    # Every assumption carries a basis note.
    assert set(body["basis"]) >= set(a)


def test_lbo_post_hand_check_and_shape(api: TestClient) -> None:
    resp = api.post("/api/companies/TESTCO/lbo", json=LBO_ASSUMPTIONS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ticker"] == "TESTCO"

    # §15 entry hand-check.
    entry = body["entry"]
    assert entry["entry_ebitda"] == pytest.approx(250e6, rel=REL_TOL)
    assert entry["entry_revenue"] == pytest.approx(1000e6, rel=REL_TOL)
    assert entry["entry_ev"] == pytest.approx(2000e6, rel=REL_TOL)
    assert entry["opening_debt"] == pytest.approx(1000e6, rel=REL_TOL)
    assert entry["sponsor_equity"] == pytest.approx(1000e6, rel=REL_TOL)
    assert entry["equity_pct"] == pytest.approx(0.5, rel=REL_TOL)

    # §15 year-1 hand-check.
    assert len(body["years"]) == 5
    y1 = body["years"][0]
    assert y1["revenue"] == pytest.approx(1050e6, rel=REL_TOL)
    assert y1["ebitda"] == pytest.approx(262.5e6, rel=REL_TOL)
    assert y1["capex"] == pytest.approx(52.5e6, rel=REL_TOL)
    assert y1["delta_nwc"] == pytest.approx(1.0e6, rel=REL_TOL)
    assert y1["interest"] == pytest.approx(80e6, rel=REL_TOL)
    assert y1["taxes"] == pytest.approx(32.5e6, rel=REL_TOL)
    assert y1["fcf"] == pytest.approx(96.5e6, rel=REL_TOL)
    assert y1["ending_debt"] == pytest.approx(903.5e6, rel=REL_TOL)

    # Exit block: mom and irr present.
    exit_block = body["exit"]
    for key in (
        "exit_ebitda", "exit_ev", "ending_debt", "ending_cash", "exit_equity",
    ):
        assert exit_block[key] is not None
    assert exit_block["mom"] is not None
    assert exit_block["irr"] is not None

    # §8 sensitivity shape: three named 5×5 grids.
    sens = body["sensitivities"]
    assert set(sens) == {
        "irr_exit_vs_growth", "irr_entry_vs_exit", "mom_exit_vs_margin",
    }
    for grid in sens.values():
        assert {"row_label", "col_label", "rows", "cols", "values"} <= set(grid)
        assert len(grid["rows"]) == 5
        assert len(grid["cols"]) == 5
        assert len(grid["values"]) == 5
        assert all(len(row) == 5 for row in grid["values"])

    # Assumptions echoed.
    assert body["assumptions"]["entry_multiple"] == pytest.approx(8.0)
    assert body["assumptions"]["holding_period"] == 5


def test_lbo_post_validation_422(api: TestClient) -> None:
    bad = dict(LBO_ASSUMPTIONS, revenue_growth=[0.05] * 3)  # wrong length
    assert api.post("/api/companies/TESTCO/lbo", json=bad).status_code == 422
    bad = dict(LBO_ASSUMPTIONS, debt_multiple=9.0)  # >= entry_multiple
    assert api.post("/api/companies/TESTCO/lbo", json=bad).status_code == 422


# ---------------------------------------------------------------------------
# Score + memo
# ---------------------------------------------------------------------------


def test_score_testco(api: TestClient) -> None:
    resp = api.get("/api/companies/TESTCO/score")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ticker"] == "TESTCO"
    assert 0.0 <= body["total"] <= 100.0
    assert body["rating"] in {"Attractive", "Watchlist", "Pass"}
    assert len(body["components"]) == 6
    assert sum(c["weight"] for c in body["components"]) == pytest.approx(1.0)
    for component in body["components"]:
        assert component["reason"]
    assert body["disclaimer"]


def test_memo_default_assumptions(api: TestClient) -> None:
    resp = api.post("/api/companies/TESTCO/memo", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ticker"] == "TESTCO"
    assert [s["key"] for s in body["sections"]] == MEMO_SECTION_KEYS
    assert len(body["sections"]) == 9
    for section in body["sections"]:
        assert section["title"]
        assert section["content"].strip()
    assert body["rating"] in {"Attractive", "Watchlist", "Pass"}
    assert body["disclaimer"]


def test_memo_with_custom_assumptions(api: TestClient) -> None:
    resp = api.post(
        "/api/companies/TESTCO/memo", json={"lbo_assumptions": LBO_ASSUMPTIONS}
    )
    assert resp.status_code == 200
    assert len(resp.json()["sections"]) == 9


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_auth_register_me_login_flow(api: TestClient) -> None:
    headers = _auth_headers(api, "flow@example.com", "password123")

    me = api.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "flow@example.com"
    assert isinstance(me.json()["id"], int)

    login = api.post(
        "/api/auth/login",
        json={"email": "flow@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    body = login.json()
    assert body["token_type"] == "bearer"
    me2 = api.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me2.status_code == 200
    assert me2.json()["email"] == "flow@example.com"


def test_auth_duplicate_register_409(api: TestClient) -> None:
    _auth_headers(api, "dup@example.com")
    resp = api.post(
        "/api/auth/register",
        json={"email": "dup@example.com", "password": "password123"},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]


def test_auth_wrong_password_401(api: TestClient) -> None:
    _auth_headers(api, "wrongpw@example.com")
    resp = api.post(
        "/api/auth/login",
        json={"email": "wrongpw@example.com", "password": "not-the-password"},
    )
    assert resp.status_code == 401


def test_auth_unknown_email_401(api: TestClient) -> None:
    resp = api.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "password123"},
    )
    assert resp.status_code == 401


def test_auth_me_requires_token(api: TestClient) -> None:
    assert api.get("/api/auth/me").status_code == 401
    assert (
        api.get(
            "/api/auth/me", headers={"Authorization": "Bearer garbage"}
        ).status_code
        == 401
    )


def test_auth_short_password_422(api: TestClient) -> None:
    resp = api.post(
        "/api/auth/register", json={"email": "short@example.com", "password": "short"}
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Saved deals (Bearer-gated CRUD, §12)
# ---------------------------------------------------------------------------


def _count_lbo_outputs(api: TestClient) -> int:
    session_factory = api.session_factory  # type: ignore[attr-defined]
    with session_factory() as db:
        return db.scalar(select(func.count(LboOutputRecord.id))) or 0


def test_deals_require_auth(api: TestClient) -> None:
    assert api.get("/api/deals").status_code == 401
    assert api.post("/api/deals", json={"ticker": "TESTCO"}).status_code == 401
    assert (
        api.put(
            "/api/deals/1/assumptions", json={"lbo_assumptions": LBO_ASSUMPTIONS}
        ).status_code
        == 401
    )
    assert api.delete("/api/deals/1").status_code == 401


def test_deals_unknown_ticker_404(api: TestClient) -> None:
    headers = _auth_headers(api)
    resp = api.post("/api/deals", json={"ticker": "ZZZZ"}, headers=headers)
    assert resp.status_code == 404


def test_deals_end_to_end(api: TestClient) -> None:
    headers = _auth_headers(api)

    # Save TESTCO (lowercase on purpose: tickers are case-insensitive).
    created = api.post("/api/deals", json={"ticker": "testco"}, headers=headers)
    assert created.status_code == 200, created.text
    deal = created.json()
    deal_id = deal["id"]
    assert deal["ticker"] == "TESTCO"
    assert deal["company_name"] == "Testco Industrials Inc"
    assert 0.0 <= deal["score"] <= 100.0
    assert deal["rating"] in {"Attractive", "Watchlist", "Pass"}
    # Snapshots embedded: memo (nine sections) + default assumptions (6.5x).
    assert [s["key"] for s in deal["memo"]["sections"]] == MEMO_SECTION_KEYS
    assert deal["lbo_assumptions"]["entry_multiple"] == pytest.approx(6.5)
    assert _count_lbo_outputs(api) == 1

    # List: one deal with embedded memo + assumptions.
    listed = api.get("/api/deals", headers=headers)
    assert listed.status_code == 200
    deals = listed.json()
    assert len(deals) == 1
    assert deals[0]["id"] == deal_id
    assert deals[0]["memo"] is not None
    assert deals[0]["lbo_assumptions"] is not None

    # Update assumptions: changed payload reflected, lbo_outputs appended.
    updated = api.put(
        f"/api/deals/{deal_id}/assumptions",
        json={"lbo_assumptions": LBO_ASSUMPTIONS},
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["lbo_assumptions"]["entry_multiple"] == pytest.approx(8.0)
    assert _count_lbo_outputs(api) == 2
    relisted = api.get("/api/deals", headers=headers).json()
    assert relisted[0]["lbo_assumptions"]["entry_multiple"] == pytest.approx(8.0)

    # Duplicate save -> 409.
    duplicate = api.post("/api/deals", json={"ticker": "TESTCO"}, headers=headers)
    assert duplicate.status_code == 409

    # Delete -> 204, then the list is empty and a re-delete 404s.
    deleted = api.delete(f"/api/deals/{deal_id}", headers=headers)
    assert deleted.status_code == 204
    assert api.get("/api/deals", headers=headers).json() == []
    assert api.delete(f"/api/deals/{deal_id}", headers=headers).status_code == 404


def test_deals_of_other_users_are_invisible(api: TestClient) -> None:
    owner = _auth_headers(api, "owner@example.com")
    other = _auth_headers(api, "other@example.com")

    deal_id = api.post(
        "/api/deals", json={"ticker": "TESTCO"}, headers=owner
    ).json()["id"]

    assert api.get("/api/deals", headers=other).json() == []
    assert (
        api.put(
            f"/api/deals/{deal_id}/assumptions",
            json={"lbo_assumptions": LBO_ASSUMPTIONS},
            headers=other,
        ).status_code
        == 404
    )
    assert api.delete(f"/api/deals/{deal_id}", headers=other).status_code == 404
    # Owner still sees the deal untouched.
    assert len(api.get("/api/deals", headers=owner).json()) == 1


def test_provider_dep_is_singleton_and_warm(monkeypatch):
    """get_provider_dep returns one shared instance (no per-request rebuild),
    and warm_provider builds it + its search index once at startup."""
    import app.api.deps as deps
    from app.providers.mock import MockProvider

    # Reset any singleton from earlier tests; force mock mode for isolation.
    deps._provider_singleton = None
    monkeypatch.setattr(deps.settings, "data_provider", "mock", raising=False)

    deps.warm_provider()
    first = deps.get_provider_dep()
    second = deps.get_provider_dep()
    assert first is second  # same object across requests
    assert isinstance(first, MockProvider)
    deps._provider_singleton = None  # leave clean for other tests
