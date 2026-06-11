"""IRR and MoM for LBO cash flows (spec §8).

`irr` solves NPV(rate) = 0 using Newton's method starting at 0.1 with a
bisection fallback on [-0.99, 10.0]. Returns None when the cash flows have no
sign change (no IRR exists) or when no root lies in the bisection bracket.
"""

from __future__ import annotations

__all__ = ["irr", "mom"]

_NEWTON_START = 0.1
_NEWTON_MAX_ITER = 80
_BISECT_LO = -0.99
_BISECT_HI = 10.0
_BISECT_MAX_ITER = 200


def _npv(rate: float, cashflows: list[float]) -> float:
    return sum(cf / (1.0 + rate) ** t for t, cf in enumerate(cashflows))


def _npv_prime(rate: float, cashflows: list[float]) -> float:
    return sum(-t * cf / (1.0 + rate) ** (t + 1) for t, cf in enumerate(cashflows))


def irr(cashflows: list[float]) -> float | None:
    """Internal rate of return of period-indexed cash flows (t = 0, 1, ...).

    None when fewer than two flows, when all flows share one sign (no IRR), or
    when Newton diverges and the bracket [-0.99, 10.0] contains no sign change.
    """
    if len(cashflows) < 2:
        return None
    if not (any(cf > 0 for cf in cashflows) and any(cf < 0 for cf in cashflows)):
        return None  # no sign change in the flows -> no IRR exists

    f_tol = max(abs(cf) for cf in cashflows) * 1e-12

    # Newton's method from 0.1 (spec §8).
    rate = _NEWTON_START
    for _ in range(_NEWTON_MAX_ITER):
        f = _npv(rate, cashflows)
        if abs(f) <= f_tol:
            return rate
        derivative = _npv_prime(rate, cashflows)
        if derivative == 0.0:
            break
        nxt = rate - f / derivative
        if nxt <= -1.0:
            break  # left the domain of the discount factor; fall back
        rate = nxt

    # Bisection fallback on the fixed bracket.
    lo, hi = _BISECT_LO, _BISECT_HI
    f_lo = _npv(lo, cashflows)
    f_hi = _npv(hi, cashflows)
    if f_lo == 0.0:
        return lo
    if f_hi == 0.0:
        return hi
    if (f_lo > 0) == (f_hi > 0):
        return None  # no sign change of NPV in the bracket
    for _ in range(_BISECT_MAX_ITER):
        mid = (lo + hi) / 2.0
        f_mid = _npv(mid, cashflows)
        if abs(f_mid) <= f_tol or (hi - lo) < 1e-13:
            return mid
        if (f_mid > 0) == (f_lo > 0):
            lo, f_lo = mid, f_mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def mom(cashflows: list[float]) -> float | None:
    """Multiple of money: total distributions / total invested capital."""
    invested = -sum(cf for cf in cashflows if cf < 0)
    returned = sum(cf for cf in cashflows if cf > 0)
    if invested <= 0:
        return None
    return returned / invested
