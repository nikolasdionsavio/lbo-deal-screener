"""Covenant-headroom stress: turn the LBO cash flows into a credit view.

An IRR says nothing about whether the debt survives the hold. Lenders set
maintenance covenants; this module tests each modeled year against them and
reports headroom, breaches, and an approximate cushion to a leverage breach.

All inputs already exist on the per-year `LboYear` output — no new data.
"""

from __future__ import annotations

from app.schemas.lbo import (
    CovenantLimits,
    CovenantYear,
    LboCovenants,
    LboYear,
)

__all__ = ["compute_covenants"]


def compute_covenants(
    years: list[LboYear],
    *,
    mandatory_principal: float,
    limits: CovenantLimits | None = None,
) -> LboCovenants:
    """Test each year against the covenant package.

    `mandatory_principal` is the fixed scheduled amortisation per year
    (mandatory_repayment_pct × opening debt), part of debt service for the DSCR.
    """
    limits = limits or CovenantLimits()
    rows: list[CovenantYear] = []
    any_breach = False
    cushions: list[float] = []

    for y in years:
        net_debt = y.ending_debt - y.ending_cash
        # Net leverage: only meaningful on positive EBITDA.
        leverage = net_debt / y.ebitda if y.ebitda > 0 else None
        # Interest coverage: undefined (unconstrained) when there is no interest.
        coverage = y.ebitda / y.interest if y.interest > 0 else None
        # DSCR = cash available for debt service / debt service.
        debt_service = y.interest + mandatory_principal
        cfads = y.fcf + y.interest  # cash before servicing interest
        dscr = cfads / debt_service if debt_service > 0 else None

        breached = (
            (leverage is not None and leverage > limits.max_net_debt_to_ebitda)
            or (coverage is not None and coverage < limits.min_interest_coverage)
            or (dscr is not None and dscr < limits.min_fcf_dscr)
        )
        any_breach = any_breach or breached
        rows.append(
            CovenantYear(
                year=y.year,
                net_debt_to_ebitda=leverage,
                interest_coverage=coverage,
                fcf_dscr=dscr,
                breached=breached,
            )
        )

        # EBITDA cushion to a leverage breach: EBITDA could fall to
        # net_debt / max_leverage before breaching, i.e. a (1 - leverage/max)
        # fraction of this year's EBITDA (debt path held fixed).
        if (
            leverage is not None
            and leverage > 0
            and limits.max_net_debt_to_ebitda > 0
            and net_debt > 0
        ):
            cushions.append(1.0 - leverage / limits.max_net_debt_to_ebitda)

    return LboCovenants(
        limits=limits,
        years=rows,
        any_breach=any_breach,
        min_ebitda_cushion_pct=min(cushions) if cushions else None,
    )
