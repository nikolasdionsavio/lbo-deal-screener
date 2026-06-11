"""Traceable KPI calculations (spec §6).

`compute_kpis` turns a `CompanyDataBundle` into the 14-KPI `KpiResponse` with full
traceability (formula, inputs, period, warnings). Missing inputs yield a `None`
value plus a warning — this module never raises on bad/absent data.

All KPIs are fundamentals-only (no market data is used here).
"""

from __future__ import annotations

from typing import Callable

from app.schemas.company import CompanyDataBundle
from app.schemas.financials import FiscalYearFinancials
from app.schemas.kpi import KpiResponse, SeriesPoint, TracedInput, TracedValue

__all__ = ["compute_kpis"]

# Human-readable labels for input fields used in warnings.
_FIELD_LABELS: dict[str, str] = {
    "revenue": "Revenue",
    "cost_of_revenue": "Cost of revenue",
    "gross_profit": "Gross profit",
    "operating_income": "Operating income",
    "depreciation_amortization": "D&A",
    "ebitda": "EBITDA",
    "interest_expense": "Interest expense",
    "tax_expense": "Tax expense",
    "net_income": "Net income",
    "operating_cash_flow": "Operating cash flow",
    "capex": "Capex",
    "free_cash_flow": "Free cash flow",
    "cash_and_equivalents": "Cash and equivalents",
    "total_debt": "Total debt",
    "current_assets": "Current assets",
    "current_liabilities": "Current liabilities",
    "total_equity": "Total equity",
    "dividends_paid": "Dividends paid",
    "share_buybacks": "Share buybacks",
    "receivables": "Receivables",
    "inventory": "Inventory",
    "accounts_payable": "Accounts payable",
}

# Effective-tax clamp bounds and fallback (spec §6, roic row).
_EFFECTIVE_TAX_MIN = 0.0
_EFFECTIVE_TAX_MAX = 0.5
_EFFECTIVE_TAX_FALLBACK = 0.25


def _fy(year: FiscalYearFinancials) -> str:
    return f"FY{year.fiscal_year}"


def _label(field: str) -> str:
    return _FIELD_LABELS.get(field, field)


def _inputs_from(
    year: FiscalYearFinancials | None, fields: list[str], period: str
) -> list[TracedInput]:
    return [
        TracedInput(
            field=field,
            value=getattr(year, field, None) if year is not None else None,
            period=period,
        )
        for field in fields
    ]


def _missing_warnings(
    year: FiscalYearFinancials | None, fields: list[str], period: str
) -> list[str]:
    if year is None:
        return [f"No financial data available for {period}"]
    return [
        f"{_label(field)} unavailable for {period}"
        for field in fields
        if getattr(year, field, None) is None
    ]


def _simple_ratio(
    latest: FiscalYearFinancials | None,
    *,
    key: str,
    label: str,
    unit: str,
    formula: str,
    numerator: Callable[[FiscalYearFinancials], float | None],
    numerator_fields: list[str],
    denominator_field: str,
) -> TracedValue:
    """Generic latest-FY ratio KPI: numerator(year) / year.<denominator_field>.

    None value + warning when any input is missing or the denominator is zero.
    """
    period = _fy(latest) if latest is not None else "N/A"
    fields = numerator_fields + [denominator_field]
    warnings = _missing_warnings(latest, fields, period)
    value: float | None = None
    if latest is not None and not warnings:
        den = getattr(latest, denominator_field)
        num = numerator(latest)
        if den == 0:
            warnings.append(f"{_label(denominator_field)} is zero for {period}; ratio undefined")
        elif num is not None:
            value = num / den
    return TracedValue(
        key=key,
        label=label,
        value=value,
        unit=unit,  # type: ignore[arg-type]
        period=period,
        formula=formula,
        inputs=_inputs_from(latest, fields, period),
        warnings=warnings,
    )


