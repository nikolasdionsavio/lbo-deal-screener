"""EDGAR tag mapping for the §19.1 diagnostics fields (dividends_paid,
share_buybacks, receivables, inventory, accounts_payable).

Synthetic companyfacts payloads served through httpx.MockTransport — no live
network calls (pattern per test_providers.py).
"""

from pathlib import Path
from typing import Any, Callable

import httpx
import pytest

from app.providers.edgar import COMPANYFACTS_URL, TICKER_MAP_URL, SecEdgarProvider

REL_TOL = 1e-6
TEST_USER_AGENT = "Test Agent test@example.com"
DIAG_CIK = 999
TICKER_MAP_PAYLOAD = {
    "0": {"cik_str": DIAG_CIK, "ticker": "DIAG", "title": "Diagnostics Test Corp"},
}


def _duration_fact(end: str, val: float) -> dict[str, Any]:
    """An annual cash-flow/income fact (start a year before end)."""
    return {
        "start": str(int(end[:4]) - 1) + end[4:],
        "end": end,
        "val": val,
        "fy": int(end[:4]),
        "fp": "FY",
        "form": "10-K",
        "filed": f"{int(end[:4]) + 1}-02-15",
    }


def _instant_fact(end: str, val: float) -> dict[str, Any]:
    """A balance-sheet fact (no start date)."""
    fact = _duration_fact(end, val)
    del fact["start"]
    return fact


def _tag(*facts: dict[str, Any]) -> dict[str, Any]:
    return {"units": {"USD": list(facts)}}


# FY2023 + FY2024 with the preferred tag covering only FY2024 for
# dividends_paid / receivables / accounts_payable, so the fallback tag must
# fill FY2023 and must NOT override the preferred tag's FY2024 value.
DIAG_GAAP: dict[str, Any] = {
    "Revenues": _tag(
        _duration_fact("2023-12-31", 400e6), _duration_fact("2024-12-31", 500e6)
    ),
    "PaymentsOfDividends": _tag(_duration_fact("2024-12-31", 30e6)),
    "PaymentsOfDividendsCommonStock": _tag(
        _duration_fact("2023-12-31", 25e6), _duration_fact("2024-12-31", 999e6)
    ),
    "PaymentsForRepurchaseOfCommonStock": _tag(
        _duration_fact("2023-12-31", 40e6), _duration_fact("2024-12-31", 50e6)
    ),
    "AccountsReceivableNetCurrent": _tag(_instant_fact("2024-12-31", 120e6)),
    "ReceivablesNetCurrent": _tag(
        _instant_fact("2023-12-31", 100e6), _instant_fact("2024-12-31", 999e6)
    ),
    "InventoryNet": _tag(
        _instant_fact("2023-12-31", 70e6), _instant_fact("2024-12-31", 80e6)
    ),
    "AccountsPayableCurrent": _tag(_instant_fact("2024-12-31", 90e6)),
    "AccountsPayableAndAccruedLiabilitiesCurrent": _tag(
        _instant_fact("2023-12-31", 85e6), _instant_fact("2024-12-31", 999e6)
    ),
}


def _facts_doc(gaap: dict[str, Any]) -> dict[str, Any]:
    return {"facts": {"us-gaap": gaap, "dei": {}}, "entityName": "Diagnostics Test Corp"}


def _handler(gaap: dict[str, Any]) -> Callable[[httpx.Request], httpx.Response]:
    facts_url = COMPANYFACTS_URL.format(cik=DIAG_CIK)

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == TICKER_MAP_URL:
            return httpx.Response(200, json=TICKER_MAP_PAYLOAD)
        if url == facts_url:
            return httpx.Response(200, json=_facts_doc(gaap))
        return httpx.Response(404, json={"detail": "not found"})

    return handler


def _make_provider(cache_dir: Path, gaap: dict[str, Any]) -> SecEdgarProvider:
    client = httpx.Client(transport=httpx.MockTransport(_handler(gaap)))
    return SecEdgarProvider(TEST_USER_AGENT, client=client, cache_dir=cache_dir)


