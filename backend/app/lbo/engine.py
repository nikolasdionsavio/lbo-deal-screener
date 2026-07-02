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

# Sponsor equity below this fraction of entry EV is treated as structurally
# unsafe: a sliver of equity produces a large-but-finite nonsense IRR that would
# still pass a naive "mom > 0" gate. Both MoM and IRR are suppressed below it.
_MIN_EQUITY_FRACTION = 0.05
# A reported IRR above this is flagged as implausible ("check your equity").
_IRR_SANITY_CEILING = 1.0  # 100%


def run_core(
    entry_ebitda: float,
    entry_revenue: float,
    assumptions: LboAssumptions,
) -> tuple[LboEntry, list[LboYear], LboExit, list[str]]:
    """Run the §8 mechanics once: entry capital structure, N years, exit.

    Two bases (spec §8, negative-EBITDA extension):

    * ``ebitda`` — entry EV = entry_multiple × EBITDA, opening debt = turns of
      EBITDA. The classic path; unchanged.
    * ``revenue`` — entry EV = entry_multiple (read as EV/Revenue) × revenue,
      opening debt = entry_leverage_pct × entry EV (loan-to-value). This models
      a high-growth company whose latest EBITDA is negative: it cannot be
      levered or multiplied, so value rests on revenue and on the projected
      margin ramp to profitability. The exit still prices on EV/EBITDA once the
      company is profitable — if it never is, no exit is fabricated.
    """
    a = assumptions
    warnings: list[str] = []

    if a.valuation_basis == "revenue":
        entry_ev = a.entry_multiple * entry_revenue
        opening_debt = a.entry_leverage_pct * entry_ev
        warnings.append(
            f"Entry priced on EV/Revenue of {a.entry_multiple:.1f}x because the "
            "latest fiscal-year EBITDA is not positive; the exit is priced on "
            "EV/EBITDA once the projected margin turns positive. Value is "
            "predicated on reaching future profitability."
        )
        if a.entry_leverage_pct > 0:
            warnings.append(
                f"Leverage sized at {a.entry_leverage_pct:.0%} of entry EV "
                "(loan-to-value), not as turns of EBITDA."
            )
        warnings.append(
            "Return is driven by revenue growth and the margin ramp, not by "
            "deleveraging or multiple expansion. Read the sensitivity range "
            "rather than the point return, and stress the terminal margin and "
            "growth."
        )
    else:
        entry_ev = a.entry_multiple * entry_ebitda
        opening_debt = a.debt_multiple * entry_ebitda
        if entry_ev <= 0:
            warnings.append(
                "Entry EV is non-positive on the EBITDA basis (latest EBITDA is "
                "not positive); switch to the revenue basis to model this company."
            )

    # Sources & Uses. Uses = purchase EV + transaction fees; Sources = new debt
    # + sponsor equity. Equity is the plug, so it absorbs the fees — exactly how
    # the S&U balances in a real deal (fees drag the sponsor's return).
    transaction_fees = a.transaction_fee_pct * entry_ev
    total_uses = entry_ev + transaction_fees
    sponsor_equity = total_uses - opening_debt
    equity_pct = sponsor_equity / total_uses if total_uses != 0 else 0.0
    opening_net_leverage = (opening_debt / entry_ebitda) if entry_ebitda > 0 else None
    entry = LboEntry(
        entry_ebitda=entry_ebitda,
        entry_revenue=entry_revenue,
        entry_ev=entry_ev,
        opening_debt=opening_debt,
        transaction_fees=transaction_fees,
        total_uses=total_uses,
        sponsor_equity=sponsor_equity,
        equity_pct=equity_pct,
        opening_net_leverage=opening_net_leverage,
    )

    mandatory = a.mandatory_repayment_pct * opening_debt  # % of ORIGINAL opening debt
    years: list[LboYear] = []
    revenue_prev = entry_revenue
    debt_prev = opening_debt
    cash_prev = 0.0
    cumulative_burn = 0.0  # sum of negative-FCF years (the funding gap)
    for t in range(1, a.holding_period + 1):
        revenue = revenue_prev * (1.0 + a.revenue_growth[t - 1])
        # Do NOT floor EBITDA at zero: on the revenue basis the early years are
        # deliberately loss-making, and flooring would hide the burn and flatter
        # deleveraging and FCF.
        ebitda = a.ebitda_margin[t - 1] * revenue
        capex = a.capex_pct_revenue * revenue
        d_and_a = capex  # simplification per spec: D&A = capex
        delta_nwc = a.nwc_pct_revenue * (revenue - revenue_prev)
        # max(0, debt) so a mis-set negative balance can never generate phantom
        # interest income; with the default low/zero revenue-basis leverage this
        # is naturally ~0 in the burn years, which is correct.
        interest = a.interest_rate * max(0.0, debt_prev)  # beginning-of-year balance
        ebt = ebitda - d_and_a - interest
        taxes = max(0.0, ebt) * a.tax_rate
        fcf = ebitda - capex - delta_nwc - interest - taxes
        if fcf < 0:
            warnings.append(f"Negative FCF in year {t}; no revolver modeled")
            cumulative_burn += fcf
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
    # An EV/EBITDA exit on a loss is meaningless (a negative exit EV). When the
    # company never reaches positive EBITDA, refuse the exit rather than report
    # a nonsense negative equity value.
    min_equity = _MIN_EQUITY_FRACTION * entry_ev if entry_ev > 0 else 0.0
    returns_ok = entry_ev > 0 and sponsor_equity > min_equity

    if exit_ebitda > 0:
        exit_ev: float | None = a.exit_multiple * exit_ebitda
        exit_equity: float | None = exit_ev - debt_prev + cash_prev
        if returns_ok:
            mom_value = exit_equity / sponsor_equity
            # Equity flows are entry and exit only, so irr == mom^(1/N) - 1.
            flows = [-sponsor_equity] + [0.0] * (a.holding_period - 1) + [exit_equity]
            irr_value = irr(flows)
        else:
            mom_value = irr_value = None
            warnings.append(
                "Sponsor equity is below 5% of entry EV; MoM and IRR are "
                "suppressed because a sliver of equity produces an unreliable "
                "return. Reduce leverage or the entry multiple."
            )
        if irr_value is not None and irr_value > _IRR_SANITY_CEILING:
            warnings.append(
                f"Modeled IRR of {irr_value:.0%} is implausibly high; check the "
                "sponsor equity, exit multiple and terminal margin."
            )
    else:
        exit_ev = None
        exit_equity = None
        mom_value = irr_value = None
        warnings.append(
            "The company does not reach positive EBITDA by exit, so no "
            "EV/EBITDA exit is possible and returns are not demonstrable on this "
            "basis. Raise the terminal margin or extend the holding period."
        )

    if cumulative_burn < 0:
        warnings.append(
            f"Cumulative pre-profit cash burn of {abs(cumulative_burn):,.0f} is "
            "not financed in this model (no revolver or equity cure is modeled); "
            "survival to a profitable exit is assumed."
        )

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
    # Local imports: all reuse run_core / its output, avoiding a module cycle.
    from app.lbo.covenants import compute_covenants
    from app.lbo.scenarios import compute_scenarios
    from app.lbo.sensitivities import compute_sensitivities

    entry, years, exit_block, warnings = run_core(
        entry_ebitda, entry_revenue, assumptions
    )
    scenarios = compute_scenarios(entry_ebitda, entry_revenue, assumptions)
    covenants = compute_covenants(
        years,
        mandatory_principal=assumptions.mandatory_repayment_pct * entry.opening_debt,
    )
    sensitivities = compute_sensitivities(entry_ebitda, entry_revenue, assumptions)
    return LboResponse(
        ticker=ticker,
        entry=entry,
        years=years,
        exit=exit_block,
        scenarios=scenarios,
        covenants=covenants,
        sensitivities=sensitivities,
        assumptions=assumptions,
        warnings=warnings,
    )
