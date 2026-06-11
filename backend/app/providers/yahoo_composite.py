"""YahooCompositeProvider: Yahoo market/profile + EDGAR US fundamentals (spec §5).

Mirrors CompositeLiveProvider for the Yahoo-first world:
- Non-US tickers (exchange suffix, e.g. "TSCO.L", "ASML.AS") or no EDGAR
  configuration -> YahooProvider entirely.
- US-style tickers (no "." suffix) with SEC_EDGAR_USER_AGENT set -> official
  SEC EDGAR fundamentals, Yahoo market data and profile;
  data_source "SEC EDGAR + Yahoo Finance". EDGAR failures degrade to Yahoo
  fundamentals with a warning instead of failing the bundle.
- Search and the §11 cache-hit market refresh always go through Yahoo.
"""

from __future__ import annotations

from app.providers.base import DataProvider
from app.providers.edgar import SecEdgarProvider
from app.providers.exceptions import ProviderError
from app.providers.yahoo import YahooProvider
from app.schemas.company import CompanyDataBundle, MarketData, SearchResult

COMBINED_DATA_SOURCE = "SEC EDGAR + Yahoo Finance"
# SEC EDGAR USD facts are served when EDGAR fundamentals are used, so the
# reporting currency of the merged bundle is USD by construction.
_EDGAR_REPORTING_CURRENCY = "USD"


def _is_us_style(ticker: str) -> bool:
    """US-style tickers carry no exchange suffix (no '.' in the symbol)."""
    return "." not in ticker.strip()


class YahooCompositeProvider(DataProvider):
    name = "yahoo"

    def __init__(
        self, yahoo: YahooProvider, edgar: SecEdgarProvider | None = None
    ) -> None:
        self.yahoo = yahoo
        self.edgar = edgar

    def search(self, query: str) -> list[SearchResult]:
        return self.yahoo.search(query)

    def get_company(self, ticker: str) -> CompanyDataBundle:
        symbol = ticker.strip().upper()
        bundle = self.yahoo.get_company(symbol)
        if self.edgar is None or not _is_us_style(symbol):
            return bundle

        try:
            edgar_bundle = self.edgar.get_company(symbol)
        except ProviderError as exc:  # includes CompanyNotFoundError
            bundle.warnings.append(
                f"SEC EDGAR fundamentals unavailable ({exc}); using Yahoo "
                "Finance fundamentals instead."
            )
            return bundle

        # Official EDGAR fundamentals replace Yahoo's; Yahoo keeps market data
        # and the profile (sector/industry/exchange/description).
        bundle.financials = edgar_bundle.financials
        bundle.currency = _EDGAR_REPORTING_CURRENCY
        bundle.info.cik = bundle.info.cik or edgar_bundle.info.cik
        bundle.data_source = COMBINED_DATA_SOURCE
        for warning in edgar_bundle.warnings:
            if warning not in bundle.warnings:
                bundle.warnings.append(warning)
        return bundle

    def refresh_market(self, ticker: str) -> MarketData | None:
        """§11 cache-hit quote refresh via Yahoo fast_info/info."""
        return self.yahoo.refresh_market(ticker)
