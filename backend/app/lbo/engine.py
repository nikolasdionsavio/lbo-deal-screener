"""Simplified holding-period LBO engine (spec §8).

`run_core` produces entry / per-year / exit blocks (no sensitivities) and is
reused per sensitivity-grid cell. `run_lbo` adds the three 5x5 grids and
returns the full `LboResponse`.

All monetary values are absolute USD floats; rates are decimals.
"""

from __future__ import annotations

from app.lbo.irr import irr
from app.schemas.lbo import LboAssumptions, LboEntry, LboExit, LboResponse, LboYear

__all__ = ["run_core", "run_lbo"]


def run_core(
    entry_ebitda: float,
    entry_revenue: float,
    assumptions: LboAssumptions,
) -> tuple[LboEntry, list[LboYear], LboExit, list[str]]:
    """Run the §8 mechanics once: entry capital structure, N years, exit."""
    a = assumptions
    warnings: list[str] = []

    entry_ev = a.entry_multiple * entry_ebitda
    opening_debt = a.debt_multiple * entry_ebitda
    sponsor_equity = entry_ev - opening_debt
    equity_pct = sponsor_equity / entry_ev if entry_ev != 0 else 0.0
    entry = LboEntry(
        entry_ebitda=entry_ebitda,
        entry_revenue=entry_revenue,
        entry_ev=entry_ev,
        opening_debt=opening_debt,
        sponsor_equity=sponsor_equity,
        equity_pct=equity_pct,
    )

    mandatory = a.mandatory_repayment_pct * opening_debt  # % of ORIGINAL opening debt
    years: list[LboYear] = []
    revenue_prev = entry_revenue
    debt_prev = opening_debt
    cash_prev = 0.0
    for t in range(1, a.holding_period + 1):
        revenue = revenue_prev * (1.0 + a.revenue_growth[t - 1])
        ebitda = a.ebitda_margin[t - 1] * revenue
        capex = a.capex_pct_revenue * revenue
        d_and_a = capex  # simplification per spec: D&A = capex
        delta_nwc = a.nwc_pct_revenue * (revenue - revenue_prev)
        interest = a.interest_rate * debt_prev  # beginning-of-year balance
        ebt = ebitda - d_and_a - interest
        taxes = max(0.0, ebt) * a.tax_rate
        fcf = ebitda - capex - delta_nwc - interest - taxes
        if fcf < 0:
            warnings.append(f"Negative FCF in year {t}; no revolver modeled")
        # Repayment = mandatory amount (mandatory_repayment_pct x opening debt)
        # plus a 100% sweep of positive FCF above it, limited to the cash
        # actually generated (no new borrowing in MVP) and floored at 0 debt.
        # The spec formula min(debt, mandatory + max(0, fcf - mandatory)) with
        # the "repay max(0, fcf) when fcf < mandatory" override reduces to:
        repay = min(debt_prev, max(0.0, fcf))
        cash = cash_prev + max(0.0, fcf - repay)  # excess builds cash after debt = 0
        debt = debt_prev - repay
        years.append(
            LboYear(
                year=t,
                revenue=revenue,
                ebitda=ebitda,
                capex=capex,
                delta_nwc=delta_nwc,
                interest=interest,
                taxes=taxes,
                fcf=fcf,
                debt_repaid=repay,
                ending_debt=debt,
                ending_cash=cash,
            )
        )
        revenue_prev, debt_prev, cash_prev = revenue, debt, cash

    exit_ebitda = years[-1].ebitda
    exit_ev = a.exit_multiple * exit_ebitda
    exit_equity = exit_ev - debt_prev + cash_prev
    mom_value = exit_equity / sponsor_equity if sponsor_equity > 0 else None
    # Equity flows are entry and exit only, so irr == mom^(1/N) - 1 here.
    flows = [-sponsor_equity] + [0.0] * (a.holding_period - 1) + [exit_equity]
    irr_value = irr(flows)
    exit_block = LboExit(
        exit_ebitda=exit_ebitda,
        exit_ev=exit_ev,
        ending_debt=debt_prev,
        ending_cash=cash_prev,
        exit_equity=exit_equity,
        mom=mom_value,
        irr=irr_value,
    )
    return entry, years, exit_block, warnings


def run_lbo(
    entry_ebitda: float,
    entry_revenue: float,
    assumptions: LboAssumptions,
    *,
    ticker: str = "",
) -> LboResponse:
    """Full LBO run: §8 mechanics plus the three sensitivity grids.

    `ticker` is optional so callers without a company context (tests) can omit
    it; the service layer passes the real ticker for the API response.
    """
    # Local import: sensitivities reuses run_core, avoiding a module cycle.
    from app.lbo.sensitivities import compute_sensitivities

    entry, years, exit_block, warnings = run_core(
        entry_ebitda, entry_revenue, assumptions
    )
    sensitivities = compute_sensitivities(entry_ebitda, entry_revenue, assumptions)
    return LboResponse(
        ticker=ticker,
        entry=entry,
        years=years,
        exit=exit_block,
        sensitivities=sensitivities,
        assumptions=assumptions,
        warnings=warnings,
    )
