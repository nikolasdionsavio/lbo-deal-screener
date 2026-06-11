"""CompositeLiveProvider: EDGAR fundamentals + FMP market data (spec §5).

- Fundamentals always come from SEC EDGAR.
- When an FmpProvider is configured, the company profile (sector, industry,
  exchange, description) and market quote are layered on top; FMP failures
  degrade gracefully to warnings instead of failing the whole bundle.
- Search uses FMP when configured (falling back to the EDGAR ticker file on
  FMP errors), else the EDGAR ticker file directly.
"""

from __future__ import annotations

from app.providers.base import DataProvider
from app.providers.edgar import SecEdgarProvider
from app.providers.exceptions import ProviderError
from app.providers.fmp import FmpProvider
from app.schemas.company import CompanyDataBundle, MarketData, SearchResult

COMBINED_DATA_SOURCE = "SEC EDGAR + Financial Modeling Prep"
_MARKET_WARNING_PREFIX = "Market data unavailable"


class CompositeLiveProvider(DataProvider):
    name = "live"

    def __init__(self, edgar: SecEdgarProvider, fmp: FmpProvider | None = None) -> None:
        self.edgar = edgar
        self.fmp = fmp

    def search(self, query: str) -> list[SearchResult]:
        if self.fmp is not None:
            try:
                return self.fmp.search(query)
            except ProviderError:
                # Degrade to the EDGAR ticker file rather than failing search.
                pass
        return self.edgar.search(query)

    def get_company(self, ticker: str) -> CompanyDataBundle:
        bundle = self.edgar.get_company(ticker)

        if self.fmp is None:
            bundle.warnings.append(
                f"{_MARKET_WARNING_PREFIX}: FMP_API_KEY not configured."
            )
            return bundle

        fmp_used = False

        try:
            profile = self.fmp.get_profile(ticker)
        except ProviderError as exc:
            profile = None
            bundle.warnings.append(f"Company profile unavailable from FMP: {exc}")
        if profile is not None:
            fmp_used = True
            info = bundle.info
            info.sector = info.sector or profile.sector
            info.industry = info.industry or profile.industry
            info.exchange = info.exchange or profile.exchange
            info.description = info.description or profile.description

        quote = None
        try:
            quote = self.fmp.get_quote(ticker)
        except ProviderError as exc:
            bundle.warnings.append(f"{_MARKET_WARNING_PREFIX}: {exc}")
        if quote is not None:
            fmp_used = True
            bundle.market = quote
        elif not any(w.startswith(_MARKET_WARNING_PREFIX) for w in bundle.warnings):
            bundle.warnings.append(
                f"{_MARKET_WARNING_PREFIX}: FMP returned no quote for this ticker."
            )

        if fmp_used:
            bundle.data_source = COMBINED_DATA_SOURCE
        return bundle

    def refresh_market(self, ticker: str) -> MarketData | None:
        """§11 cache-hit quote refresh via FMP (None when FMP not configured)."""
        if self.fmp is None:
            return None
        return self.fmp.get_quote(ticker)