def _revenue_growth_yoy(
    latest: FiscalYearFinancials | None, prior: FiscalYearFinancials | None
) -> TracedValue:
    latest_period = _fy(latest) if latest is not None else "N/A"
    prior_period = _fy(prior) if prior is not None else "N/A"
    period = f"{prior_period}→{latest_period}"
    inputs = [
        TracedInput(
            field="revenue",
            value=latest.revenue if latest is not None else None,
            period=latest_period,
        ),
        TracedInput(
            field="revenue",
            value=prior.revenue if prior is not None else None,
            period=prior_period,
        ),
    ]
    warnings: list[str] = []
    value: float | None = None
    if latest is None:
        warnings.append("No financial data available")
    elif prior is None:
        warnings.append(f"Prior fiscal year (FY{latest.fiscal_year - 1}) unavailable")
    elif latest.revenue is None:
        warnings.append(f"Revenue unavailable for {latest_period}")
    elif prior.revenue is None:
        warnings.append(f"Revenue unavailable for {prior_period}")
    elif prior.revenue == 0:
        warnings.append(f"Revenue is zero for {prior_period}; growth undefined")
    else:
        value = latest.revenue / prior.revenue - 1
    return TracedValue(
        key="revenue_growth_yoy",
        label="Revenue Growth (YoY)",
        value=value,
        unit="percent",
        period=period,
        formula="Revenue_t / Revenue_(t−1) − 1",
        inputs=inputs,
        warnings=warnings,
    )


def _revenue_cagr_3y(financials: list[FiscalYearFinancials]) -> TracedValue:
    """3-year revenue CAGR; uses the available span if shorter (shown in period)."""
    with_revenue = [y for y in financials if y.revenue is not None]
    warnings: list[str] = []
    value: float | None = None
    period = "N/A"
    formula = "(Revenue_t / Revenue_(t−3))^(1/3) − 1"
    inputs: list[TracedInput] = []

    if not with_revenue:
        warnings.append("Revenue history unavailable")
    else:
        end = with_revenue[-1]
        # Base year: the earliest year with revenue that is at most 3 years back.
        candidates = [
            y
            for y in with_revenue
            if end.fiscal_year - 3 <= y.fiscal_year < end.fiscal_year
        ]
        if not candidates:
            period = _fy(end)
            inputs = [
                TracedInput(field="revenue", value=end.revenue, period=_fy(end))
            ]
            if len(with_revenue) > 1:
                warnings.append(
                    f"No revenue history within 3 years of {_fy(end)}; CAGR undefined"
                )
            else:
                warnings.append(
                    "Only one fiscal year of revenue available; CAGR undefined"
                )
        else:
            base = candidates[0]
            span = end.fiscal_year - base.fiscal_year
            period = f"{_fy(base)}→{_fy(end)}"
            formula = f"(Revenue {_fy(end)} / Revenue {_fy(base)})^(1/{span}) − 1"
            inputs = [
                TracedInput(field="revenue", value=end.revenue, period=_fy(end)),
                TracedInput(field="revenue", value=base.revenue, period=_fy(base)),
            ]
            if span < 3:
                warnings.append(
                    f"Only a {span}-year span available; CAGR computed over {period}"
                )
            assert base.revenue is not None and end.revenue is not None
            if base.revenue <= 0:
                warnings.append(
                    f"Revenue not positive for {_fy(base)}; CAGR undefined"
                )
            else:
                value = (end.revenue / base.revenue) ** (1.0 / span) - 1
    return TracedValue(
        key="revenue_cagr_3y",
        label="Revenue CAGR (3Y)",
        value=value,
        unit="percent",
        period=period,
        formula=formula,
        inputs=inputs,
        warnings=warnings,
    )


def _interest_coverage(latest: FiscalYearFinancials | None) -> TracedValue:
    period = _fy(latest) if latest is not None else "N/A"
    fields = ["ebitda", "interest_expense"]
    warnings = _missing_warnings(latest, fields, period)
    value: float | None = None
    if latest is not None and not warnings:
        assert latest.ebitda is not None and latest.interest_expense is not None
        if latest.interest_expense <= 0:
            warnings.append(
                f"Interest expense not positive for {period}; coverage undefined"
            )
        else:
            value = latest.ebitda / latest.interest_expense
    return TracedValue(
        key="interest_coverage",
        label="Interest Coverage",
        value=value,
        unit="multiple",
        period=period,
        formula="EBITDA / Interest expense",
        inputs=_inputs_from(latest, fields, period),
        warnings=warnings,
    )