def test_new_fields_mapped_from_preferred_tags(tmp_path: Path) -> None:
    bundle = _make_provider(tmp_path / "cache", DIAG_GAAP).get_company("DIAG")
    assert [y.fiscal_year for y in bundle.financials] == [2023, 2024]
    fy2024 = bundle.financials[-1]
    assert fy2024.dividends_paid == pytest.approx(30e6, rel=REL_TOL)
    assert fy2024.share_buybacks == pytest.approx(50e6, rel=REL_TOL)
    assert fy2024.receivables == pytest.approx(120e6, rel=REL_TOL)
    assert fy2024.inventory == pytest.approx(80e6, rel=REL_TOL)
    assert fy2024.accounts_payable == pytest.approx(90e6, rel=REL_TOL)


def test_preferred_tag_wins_per_period_fallback_fills_gaps(tmp_path: Path) -> None:
    """Per-period merge machinery: the preferred tag's FY2024 value wins over
    the fallback's 999m sentinel; the fallback supplies FY2023."""
    bundle = _make_provider(tmp_path / "cache", DIAG_GAAP).get_company("DIAG")
    fy2023, fy2024 = bundle.financials
    # FY2023 came from the fallback tags.
    assert fy2023.dividends_paid == pytest.approx(25e6, rel=REL_TOL)
    assert fy2023.receivables == pytest.approx(100e6, rel=REL_TOL)
    assert fy2023.accounts_payable == pytest.approx(85e6, rel=REL_TOL)
    # FY2024 kept the preferred tags' values (no 999m sentinel leaked).
    assert fy2024.dividends_paid == pytest.approx(30e6, rel=REL_TOL)
    assert fy2024.receivables == pytest.approx(120e6, rel=REL_TOL)
    assert fy2024.accounts_payable == pytest.approx(90e6, rel=REL_TOL)
    # Multi-tag assembly is flagged for the merged fields.
    for field in ("dividends_paid", "receivables", "accounts_payable"):
        assert any(
            w.startswith(f"{field} assembled from multiple SEC tags")
            for w in bundle.warnings
        ), field


def test_single_tag_fields_have_no_merge_warning(tmp_path: Path) -> None:
    bundle = _make_provider(tmp_path / "cache", DIAG_GAAP).get_company("DIAG")
    for field in ("share_buybacks", "inventory"):
        assert not any(
            w.startswith(f"{field} assembled") for w in bundle.warnings
        ), field


def test_missing_new_tags_give_none_and_warning(tmp_path: Path) -> None:
    gaap = {
        "Revenues": _tag(
            _duration_fact("2023-12-31", 400e6), _duration_fact("2024-12-31", 500e6)
        ),
    }
    bundle = _make_provider(tmp_path / "cache", gaap).get_company("DIAG")
    fy2024 = bundle.financials[-1]
    for field in (
        "dividends_paid", "share_buybacks", "receivables", "inventory",
        "accounts_payable",
    ):
        assert getattr(fy2024, field) is None, field
        assert f"{field} unavailable from SEC EDGAR" in bundle.warnings, field


def test_quarterly_and_10q_facts_excluded_from_new_fields(tmp_path: Path) -> None:
    """The annual-fact selection rules apply to the new tags too: 10-Q facts
    and quarterly-duration 10-K facts must not leak in."""
    ten_q = dict(_duration_fact("2024-12-31", 7e6), form="10-Q", fp="Q4")
    quarterly = dict(_duration_fact("2024-12-31", 8e6), start="2024-10-01")
    gaap = {
        "Revenues": _tag(_duration_fact("2024-12-31", 500e6)),
        "PaymentsOfDividends": _tag(
            _duration_fact("2024-12-31", 30e6), ten_q, quarterly
        ),
        "PaymentsForRepurchaseOfCommonStock": _tag(ten_q, quarterly),
    }
    bundle = _make_provider(tmp_path / "cache", gaap).get_company("DIAG")
    fy2024 = bundle.financials[-1]
    assert fy2024.dividends_paid == pytest.approx(30e6, rel=REL_TOL)
    # Only non-annual facts -> field unavailable.
    assert fy2024.share_buybacks is None
    assert "share_buybacks unavailable from SEC EDGAR" in bundle.warnings
