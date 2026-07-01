"""Default LBO assumptions derived from company data (spec §8).

`derive_defaults` returns the `LboAssumptions` plus a `basis` dict mapping each
assumption field to a human-readable note explaining how it was derived
(including fallbacks when inputs are unavailable).
"""

from __future__ import annotations

import math

from app.normalization import currency_mismatch_warning
from app.schemas.company import CompanyDataBundle
from app.schemas.financials import FiscalYearFinancials
from app.schemas.lbo import LboAssumptions

__all__ = ["derive_defaults"]

_FALLBACK_ENTRY_MULTIPLE = 8.0
_MAX_DEBT_MULTIPLE = 6.0
_DEBT_HEADROOM = 0.5  # debt_multiple must stay below entry_multiple
_GROWTH_CLAMP = (0.0, 0.15)
_FALLBACK_GROWTH = 0.03
_FALLBACK_MARGIN = 0.20
_FALLBACK_CAPEX_PCT = 0.04
_DEFAULT_NWC_PCT = 0.02
_DEFAULT_TAX_RATE = 0.25
_DEFAULT_INTEREST_RATE = 0.08
_DEFAULT_MANDATORY_PCT = 0.05
_DEFAULT_HOLDING_PERIOD = 5
_CAPEX_LOOKBACK_YEARS = 3

# Revenue-basis defaults (used when latest-FY EBITDA is non-positive). A
# high-growth company with negative EBITDA cannot be valued or levered off
# EBITDA, so entry prices on EV/Revenue, leverage defaults to zero (growth
# equity), the margin ramps to a conservative terminal level and the exit
# reverts to a normalized peer EV/EBITDA once the company is profitable.
_FALLBACK_ENTRY_REVENUE_MULTIPLE = 3.0
_MAX_ENTRY_REVENUE_MULTIPLE = 6.0
_MIN_ENTRY_REVENUE_MULTIPLE = 0.5
_REVENUE_BASIS_LEVERAGE = 0.0  # loan-to-value; cash-burning names carry no debt
_REVENUE_BASIS_TERMINAL_MARGIN = 0.20  # conservative software-ish terminal EBITDA margin
_FALLBACK_ENTRY_MARGIN = -0.10  # assumed current margin when it cannot be computed
_REVENUE_GROWTH_CLAMP = (0.0, 0.60)  # wider than the EBITDA basis: do not neuter a hyper-grower
_REVENUE_BASIS_FALLBACK_GROWTH = 0.20
_REVENUE_BASIS_DECELERATION = 0.25  # terminal-year growth = this × year-1 growth
# Exit-multiple derivation. The exit prices on EV/EBITDA once profitable, but
# the DEFAULT must not manufacture an unearned revenue re-rating: an entry at a
# depressed EV/Revenue exited at a flat "peer" EBITDA multiple would fabricate
# most of the return. So the default holds the exit EV/Revenue at no more than
# entry (only ever de-rating toward a normalized peer level) and expresses it as
# an EBITDA multiple via the identity EV/Revenue = margin × EV/EBITDA. Return
# then reflects growth and the margin ramp — not a multiple game.
_NORMALIZED_EXIT_EV_REVENUE = 2.5  # profitable-peer EV/Revenue ceiling at exit
_MAX_EXIT_EV_EBITDA = 25.0  # absolute sanity cap on the implied exit EBITDA multiple


def _round_half(x: float) -> float:
    """Round to the nearest 0.5x (ties rounded up, not banker's rounding)."""
    return math.floor(x * 2.0 + 0.5) / 2.0


def _current_ev_ebitda(
    bundle: CompanyDataBundle, latest: FiscalYearFinancials | None
) -> float | None:
    """Current EV/EBITDA: (market cap + total debt - cash) / latest EBITDA.

    None under a quote/reporting currency mismatch (spec §4): the multiple
    would mix currencies, so the 8.0x fallback applies instead. The LBO model
    itself stays single-currency (entry EV = multiple × EBITDA).
    """
    if latest is None or latest.ebitda is None or latest.ebitda <= 0:
        return None
    if currency_mismatch_warning(bundle) is not None:
        return None
    market = bundle.market
    market_cap = market.market_cap if market is not None else None
    if market_cap is None and market is not None and market.share_price is not None:
        shares = market.shares_outstanding or latest.shares_outstanding
        if shares:
            market_cap = market.share_price * shares
    if (
        market_cap is None
        or latest.total_debt is None
        or latest.cash_and_equivalents is None
    ):
        return None
    net_debt = latest.total_debt - latest.cash_and_equivalents
    return (market_cap + net_debt) / latest.ebitda


