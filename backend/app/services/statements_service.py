"""Financial statements service (spec §19.7): full history, regrouped per year.

Providers whose ``get_company`` accepts the ``max_years`` keyword (the
EDGAR-backed paths) are asked for up to 15 fiscal years directly — a live
fetch on every call. The §11 24h bundle cache is deliberately untouched: its
5-year shape feeds every other endpoint, and caching a second shape is not
worth the complexity. Providers without the keyword (MockProvider) duck-type
out via TypeError and fall back to the regular bundle's financials regrouped
(mock = its 5 years).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.providers.base import DataProvider
from app.schemas.company import CompanyDataBundle
from app.schemas.financials import FiscalYearFinancials
from app.schemas.statements import (
    StatementBalance,
    StatementCashFlow,
    StatementIncome,
    StatementsResponse,
    StatementYear,
)
from app.services import company_service

STATEMENTS_MAX_YEARS = 15


def get_statements(
    ticker: str, db: Session, provider: DataProvider
) -> StatementsResponse:
    """Build the §19.7 statements response (years DESCENDING fiscal_year)."""
    ticker = ticker.strip().upper()
    try:
        bundle: CompanyDataBundle = provider.get_company(
            ticker, max_years=STATEMENTS_MAX_YEARS
        )
    except TypeError:
        # Provider lacks the max_years keyword: regroup the regular
        # (cache-honoring) bundle's financials instead.
        bundle = company_service.get_bundle(ticker, db, provider)

    years = sorted(bundle.financials, key=lambda y: y.fiscal_year, reverse=True)
    return StatementsResponse(
        ticker=bundle.info.ticker.upper(),
        currency=bundle.currency,
        data_source=bundle.data_source,
        fetched_at=bundle.fetched_at,
        years=[_statement_year(year) for year in years],
        warnings=bundle.warnings,
    )


def _statement_year(year: FiscalYearFinancials) -> StatementYear:
    """Regroup one FiscalYearFinancials into the three filing statements."""
    return StatementYear(
        fiscal_year=year.fiscal_year,
        period_end=year.period_end,
        derived_fields=list(year.derived_fields),
        income_statement=StatementIncome(
            revenue=year.revenue,
            cost_of_revenue=year.cost_of_revenue,
            gross_profit=year.gross_profit,
            research_development=year.research_development,
            selling_general_admin=year.selling_general_admin,
            operating_income=year.operating_income,
            depreciation_amortization=year.depreciation_amortization,
            ebitda=year.ebitda,
            interest_expense=year.interest_expense,
            pretax_income=year.pretax_income,
            tax_expense=year.tax_expense,
            net_income=year.net_income,
            eps_basic=year.eps_basic,
            eps_diluted=year.eps_diluted,
            shares_diluted=year.shares_diluted,
        ),
        balance_sheet=StatementBalance(
            cash_and_equivalents=year.cash_and_equivalents,
            receivables=year.receivables,
            inventory=year.inventory,
            current_assets=year.current_assets,
            ppe_net=year.ppe_net,
            goodwill=year.goodwill,
            intangible_assets=year.intangible_assets,
            total_assets=year.total_assets,
            accounts_payable=year.accounts_payable,
            current_liabilities=year.current_liabilities,
            long_term_debt=year.long_term_debt,
            total_debt=year.total_debt,
            total_liabilities=year.total_liabilities,
            retained_earnings=year.retained_earnings,
            total_equity=year.total_equity,
        ),
        cash_flow=StatementCashFlow(
            stock_based_compensation=year.stock_based_compensation,
            operating_cash_flow=year.operating_cash_flow,
            capex=year.capex,
            free_cash_flow=year.free_cash_flow,
            investing_cash_flow=year.investing_cash_flow,
            dividends_paid=year.dividends_paid,
            share_buybacks=year.share_buybacks,
            financing_cash_flow=year.financing_cash_flow,
        ),
    )