def _roic(latest: FiscalYearFinancials | None) -> TracedValue:
    """ROIC = Operating income × (1 − effective tax) / (Debt + Equity − Cash).

    effective_tax = tax_expense / (net_income + tax_expense), clamped to
    [0, 0.5]; falls back to 0.25 with a warning when it cannot be computed.
    """
    period = _fy(latest) if latest is not None else "N/A"
    capital_fields = ["operating_income", "total_debt", "total_equity", "cash_and_equivalents"]
    tax_fields = ["tax_expense", "net_income"]
    warnings = _missing_warnings(latest, capital_fields, period)
    inputs = _inputs_from(latest, capital_fields + tax_fields, period)

    effective_tax = _EFFECTIVE_TAX_FALLBACK
    if latest is not None and latest.tax_expense is not None and latest.net_income is not None:
        pretax = latest.net_income + latest.tax_expense
        if pretax > 0:
            raw = latest.tax_expense / pretax
            effective_tax = min(max(raw, _EFFECTIVE_TAX_MIN), _EFFECTIVE_TAX_MAX)
            if raw != effective_tax:
                warnings.append(
                    f"Effective tax rate {raw:.2f} clamped to {effective_tax:.2f}"
                )
        else:
            warnings.append(
                "Pre-tax income not positive; effective tax rate fallback 0.25 used"
            )
    else:
        warnings.append(
            "Effective tax rate inputs unavailable; fallback 0.25 used"
        )
    inputs.append(TracedInput(field="effective_tax", value=effective_tax, period=period))

    value: float | None = None
    if latest is not None and not _missing_warnings(latest, capital_fields, period):
        assert (
            latest.operating_income is not None
            and latest.total_debt is not None
            and latest.total_equity is not None
            and latest.cash_and_equivalents is not None
        )
        invested_capital = (
            latest.total_debt + latest.total_equity - latest.cash_and_equivalents
        )
        if invested_capital <= 0:
            warnings.append(
                f"Invested capital not positive for {period}; ROIC undefined"
            )
        else:
            value = latest.operating_income * (1 - effective_tax) / invested_capital
    return TracedValue(
        key="roic",
        label="Return on Invested Capital",
        value=value,
        unit="percent",
        period=period,
        formula="Operating income × (1 − effective tax) / (Total debt + Total equity − Cash)",
        inputs=inputs,
        warnings=warnings,
    )


def _build_series(financials: list[FiscalYearFinancials]) -> dict[str, list[SeriesPoint]]:
    """Per-year series (spec §6), skipping years with missing inputs."""

    def div(num: float | None, den: float | None) -> float | None:
        if num is None or den is None or den == 0:
            return None
        return num / den

    extractors: dict[str, Callable[[FiscalYearFinancials], float | None]] = {
        "revenue": lambda y: y.revenue,
        "ebitda": lambda y: y.ebitda,
        "free_cash_flow": lambda y: y.free_cash_flow,
        "total_debt": lambda y: y.total_debt,
        "gross_margin": lambda y: div(y.gross_profit, y.revenue),
        "ebitda_margin": lambda y: div(y.ebitda, y.revenue),
        "net_income_margin": lambda y: div(y.net_income, y.revenue),
        "fcf_margin": lambda y: div(y.free_cash_flow, y.revenue),
        "net_debt_to_ebitda": lambda y: div(
            (y.total_debt - y.cash_and_equivalents)
            if y.total_debt is not None and y.cash_and_equivalents is not None
            else None,
            y.ebitda,
        ),
    }

    series: dict[str, list[SeriesPoint]] = {}
    for name, extract in extractors.items():
        points = [
            SeriesPoint(fiscal_year=y.fiscal_year, value=value)
            for y in financials
            if (value := extract(y)) is not None
        ]
        if points:
            series[name] = points
    return series