def _current_ev_revenue(
    bundle: CompanyDataBundle, latest: FiscalYearFinancials | None
) -> float | None:
    """Current EV/Revenue: (market cap + net debt) / latest revenue.

    Unlike `_current_ev_ebitda` this does not require positive EBITDA — it is
    the anchor for the revenue basis. None under a currency mismatch or when
    market data is missing, in which case a conservative fallback applies.
    """
    if latest is None or latest.revenue is None or latest.revenue <= 0:
        return None
    if currency_mismatch_warning(bundle) is not None:
        return None
    market = bundle.market
    market_cap = market.market_cap if market is not None else None
    if market_cap is None and market is not None and market.share_price is not None:
        shares = market.shares_outstanding or latest.shares_outstanding
        if shares:
            market_cap = market.share_price * shares
    if (
        market_cap is None
        or latest.total_debt is None
        or latest.cash_and_equivalents is None
    ):
        return None
    net_debt = latest.total_debt - latest.cash_and_equivalents
    return (market_cap + net_debt) / latest.revenue


def _ramp(start: float, end: float, periods: int) -> list[float]:
    """Per-year path from `start` toward `end`, reaching `end` in the final year.

    Year 1 already steps off `start` (1/N of the way) so the very first modeled
    year shows improvement, and year N lands exactly on `end`.
    """
    if periods <= 1:
        return [end]
    return [start + (end - start) * (i / periods) for i in range(1, periods + 1)]


def _revenue_cagr(financials: list[FiscalYearFinancials]) -> float | None:
    """Revenue CAGR over up to 3 years (mirrors the §6 KPI convention)."""
    with_revenue = [y for y in financials if y.revenue is not None]
    if not with_revenue:
        return None
    end = with_revenue[-1]
    candidates = [
        y
        for y in with_revenue
        if end.fiscal_year - 3 <= y.fiscal_year < end.fiscal_year
    ]
    if not candidates:
        return None
    base = candidates[0]
    if base.revenue is None or base.revenue <= 0 or end.revenue is None:
        return None
    span = end.fiscal_year - base.fiscal_year
    return (end.revenue / base.revenue) ** (1.0 / span) - 1.0


