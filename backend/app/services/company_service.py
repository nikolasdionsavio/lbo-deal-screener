"""Company data retrieval with §11 cache semantics, and profile building (§12).

Cache policy:
- MockProvider is instant -> skip the DB cache entirely.
- Live providers: serve from `crud.companies.get_cached` (24h TTL) when fresh.
  Cached bundles carry no market data (the §11 companies table has no market
  columns), so on a cache hit we re-fetch the quote via FMP when configured and
  replace the "not cached" warning. On a miss we fetch from the provider and
  write through via the crud upsert.
"""

from sqlalchemy.orm import Session

from app.crud import companies as companies_crud
from app.crud.companies import _MARKET_NOT_CACHED_WARNING as MARKET_NOT_CACHED_WARNING
from app.providers.base import DataProvider
from app.providers.exceptions import ProviderError
from app.providers.mock import MockProvider
from app.schemas.company import CompanyDataBundle, CompanyProfile

CACHE_TTL_HOURS = 24
MARKET_DATA_UNAVAILABLE_WARNING = "Market data unavailable"


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
    """Re-fetch the market quote via FMP for a cache-hit bundle (market=None).

    Successful refresh replaces the cached-bundle warning; failures keep the
    warning so the response still explains the missing quote.
    """
    fmp = getattr(provider, "fmp", None)  # CompositeLiveProvider when configured
    if fmp is None:
        return
    try:
        quote = fmp.get_quote(ticker)
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
    """
    financials = sorted(bundle.financials, key=lambda y: y.fiscal_year)
    latest = financials[-1] if financials else None
    warnings = list(bundle.warnings)

    def _warn(message: str) -> None:
        if message not in warnings:
            warnings.append(message)

    if latest is None:
        _warn("No annual financial data available")

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
    if net_debt is None:
        _warn(
            "Net debt unavailable (total debt or cash missing for the latest "
            "fiscal year)"
        )

    enterprise_value = (
        market_cap + net_debt
        if market_cap is not None and net_debt is not None
        else None
    )
    if enterprise_value is None:
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
        data_source=bundle.data_source,
        data_as_of=data_as_of,
        warnings=warnings,
    )
