"""DataProvider interface (spec §5)."""

from abc import ABC, abstractmethod

from app.schemas.company import CompanyDataBundle, MarketData, SearchResult


class DataProvider(ABC):
    """Abstract data provider: ticker/name search and company bundle fetch."""

    name: str = "base"

    @abstractmethod
    def search(self, query: str) -> list[SearchResult]:
        """Return companies matching a ticker or name query."""

    @abstractmethod
    def get_company(self, ticker: str) -> CompanyDataBundle:
        """Return the full data bundle for a ticker.

        Raises CompanyNotFoundError for unknown tickers and ProviderError for
        upstream failures.
        """

    def refresh_market(self, ticker: str) -> MarketData | None:
        """Optional light-weight quote refresh used on §11 cache hits.

        Cached bundles carry no market data, so the services layer asks the
        provider for a fresh quote when serving from cache. The default is a
        no-op (None); market-capable providers override it.
        """
        return None
