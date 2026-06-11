"""Uniform derivations applied to all providers' financials (spec §4).

Rules (only applied when the target field is missing and all inputs are present):
- gross_profit     = revenue - cost_of_revenue
- ebitda           = operating_income + depreciation_amortization
- free_cash_flow   = operating_cash_flow - capex   (capex stored positive)

Each derived field name is recorded in ``derived_fields``. Fields already stated
by the provider (e.g. complete mock sample files) are left untouched, so the
functions are tolerant of pre-populated data and idempotent. EDGAR data never
carries a reported EBITDA tag, so EBITDA is always recorded as derived there.
"""

from app.schemas.financials import FiscalYearFinancials


def _record(year: FiscalYearFinancials, field: str) -> None:
    if field not in year.derived_fields:
        year.derived_fields.append(field)


def apply_derivations(year: FiscalYearFinancials) -> FiscalYearFinancials:
    """Fill derivable missing fields in place and return the same object."""
    if (
        year.gross_profit is None
        and year.revenue is not None
        and year.cost_of_revenue is not None
    ):
        year.gross_profit = year.revenue - year.cost_of_revenue
        _record(year, "gross_profit")

    if (
        year.ebitda is None
        and year.operating_income is not None
        and year.depreciation_amortization is not None
    ):
        year.ebitda = year.operating_income + year.depreciation_amortization
        _record(year, "ebitda")

    if (
        year.free_cash_flow is None
        and year.operating_cash_flow is not None
        and year.capex is not None
    ):
        year.free_cash_flow = year.operating_cash_flow - year.capex
        _record(year, "free_cash_flow")

    return year


def normalize_financials(
    years: list[FiscalYearFinancials],
) -> list[FiscalYearFinancials]:
    """Apply derivations to every fiscal year in place and return the list."""
    for year in years:
        apply_derivations(year)
    return years
