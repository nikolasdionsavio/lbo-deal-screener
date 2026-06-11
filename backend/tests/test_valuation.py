"""Valuation model tests (spec §7, §15)."""

import pytest

from app.schemas.company import CompanyDataBundle
from app.schemas.kpi import TracedValue
from app.schemas.valuation import ValuationRequest, ValuationResponse
from app.valuation.model import compute_valuation

M = 1e6
REL = 1e-6


def _multiple(response: ValuationResponse, key: str) -> TracedValue:
    return next(m for m in response.multiples if m.key == key)


def test_default_multiples_testco(testco_bundle: CompanyDataBundle) -> None:
    """TESTCO EV/EBITDA 6.6x -> base rounds to 6.5x, low 4.5x, high 8.5x."""
    response = compute_valuation(testco_bundle)
    assert response.ticker == "TESTCO"
    assert response.assumptions.base == pytest.approx(6.5)
    assert response.assumptions.low == pytest.approx(4.5)
    assert response.assumptions.high == pytest.approx(8.5)


def test_current_multiples_values(testco_bundle: CompanyDataBundle) -> None:
    response = compute_valuation(testco_bundle)
    keys = [m.key for m in response.multiples]
    assert keys == [
        "market_cap",
        "enterprise_value",
        "ev_revenue",
        "ev_ebitda",
        "pe",
        "price_sales",
        "fcf_yield",
    ]
    assert _multiple(response, "market_cap").value == pytest.approx(1350.0 * M, rel=REL)
    assert _multiple(response, "enterprise_value").value == pytest.approx(
        1650.0 * M, rel=REL
    )
    assert _multiple(response, "ev_revenue").value == pytest.approx(1.65, rel=REL)
    assert _multiple(response, "ev_ebitda").value == pytest.approx(6.6, rel=REL)
    assert _multiple(response, "pe").value == pytest.approx(1350.0 / 135.0, rel=REL)
    assert _multiple(response, "price_sales").value == pytest.approx(1.35, rel=REL)
    assert _multiple(response, "fcf_yield").value == pytest.approx(
        180.0 / 1350.0, rel=REL
    )
    assert _multiple(response, "market_cap").unit == "currency"
    assert _multiple(response, "enterprise_value").unit == "currency"
    assert _multiple(response, "ev_ebitda").unit == "multiple"
    assert _multiple(response, "fcf_yield").unit == "percent"


def test_implied_range_testco(testco_bundle: CompanyDataBundle) -> None:
    """§15: implied equity = m x 250m - 300m; share price = equity / 100m;
    premium vs the 13.50 share price."""
    response = compute_valuation(testco_bundle)
    assert [c.case for c in response.range] == ["low", "base", "high"]
    for case in response.range:
        m = case.multiple
        expected_equity = m * 250.0 * M - 300.0 * M
        assert case.implied_ev == pytest.approx(m * 250.0 * M, rel=REL)
        assert case.implied_equity == pytest.approx(expected_equity, rel=REL)
        assert case.implied_share_price == pytest.approx(
            expected_equity / 100.0e6, rel=REL
        )
        assert case.implied_share_price is not None
        assert case.premium_vs_current == pytest.approx(
            case.implied_share_price / 13.50 - 1.0, rel=REL
        )


def test_base_case_premium_value(testco_bundle: CompanyDataBundle) -> None:
    response = compute_valuation(testco_bundle)
    base_case = next(c for c in response.range if c.case == "base")
    # 6.5 x 250m - 300m = 1325m -> $13.25 vs $13.50 -> -1.85% premium.
    assert base_case.implied_share_price == pytest.approx(13.25, rel=REL)
    assert base_case.premium_vs_current == pytest.approx(13.25 / 13.5 - 1.0, rel=REL)


def test_user_supplied_multiples(testco_bundle: CompanyDataBundle) -> None:
    response = compute_valuation(
        testco_bundle, ValuationRequest(low=5.0, base=7.0, high=9.0)
    )
    assert response.assumptions.low == pytest.approx(5.0)
    assert response.assumptions.base == pytest.approx(7.0)
    assert response.assumptions.high == pytest.approx(9.0)
    base_case = next(c for c in response.range if c.case == "base")
    assert base_case.implied_equity == pytest.approx(
        7.0 * 250.0 * M - 300.0 * M, rel=REL
    )


def test_partial_override_base_only(testco_bundle: CompanyDataBundle) -> None:
    """A user-supplied base re-anchors the defaulted low/high."""
    response = compute_valuation(testco_bundle, ValuationRequest(base=10.0))
    assert response.assumptions.base == pytest.approx(10.0)
    assert response.assumptions.low == pytest.approx(8.0)
    assert response.assumptions.high == pytest.approx(12.0)


def test_default_base_when_ev_ebitda_unavailable(
    testco_bundle: CompanyDataBundle,
) -> None:
    """§15: EV/EBITDA unavailable -> default base 8.0x plus a warning."""
    bundle = testco_bundle.model_copy(update={"market": None})
    response = compute_valuation(bundle)
    assert response.assumptions.base == pytest.approx(8.0)
    assert response.assumptions.low == pytest.approx(6.0)
    assert response.assumptions.high == pytest.approx(10.0)
    assert any("8.0x" in w for w in response.warnings)
    assert any("Market data unavailable" in w for w in response.warnings)
    assert _multiple(response, "ev_ebitda").value is None
    # Implied EV/equity still computable from fundamentals; premium is not.
    base_case = next(c for c in response.range if c.case == "base")
    assert base_case.implied_equity == pytest.approx(
        8.0 * 250.0 * M - 300.0 * M, rel=REL
    )
    assert base_case.premium_vs_current is None


def test_never_raises_on_empty_financials(
    testco_bundle: CompanyDataBundle,
) -> None:
    bundle = testco_bundle.model_copy(update={"financials": [], "market": None})
    response = compute_valuation(bundle)
    assert response.assumptions.base == pytest.approx(8.0)
    for case in response.range:
        assert case.implied_ev is None
        assert case.implied_equity is None
        assert case.implied_share_price is None
        assert case.premium_vs_current is None
    assert response.warnings  # missing data is reported, not raised
