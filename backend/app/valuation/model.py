"""Valuation: current multiples and EV/EBITDA valuation range (spec §7).

Current multiples are TracedValue entries (formula + inputs + period +
warnings). The valuation range applies user-editable low/base/high EV/EBITDA
multiples to the latest fiscal-year EBITDA. Missing inputs yield None values
plus warnings — this module never raises on bad/absent data.
"""

from __future__ import annotations

import math

from app.schemas.company import CompanyDataBundle
from app.schemas.financials import FiscalYearFinancials
from app.schemas.kpi import TracedInput, TracedValue
from app.schemas.valuation import (
    ValuationAssumptions,
    ValuationCase,
    ValuationRequest,
    ValuationResponse,
)

__all__ = ["compute_valuation"]

_FALLBACK_BASE_MULTIPLE = 8.0
_RANGE_SPREAD = 2.0
_MIN_LOW_MULTIPLE = 1.0


def _round_half(x: float) -> float:
    """Round to the nearest 0.5x (ties rounded up, not banker's rounding)."""
    return math.floor(x * 2.0 + 0.5) / 2.0


def _ratio(
    numerator: float | None, denominator: float | None
) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def compute_valuation(
    bundle: CompanyDataBundle, request: ValuationRequest | None = None
) -> ValuationResponse:
    """Compute current multiples and the implied EV/EBITDA valuation range."""
    request = request or ValuationRequest()
    financials = sorted(bundle.financials, key=lambda y: y.fiscal_year)
    latest: FiscalYearFinancials | None = financials[-1] if financials else None
    fy_period = f"FY{latest.fiscal_year}" if latest is not None else "N/A"
    market = bundle.market
    market_period = (
        market.as_of if market is not None and market.as_of else bundle.fetched_at
    )

    warnings: list[str] = []

    share_price = market.share_price if market is not None else None
    shares: float | None = None
    if market is not None and market.shares_outstanding:
        shares = market.shares_outstanding
    elif latest is not None and latest.shares_outstanding:
        shares = latest.shares_outstanding

    market_cap = market.market_cap if market is not None else None
    market_cap_warnings: list[str] = []
    if market_cap is None and share_price is not None and shares:
        market_cap = share_price * shares
        market_cap_warnings.append(
            "Market cap derived as share price × shares outstanding"
        )
    if market_cap is None:
        warnings.append("Market data unavailable")
        market_cap_warnings.append("Market data unavailable")

    revenue = latest.revenue if latest is not None else None
    ebitda = latest.ebitda if latest is not None else None
    net_income = latest.net_income if latest is not None else None
    fcf = latest.free_cash_flow if latest is not None else None
    total_debt = latest.total_debt if latest is not None else None
    cash = latest.cash_and_equivalents if latest is not None else None
    net_debt = (
        total_debt - cash if total_debt is not None and cash is not None else None
    )
    enterprise_value = (
        market_cap + net_debt
        if market_cap is not None and net_debt is not None
        else None
    )

    def _missing(pairs: list[tuple[str, float | None, str]]) -> list[str]:
        return [
            f"{label} unavailable" for label, value, _period in pairs if value is None
        ]

    def _traced(
        key: str,
        label: str,
        value: float | None,
        unit: str,
        period: str,
        formula: str,
        input_pairs: list[tuple[str, float | None, str]],
        extra_warnings: list[str] | None = None,
    ) -> TracedValue:
        return TracedValue(
            key=key,
            label=label,
            value=value,
            unit=unit,  # type: ignore[arg-type]
            period=period,
            formula=formula,
            inputs=[
                TracedInput(field=field, value=val, period=per)
                for field, val, per in input_pairs
            ],
            warnings=(extra_warnings or []) + _missing(input_pairs),
        )

    ev_inputs = [
        ("market_cap", market_cap, market_period),
        ("total_debt", total_debt, fy_period),
        ("cash_and_equivalents", cash, fy_period),
    ]
    multiples: list[TracedValue] = [
        _traced(
            "market_cap",
            "Market Capitalization",
            market_cap,
            "currency",
            market_period,
            "Share price × Shares outstanding",
            [
                ("share_price", share_price, market_period),
                ("shares_outstanding", shares, market_period),
            ],
            extra_warnings=market_cap_warnings,
        ),
        _traced(
            "enterprise_value",
            "Enterprise Value",
            enterprise_value,
            "currency",
            fy_period,
            "Market cap + Total debt − Cash",
            ev_inputs,
        ),
        _traced(
            "ev_revenue",
            "EV / Revenue",
            _ratio(enterprise_value, revenue),
            "multiple",
            fy_period,
            "Enterprise value / Revenue",
            [
                ("enterprise_value", enterprise_value, fy_period),
                ("revenue", revenue, fy_period),
            ],
        ),
        _traced(
            "ev_ebitda",
            "EV / EBITDA",
            _ratio(enterprise_value, ebitda),
            "multiple",
            fy_period,
            "Enterprise value / EBITDA",
            [
                ("enterprise_value", enterprise_value, fy_period),
                ("ebitda", ebitda, fy_period),
            ],
        ),
        _traced(
            "pe",
            "Price / Earnings",
            _ratio(market_cap, net_income),
            "multiple",
            fy_period,
            "Market cap / Net income",
            [
                ("market_cap", market_cap, market_period),
                ("net_income", net_income, fy_period),
            ],
        ),
        _traced(
            "price_sales",
            "Price / Sales",
            _ratio(market_cap, revenue),
            "multiple",
            fy_period,
            "Market cap / Revenue",
            [
                ("market_cap", market_cap, market_period),
                ("revenue", revenue, fy_period),
            ],
        ),
        _traced(
            "fcf_yield",
            "FCF Yield",
            _ratio(fcf, market_cap),
            "percent",
            fy_period,
            "Free cash flow / Market cap",
            [
                ("free_cash_flow", fcf, fy_period),
                ("market_cap", market_cap, market_period),
            ],
        ),
    ]

    # Default multiples: base = current EV/EBITDA rounded to the nearest 0.5x;
    # low = max(1.0, base − 2); high = base + 2. Fallback base 8.0x + warning.
    current_ev_ebitda = _ratio(enterprise_value, ebitda)
    if current_ev_ebitda is not None and current_ev_ebitda > 0:
        default_base = _round_half(current_ev_ebitda)
    else:
        default_base = _FALLBACK_BASE_MULTIPLE
        if request.base is None:
            warnings.append(
                "Current EV/EBITDA unavailable; default base multiple of "
                "8.0x applied"
            )
    base = request.base if request.base is not None else default_base
    low = (
        request.low
        if request.low is not None
        else max(_MIN_LOW_MULTIPLE, base - _RANGE_SPREAD)
    )
    high = request.high if request.high is not None else base + _RANGE_SPREAD
    assumptions = ValuationAssumptions(low=low, base=base, high=high)

    if ebitda is None:
        warnings.append(
            f"EBITDA unavailable for {fy_period}; implied valuation range "
            "not computed"
        )
    elif net_debt is None:
        warnings.append(
            f"Net debt unavailable for {fy_period}; implied equity value "
            "not computed"
        )
    if shares is None:
        warnings.append(
            "Shares outstanding unavailable; implied share price not computed"
        )
    if share_price is None:
        warnings.append(
            "Share price unavailable; premium vs current not computed"
        )

    cases: list[ValuationCase] = []
    for case_name, multiple in (("low", low), ("base", base), ("high", high)):
        implied_ev = multiple * ebitda if ebitda is not None else None
        implied_equity = (
            implied_ev - net_debt
            if implied_ev is not None and net_debt is not None
            else None
        )
        implied_share_price = (
            implied_equity / shares
            if implied_equity is not None and shares
            else None
        )
        premium_vs_current = (
            implied_share_price / share_price - 1
            if implied_share_price is not None and share_price
            else None
        )
        cases.append(
            ValuationCase(
                case=case_name,
                multiple=multiple,
                implied_ev=implied_ev,
                implied_equity=implied_equity,
                implied_share_price=implied_share_price,
                premium_vs_current=premium_vs_current,
            )
        )

    as_of = (
        (market.as_of if market is not None else None)
        or (latest.period_end if latest is not None else None)
        or bundle.fetched_at
    )
    return ValuationResponse(
        ticker=bundle.info.ticker,
        as_of=as_of,
        multiples=multiples,
        assumptions=assumptions,
        range=cases,
        warnings=warnings,
    )
