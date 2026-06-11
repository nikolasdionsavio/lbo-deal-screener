"""IRR / MoM unit tests (spec §15)."""

import numpy as np
import pytest

from app.lbo.irr import irr, mom


def test_irr_closed_form_five_year_double() -> None:
    """irr([-1000, 0, 0, 0, 0, 2000]) == 2^(1/5) - 1 (money doubles in 5y)."""
    result = irr([-1000.0, 0.0, 0.0, 0.0, 0.0, 2000.0])
    assert result is not None
    assert result == pytest.approx(2.0 ** 0.2 - 1.0, rel=1e-9)


def test_irr_closed_form_negative_rate() -> None:
    """Halving over 3 years: irr == 0.5^(1/3) - 1 (negative)."""
    result = irr([-1000.0, 0.0, 0.0, 500.0])
    assert result is not None
    assert result == pytest.approx(0.5 ** (1.0 / 3.0) - 1.0, rel=1e-9)


def test_mom_simple_double() -> None:
    assert mom([-1000.0, 0.0, 0.0, 0.0, 0.0, 2000.0]) == pytest.approx(2.0)


def test_irr_all_negative_returns_none() -> None:
    assert irr([-1000.0, -50.0, -25.0]) is None


def test_irr_all_positive_returns_none() -> None:
    assert irr([1000.0, 50.0, 25.0]) is None


def test_irr_trivial_inputs_return_none() -> None:
    assert irr([]) is None
    assert irr([-1000.0]) is None


def test_mom_no_invested_capital_returns_none() -> None:
    assert mom([0.0, 100.0]) is None


def test_irr_multi_flow_vs_numpy_roots() -> None:
    """Cross-check a multi-flow IRR against the polynomial roots."""
    flows = [-1000.0, 300.0, 420.0, 680.0]
    result = irr(flows)
    assert result is not None

    # NPV(r) = sum cf_t * x^t with x = 1/(1+r). numpy.roots wants
    # highest-degree-first coefficients, so reverse the flow list.
    roots = np.roots(list(reversed(flows)))
    real_positive = [r.real for r in roots if abs(r.imag) < 1e-9 and r.real > 0]
    candidates = [1.0 / x - 1.0 for x in real_positive]
    in_range = [r for r in candidates if -0.99 <= r <= 10.0]
    assert len(in_range) == 1
    assert result == pytest.approx(in_range[0], rel=1e-6)


def test_irr_npv_residual_is_zero() -> None:
    flows = [-1000.0, 250.0, 300.0, 350.0, 400.0]
    rate = irr(flows)
    assert rate is not None
    npv = sum(cf / (1.0 + rate) ** t for t, cf in enumerate(flows))
    assert abs(npv) < 1e-6