def derive_defaults(bundle: CompanyDataBundle) -> tuple[LboAssumptions, dict[str, str]]:
    """Derive default LBO assumptions and per-field basis notes from a bundle."""
    financials = sorted(bundle.financials, key=lambda y: y.fiscal_year)
    latest = financials[-1] if financials else None
    basis: dict[str, str] = {}
    n = _DEFAULT_HOLDING_PERIOD

    # ---- Shared cash-flow assumptions (identical on both bases) --------------
    # Capex % of revenue: average over the latest 3 fiscal years, fallback 4%.
    capex_ratios = [
        y.capex / y.revenue
        for y in financials[-_CAPEX_LOOKBACK_YEARS:]
        if y.capex is not None and y.revenue is not None and y.revenue > 0
    ]
    if capex_ratios:
        capex_pct = sum(capex_ratios) / len(capex_ratios)
        basis["capex_pct_revenue"] = (
            f"Average capex/revenue of {capex_pct:.1%} over the latest "
            f"{len(capex_ratios)} fiscal year(s)"
        )
    else:
        capex_pct = _FALLBACK_CAPEX_PCT
        basis["capex_pct_revenue"] = (
            "Capex history unavailable; fallback default of 4.0%"
        )

    basis["nwc_pct_revenue"] = (
        "Standard assumption of 2% of revenue growth (history-based derivation "
        "out of MVP scope)"
    )
    basis["tax_rate"] = "Standard assumption of 25%"
    basis["interest_rate"] = "Standard assumption of 8% cash interest"
    basis["mandatory_repayment_pct"] = (
        "Standard assumption of 5% of original opening debt per year"
    )
    basis["holding_period"] = "Standard 5-year holding period"

    cagr = _revenue_cagr(financials)
    latest_ebitda = latest.ebitda if latest is not None else None
    latest_positive = latest_ebitda is not None and latest_ebitda > 0

    if latest_positive:
        # ================= EBITDA basis (company is profitable) ==============
        valuation_basis = "ebitda"
        entry_leverage_pct = 0.0

        # Entry multiple: current EV/EBITDA rounded to 0.5x, fallback 8.0x.
        ev_ebitda = _current_ev_ebitda(bundle, latest)
        if ev_ebitda is not None and ev_ebitda > 0:
            entry_multiple = _round_half(ev_ebitda)
            basis["entry_multiple"] = (
                f"Current EV/EBITDA of {ev_ebitda:.1f}x rounded to the nearest 0.5x"
            )
        else:
            entry_multiple = _FALLBACK_ENTRY_MULTIPLE
            basis["entry_multiple"] = (
                "Current EV/EBITDA unavailable; fallback default of 8.0x"
            )

        # Debt multiple: ~50% of entry, capped 6.0x, kept strictly below entry.
        debt_multiple = min(_MAX_DEBT_MULTIPLE, _round_half(entry_multiple / 2.0))
        debt_multiple = max(0.0, min(debt_multiple, entry_multiple - _DEBT_HEADROOM))
        basis["debt_multiple"] = (
            f"Approximately 50% of the entry multiple ({entry_multiple:.1f}x), "
            "capped at 6.0x"
        )

        # Revenue growth: 3-year CAGR clamped to [0%, 15%], flat across years.
        if cagr is not None:
            g = min(max(cagr, _GROWTH_CLAMP[0]), _GROWTH_CLAMP[1])
            note = f"3-year revenue CAGR of {cagr:.1%} clamped to [0%, 15%], held flat"
            if g != cagr:
                note += f" (clamped to {g:.1%})"
            basis["revenue_growth"] = note
        else:
            g = _FALLBACK_GROWTH
            basis["revenue_growth"] = (
                "Revenue history unavailable; fallback default of 3.0% flat"
            )
        revenue_growth = [g] * n

        # EBITDA margin: latest fiscal-year margin, flat across years.
        if latest is not None and latest.revenue is not None and latest.revenue > 0:
            margin = latest_ebitda / latest.revenue  # type: ignore[operator]
            basis["ebitda_margin"] = (
                f"Latest fiscal-year EBITDA margin of {margin:.1%} held flat"
            )
        else:
            margin = _FALLBACK_MARGIN
            basis["ebitda_margin"] = (
                "Latest EBITDA margin unavailable; fallback default of 20.0%"
            )
        ebitda_margin = [margin] * n

        exit_multiple = entry_multiple
        basis["exit_multiple"] = (
            f"Set equal to the entry multiple ({entry_multiple:.1f}x)"
        )
        basis["valuation_basis"] = (
            "EBITDA basis: the company is EBITDA-positive, so entry and exit "
            "price on EV/EBITDA."
        )
        basis["entry_leverage_pct"] = (
            "Not used on the EBITDA basis; opening debt is set by the debt "
            "multiple (turns of EBITDA)."
        )
    else:
        # ============== Revenue basis (non-positive EBITDA) ==================
        # A negative-EBITDA high-growth company: entry prices on EV/Revenue,
        # value rests on the projected margin ramp to profitability, and the
        # exit reverts to EV/EBITDA once profitable.
        valuation_basis = "revenue"
        debt_multiple = 0.0  # unused on this basis; kept below any EV/Revenue entry

        # Entry EV/Revenue: current EV/Revenue if computable (rounded, capped),
        # else a conservative 3.0x. Always editable.
        ev_rev = _current_ev_revenue(bundle, latest)
        if ev_rev is not None and ev_rev > 0:
            entry_multiple = max(
                _MIN_ENTRY_REVENUE_MULTIPLE,
                _round_half(min(ev_rev, _MAX_ENTRY_REVENUE_MULTIPLE)),
            )
            basis["entry_multiple"] = (
                f"Current EV/Revenue of {ev_rev:.1f}x rounded to the nearest 0.5x "
                f"(capped at {_MAX_ENTRY_REVENUE_MULTIPLE:.0f}x). EBITDA is "
                "non-positive, so revenue is the entry basis."
            )
        else:
            entry_multiple = _FALLBACK_ENTRY_REVENUE_MULTIPLE
            basis["entry_multiple"] = (
                "EV/Revenue unavailable; conservative fallback of 3.0x. EBITDA "
                "is non-positive, so revenue is the entry basis."
            )

        # Leverage: none by default — a cash-burning business is modeled as a
        # growth-equity structure.
        entry_leverage_pct = _REVENUE_BASIS_LEVERAGE
        basis["entry_leverage_pct"] = (
            "No leverage assumed by default (0% loan-to-value): a cash-burning "
            "company is modeled as growth equity. Editable up to 70% LTV."
        )
        basis["debt_multiple"] = (
            "Not used on the revenue basis; leverage is a fraction of entry EV "
            "(loan-to-value), not turns of EBITDA."
        )

        # Growth: observed CAGR clamped to [0%, 60%], decelerating across hold.
        hi = _REVENUE_GROWTH_CLAMP[1]
        if cagr is not None:
            g0 = min(max(cagr, _REVENUE_GROWTH_CLAMP[0]), hi)
            # An off-a-tiny-base CAGR (reverse mergers, first revenue year) can
            # be absurdly large; quoting it verbatim reads as a data glitch, so
            # phrase it as a cap rather than printing the raw figure.
            if cagr > hi:
                src = f"Revenue CAGR exceeds {hi:.0%}, so growth is capped at {hi:.0%}"
            else:
                src = f"3-year revenue CAGR of {cagr:.1%}"
        else:
            g0 = _REVENUE_BASIS_FALLBACK_GROWTH
            src = "Revenue history unavailable; assumed 20.0%"
        g_terminal = g0 * _REVENUE_BASIS_DECELERATION
        revenue_growth = _ramp(g0, g_terminal, n)
        # _ramp lands year 1 above g0; front-load year 1 at g0 for growth so the
        # first modeled year matches the observed rate before decelerating.
        revenue_growth[0] = g0
        basis["revenue_growth"] = (
            f"{src}, decelerating from {g0:.0%} to {g_terminal:.0%} across the "
            "hold."
        )

        # Margin ramp: latest (negative) margin -> conservative terminal margin.
        if latest is not None and latest.revenue is not None and latest.revenue > 0:
            m0 = latest_ebitda / latest.revenue  # type: ignore[operator]
            m0_src = f"the latest {m0:.1%}"
        else:
            m0 = _FALLBACK_ENTRY_MARGIN
            m0_src = f"an assumed {m0:.1%}"
        ebitda_margin = _ramp(m0, _REVENUE_BASIS_TERMINAL_MARGIN, n)
        basis["ebitda_margin"] = (
            f"Margin ramps from {m0_src} to a terminal "
            f"{_REVENUE_BASIS_TERMINAL_MARGIN:.0%} over the hold (linear). Value "
            "is predicated on this ramp — the single most load-bearing input."
        )

        # Exit multiple: hold the exit EV/Revenue at no more than entry (only
        # de-rate toward a normalized peer level), then express it as an EBITDA
        # multiple via EV/Revenue = terminal margin × EV/EBITDA. This avoids
        # baking a revenue re-rating into the default return.
        exit_ev_rev = min(_NORMALIZED_EXIT_EV_REVENUE, entry_multiple)
        exit_multiple = min(
            exit_ev_rev / _REVENUE_BASIS_TERMINAL_MARGIN, _MAX_EXIT_EV_EBITDA
        )
        if exit_ev_rev < entry_multiple:
            basis["exit_multiple"] = (
                f"Exit at {exit_multiple:.1f}x EV/EBITDA — a normalized peer "
                f"{exit_ev_rev:.1f}x EV/Revenue at the terminal "
                f"{_REVENUE_BASIS_TERMINAL_MARGIN:.0%} margin, a de-rating from "
                f"the {entry_multiple:.1f}x entry revenue multiple."
            )
        else:
            basis["exit_multiple"] = (
                f"Exit at {exit_multiple:.1f}x EV/EBITDA, set to hold the exit "
                f"EV/Revenue flat with the {entry_multiple:.1f}x entry (no "
                "re-rating assumed). Raise it if you expect a re-rating as the "
                "company matures."
            )
        basis["valuation_basis"] = (
            "Revenue basis: the latest EBITDA is non-positive, so entry prices "
            "on EV/Revenue and the exit prices on EV/EBITDA once the margin "
            "turns positive."
        )

    assumptions = LboAssumptions(
        valuation_basis=valuation_basis,
        entry_multiple=entry_multiple,
        debt_multiple=debt_multiple,
        entry_leverage_pct=entry_leverage_pct,
        revenue_growth=revenue_growth,
        ebitda_margin=ebitda_margin,
        capex_pct_revenue=capex_pct,
        nwc_pct_revenue=_DEFAULT_NWC_PCT,
        tax_rate=_DEFAULT_TAX_RATE,
        interest_rate=_DEFAULT_INTEREST_RATE,
        mandatory_repayment_pct=_DEFAULT_MANDATORY_PCT,
        exit_multiple=exit_multiple,
        holding_period=n,
    )
    return assumptions, basis
