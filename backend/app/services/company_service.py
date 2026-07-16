"""Company data retrieval with §11 cache semantics, and profile building (§12).

Cache policy:
- MockProvider is instant -> skip the DB cache entirely.
- Live providers: serve from `crud.companies.get_cached` (24h TTL) when fresh.
  Cached bundles carry no market data (the §11 companies table has no market
  columns), so on a cache hit we ask the provider for a fresh quote via its
  optional `refresh_market` hook (FMP for CompositeLiveProvider, Yahoo
  fast_info/info for YahooCompositeProvider) and replace the "not cached"
  warning. On a miss we fetch from the provider and write through via the
  crud upsert.
"""

from sqlalchemy.orm import Session

from app.crud import companies as companies_crud
from app.crud.companies import MARKET_NOT_CACHED_WARNING
from app.normalization import currency_mismatch_warning, reporting_currency
from app.providers.base import DataProvider
from app.providers.exceptions import ProviderError
from app.providers.mock import MockProvider
from app.schemas.company import CompanyDataBundle, CompanyProfile

CACHE_TTL_HOURS = 24
MARKET_DATA_UNAVAILABLE_WARNING = "Market data unavailable"
# Shown when a filer has no annual-report financials at all (e.g. a company that
# has only just IPO'd, like SK hynix / SKHY in Jul 2026). Computed here from the
# persisted financials rather than the provider warnings, which the 24h company
# cache does not round-trip — so it survives a cache hit and reads as a designed
# empty state instead of a bare blank page.
NO_ANNUAL_REPORT_WARNING = (
    "No annual report (10-K or 20-F) is on file with the SEC yet, so financial "
    "statements are not available. A newly listed company appears here in full "
    "once it files its first annual report."
)


def get_bundle(
    ticker: str, db: Session, provider: DataProvider
) -> CompanyDataBundle:
    """Return the company bundle, honoring the §11 24h write-through cache.

    Raises CompanyNotFoundError / ProviderError from the provider (routes map
    them to 404 / 502).
    """
    ticker = ticker.strip().upper()
    if isinstance(provider, MockProvider):
        return provider.get_company(ticker)  # mock is instant; never cache

    cached = companies_crud.get_cached(db, ticker, CACHE_TTL_HOURS)
    if cached is not None:
        _refresh_market_data(cached, ticker, provider)
        return cached

    bundle = provider.get_company(ticker)
    companies_crud.upsert_company(db, bundle)
    return bundle


def _refresh_market_data(
    bundle: CompanyDataBundle, ticker: str, provider: DataProvider
) -> None:
    """Refresh the market quote for a cache-hit bundle (market=None).

    Uses the provider's optional `refresh_market` hook (spec §5). Successful
    refresh replaces the cached-bundle warning; failures keep the warning so
    the response still explains the missing quote.
    """
    try:
        quote = provider.refresh_market(ticker)
    except ProviderError:
        return
    if quote is None:
        return
    bundle.market = quote
    bundle.warnings = [
        w for w in bundle.warnings if w != MARKET_NOT_CACHED_WARNING
    ]


def build_profile(bundle: CompanyDataBundle) -> CompanyProfile:
    """Build the §12 CompanyProfile with headline aggregates (spec §4).

    EV = market_cap + net_debt; net_debt = total_debt − cash (latest FY);
    market_cap derived from share price × shares when the quote lacks it.
    None-tolerant: missing inputs yield None fields plus warnings.

    Currency contract (§4): profile.currency is the reporting currency
    (bundle.currency, default USD). When the normalized quote currency
    differs, EV mixes currencies and is suppressed with the spec warning;
    market_cap is still shown but flagged by the same warning.
    """
    financials = sorted(bundle.financials, key=lambda y: y.fiscal_year)
    latest = financials[-1] if financials else None
    warnings = list(bundle.warnings)

    def _warn(message: str) -> None:
        if message not in warnings:
            warnings.append(message)

    no_financials = latest is None
    if no_financials:
        _warn(NO_ANNUAL_REPORT_WARNING)

    market = bundle.market
    share_price = market.share_price if market is not None else None
    shares: float | None = None
    if market is not None and market.shares_outstanding:
        shares = market.shares_outstanding
    elif latest is not None and latest.shares_outstanding:
        shares = latest.shares_outstanding

    market_cap = market.market_cap if market is not None else None
    if market_cap is None and share_price is not None and shares:
        market_cap = share_price * shares
        _warn("Market cap derived as share price × shares outstanding")
    if market_cap is None:
        _warn(MARKET_DATA_UNAVAILABLE_WARNING)

    cash = latest.cash_and_equivalents if latest is not None else None
    total_debt = latest.total_debt if latest is not None else None
    net_debt = (
        total_debt - cash if total_debt is not None and cash is not None else None
    )
    if net_debt is None and not no_financials:
        # When there are no financials at all the lead warning already covers it;
        # only flag net debt specifically when we have statements but this line
        # is missing.
        _warn(
            "Net debt unavailable (total debt or cash missing for the latest "
            "fiscal year)"
        )

    mismatch_warning = currency_mismatch_warning(bundle)
    if mismatch_warning is not None:
        enterprise_value = None  # market cap and net debt are in different currencies
        _warn(mismatch_warning)
    else:
        enterprise_value = (
            market_cap + net_debt
            if market_cap is not None and net_debt is not None
            else None
        )
        if enterprise_value is None and not no_financials:
            _warn("Enterprise value unavailable (market cap or net debt missing)")

    data_as_of = (
        market.as_of if market is not None and market.as_of else bundle.fetched_at
    )

    return CompanyProfile(
        ticker=bundle.info.ticker.upper(),
        name=bundle.info.name,
        sector=bundle.info.sector,
        industry=bundle.info.industry,
        exchange=bundle.info.exchange,
        description=bundle.info.description,
        share_price=share_price,
        market_cap=market_cap,
        enterprise_value=enterprise_value,
        shares_outstanding=shares,
        latest_fiscal_year=latest.fiscal_year if latest is not None else None,
        revenue=latest.revenue if latest is not None else None,
        ebitda=latest.ebitda if latest is not None else None,
        net_income=latest.net_income if latest is not None else None,
        free_cash_flow=latest.free_cash_flow if latest is not None else None,
        cash=cash,
        total_debt=total_debt,
        net_debt=net_debt,
        currency=reporting_currency(bundle),
        data_source=bundle.data_source,
        data_as_of=data_as_of,
        warnings=warnings,
    )
