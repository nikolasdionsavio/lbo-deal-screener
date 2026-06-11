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
    cagr = _revenue_cagr(financials)
    if cagr is not None:
        growth = min(max(cagr, _GROWTH_CLAMP[0]), _GROWTH_CLAMP[1])
        note = f"3-year revenue CAGR of {cagr:.1%} clamped to [0%, 15%], held flat"
        if growth != cagr:
            note += f" (clamped to {growth:.1%})"
        basis["revenue_growth"] = note
    else:
        growth = _FALLBACK_GROWTH
        basis["revenue_growth"] = (
            "Revenue history unavailable; fallback default of 3.0% flat"
        )

    # EBITDA margin: latest fiscal-year margin, flat across years.
    if (
        latest is not None
        and latest.ebitda is not None
        and latest.revenue is not None
        and latest.revenue > 0
    ):
        margin = latest.ebitda / latest.revenue
        basis["ebitda_margin"] = (
            f"Latest fiscal-year EBITDA margin of {margin:.1%} held flat"
        )
    else:
        margin = _FALLBACK_MARGIN
        basis["ebitda_margin"] = (
            "Latest EBITDA margin unavailable; fallback default of 20.0%"
        )

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
    basis["exit_multiple"] = (
        f"Set equal to the entry multiple ({entry_multiple:.1f}x)"
    )
    basis["holding_period"] = "Standard 5-year holding period"

    assumptions = LboAssumptions(
        entry_multiple=entry_multiple,
        debt_multiple=debt_multiple,
        revenue_growth=[growth] * _DEFAULT_HOLDING_PERIOD,
        ebitda_margin=[margin] * _DEFAULT_HOLDING_PERIOD,
        capex_pct_revenue=capex_pct,
        nwc_pct_revenue=_DEFAULT_NWC_PCT,
        tax_rate=_DEFAULT_TAX_RATE,
        interest_rate=_DEFAULT_INTEREST_RATE,
        mandatory_repayment_pct=_DEFAULT_MANDATORY_PCT,
        exit_multiple=entry_multiple,
        holding_period=_DEFAULT_HOLDING_PERIOD,
    )
    return assumptions, basis