def compute_kpis(bundle: CompanyDataBundle) -> KpiResponse:
    """Compute the 14 traceable KPIs and time series for a company bundle.

    Never raises on missing data: each affected KPI gets value None plus a
    warning explaining which input was unavailable.
    """
    financials = sorted(bundle.financials, key=lambda y: y.fiscal_year)
    latest = financials[-1] if financials else None
    prior = None
    if latest is not None:
        for year in financials:
            if year.fiscal_year == latest.fiscal_year - 1:
                prior = year
                break

    kpis: list[TracedValue] = [
        _revenue_growth_yoy(latest, prior),
        _revenue_cagr_3y(financials),
        _simple_ratio(
            latest,
            key="gross_margin",
            label="Gross Margin",
            unit="percent",
            formula="Gross profit / Revenue",
            numerator=lambda y: y.gross_profit,
            numerator_fields=["gross_profit"],
            denominator_field="revenue",
        ),
        _simple_ratio(
            latest,
            key="ebitda_margin",
            label="EBITDA Margin",
            unit="percent",
            formula="EBITDA / Revenue",
            numerator=lambda y: y.ebitda,
            numerator_fields=["ebitda"],
            denominator_field="revenue",
        ),
        _simple_ratio(
            latest,
            key="net_income_margin",
            label="Net Income Margin",
            unit="percent",
            formula="Net income / Revenue",
            numerator=lambda y: y.net_income,
            numerator_fields=["net_income"],
            denominator_field="revenue",
        ),
        _simple_ratio(
            latest,
            key="fcf_margin",
            label="FCF Margin",
            unit="percent",
            formula="Free cash flow / Revenue",
            numerator=lambda y: y.free_cash_flow,
            numerator_fields=["free_cash_flow"],
            denominator_field="revenue",
        ),
        _simple_ratio(
            latest,
            key="fcf_conversion",
            label="FCF Conversion",
            unit="percent",
            formula="Free cash flow / EBITDA",
            numerator=lambda y: y.free_cash_flow,
            numerator_fields=["free_cash_flow"],
            denominator_field="ebitda",
        ),
        _simple_ratio(
            latest,
            key="capex_pct_revenue",
            label="Capex % of Revenue",
            unit="percent",
            formula="Capex / Revenue",
            numerator=lambda y: y.capex,
            numerator_fields=["capex"],
            denominator_field="revenue",
        ),
        _simple_ratio(
            latest,
            key="net_debt_to_ebitda",
            label="Net Debt / EBITDA",
            unit="multiple",
            formula="(Total debt − Cash) / EBITDA",
            numerator=lambda y: (
                y.total_debt - y.cash_and_equivalents
                if y.total_debt is not None and y.cash_and_equivalents is not None
                else None
            ),
            numerator_fields=["total_debt", "cash_and_equivalents"],
            denominator_field="ebitda",
        ),
        _simple_ratio(
            latest,
            key="debt_to_ebitda",
            label="Debt / EBITDA",
            unit="multiple",
            formula="Total debt / EBITDA",
            numerator=lambda y: y.total_debt,
            numerator_fields=["total_debt"],
            denominator_field="ebitda",
        ),
        _interest_coverage(latest),
        _roic(latest),
        _simple_ratio(
            latest,
            key="current_ratio",
            label="Current Ratio",
            unit="ratio",
            formula="Current assets / Current liabilities",
            numerator=lambda y: y.current_assets,
            numerator_fields=["current_assets"],
            denominator_field="current_liabilities",
        ),
        _simple_ratio(
            latest,
            key="nwc_pct_revenue",
            label="NWC % of Revenue",
            unit="percent",
            formula="(Current assets − Current liabilities) / Revenue",
            numerator=lambda y: (
                y.current_assets - y.current_liabilities
                if y.current_assets is not None and y.current_liabilities is not None
                else None
            ),
            numerator_fields=["current_assets", "current_liabilities"],
            denominator_field="revenue",
        ),
    ]

    as_of = (latest.period_end if latest is not None else None) or bundle.fetched_at
    return KpiResponse(
        ticker=bundle.info.ticker,
        as_of=as_of,
        data_source=bundle.data_source,
        kpis=kpis,
        series=_build_series(financials),
    )
