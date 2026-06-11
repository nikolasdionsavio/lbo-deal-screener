"""CompositeLiveProvider: EDGAR fundamentals + chained market data (spec §5, §19.4).

- Fundamentals always come from SEC EDGAR.
- Market data is an ordered chain of configured quote adapters
  [FMP, Polygon, Alpha Vantage, Tiingo]: the first non-None quote wins (its
  MarketData.source identifies the adapter); an adapter ProviderError becomes
  a bundle warning and the chain moves on. `refresh_market` walks the same
  chain.
- Company profile enrichment (sector, industry, exchange, description) stays
  FMP-only; FMP failures degrade gracefully to warnings instead of failing
  the whole bundle.
- Search uses FMP when configured (falling back to the EDGAR ticker file on
  FMP errors), else the EDGAR ticker file directly.
"""

from __future__ import annotations

from typing import Protocol, Sequence

from app.providers.base import DataProvider
from app.providers.edgar import SecEdgarProvider
from app.providers.exceptions import ProviderError
from app.providers.fmp import DATA_SOURCE as FMP_DATA_SOURCE
from app.providers.fmp import FmpProvider
from app.schemas.company import CompanyDataBundle, MarketData, SearchResult

COMBINED_DATA_SOURCE = "SEC EDGAR + Financial Modeling Prep"
_MARKET_WARNING_PREFIX = "Market data unavailable"
_NO_ADAPTER_WARNING = (
    f"{_MARKET_WARNING_PREFIX}: no market-data API key configured "
    "(set FMP_API_KEY, POLYGON_API_KEY, ALPHAVANTAGE_API_KEY or TIINGO_API_KEY)."
)


class MarketDataAdapter(Protocol):
    """A key-gated quote source pluggable into the market-data chain."""

    name: str

    def get_quote(self, ticker: str) -> MarketData | None: ...


class CompositeLiveProvider(DataProvider):
    name = "live"

    def __init__(
        self,
        edgar: SecEdgarProvider,
        fmp: FmpProvider | None = None,
        market_adapters: Sequence[MarketDataAdapter] | None = None,
    ) -> None:
        self.edgar = edgar
        self.fmp = fmp
        # Ordered quote chain: FMP first (when configured), then the extra
        # adapters in the order given (factory order: Polygon, AV, Tiingo).
        self.market_adapters: list[MarketDataAdapter] = (
            [fmp] if fmp is not None else []
        ) + list(market_adapters or [])

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

        if not self.market_adapters and self.fmp is None:
            bundle.warnings.append(_NO_ADAPTER_WARNING)
            return bundle

        # Profile enrichment is FMP-only (the other adapters are quote-only).
        fmp_used = False
        if self.fmp is not None:
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

        quote = self._first_quote(ticker, bundle.warnings)
        if quote is not None:
            bundle.market = quote
            if quote.source == FMP_DATA_SOURCE:
                fmp_used = True
        elif not any(w.startswith(_MARKET_WARNING_PREFIX) for w in bundle.warnings):
            bundle.warnings.append(
                f"{_MARKET_WARNING_PREFIX}: no configured provider returned a "
                "quote for this ticker."
            )

        bundle.data_source = self._combined_source(fmp_used, quote)
        return bundle

    def refresh_market(self, ticker: str) -> MarketData | None:
        """§11 cache-hit quote refresh: first non-None quote in the chain
        (None when no adapter is configured or none has a quote)."""
        return self._first_quote(ticker, warnings=None)

    # ------------------------------------------------------------------
    # Market-data chain
    # ------------------------------------------------------------------

    def _first_quote(
        self, ticker: str, warnings: list[str] | None
    ) -> MarketData | None:
        """Walk the adapter chain; first non-None quote wins. An adapter
        ProviderError is recorded as a warning (when collecting) and the
        chain moves on to the next adapter."""
        for adapter in self.market_adapters:
            try:
                quote = adapter.get_quote(ticker)
            except ProviderError as exc:
                if warnings is not None:
                    warnings.append(f"{_MARKET_WARNING_PREFIX}: {exc}")
                continue
            if quote is not None:
                return quote
        return None

    @staticmethod
    def _combined_source(fmp_used: bool, quote: MarketData | None) -> str:
        parts = ["SEC EDGAR"]
        if fmp_used:
            parts.append(FMP_DATA_SOURCE)
        if quote is not None and quote.source not in parts:
            parts.append(quote.source)
        return " + ".join(parts)
