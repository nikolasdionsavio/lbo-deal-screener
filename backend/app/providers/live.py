"""CompositeLiveProvider: EDGAR fundamentals + chained market data (spec §5, §19.4).

- Fundamentals always come from SEC EDGAR.
- Market data is an ordered chain of configured quote adapters
  [FMP, Polygon, Alpha Vantage, Tiingo]: the first non-None quote wins (its
  MarketData.source identifies the adapter); an adapter ProviderError becomes
  a bundle warning and the chain moves on. `refresh_market` walks the same
  chain.
- Company profile enrichment (sector, industry, exchange, description) is
  FMP-first; when the FMP profile is unavailable (quota/missing key/error)
  the gaps are filled best-effort from yfinance ``Ticker.info`` (§19.8),
  with the source noted in a warning. FMP failures degrade gracefully to
  warnings instead of failing the whole bundle.
- Search uses FMP when configured (falling back to the EDGAR ticker file on
  FMP errors), else the EDGAR ticker file directly.
"""

from __future__ import annotations

from typing import Any, Protocol, Sequence

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
PROFILE_FALLBACK_WARNING = (
    "Company profile (sector/industry/description) from Yahoo Finance "
    "(unofficial endpoints, via yfinance); FMP profile unavailable."
)


def _yfinance_profile_info(ticker: str) -> dict[str, Any] | None:
    """Best-effort ``yfinance.Ticker(ticker).info`` (§19.8 profile fallback).

    Lazy import keeps the dependency optional; any failure (missing package,
    network, unofficial-endpoint breakage) returns None — the fallback must
    never break a bundle. Module-level so tests can stub it out.
    """
    try:
        import yfinance  # lazy: optional dependency
    except ImportError:
        return None
    try:
        info = yfinance.Ticker(ticker).info
    except Exception:  # unofficial endpoints fail in many shapes
        return None
    return info if isinstance(info, dict) else None


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

    def get_company(self, ticker: str, max_years: int = 5) -> CompanyDataBundle:
        # max_years (§19.7) forwards to EDGAR's year-selection cap; the
        # 5-year default keeps every regular bundle unchanged, the statements
        # endpoint asks for up to 15.
        bundle = self.edgar.get_company(ticker, max_years=max_years)

        if not self.market_adapters and self.fmp is None:
            bundle.warnings.append(_NO_ADAPTER_WARNING)
            self._fill_profile_from_yfinance(ticker, bundle)  # §19.8: no FMP key
            return bundle

        # Profile enrichment is FMP-first (the other adapters are quote-only).
        fmp_used = False
        profile = None
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
        if profile is None:
            # §19.8: FMP profile unavailable (quota/missing key/error) —
            # fill the gaps from yfinance Ticker.info, best-effort.
            self._fill_profile_from_yfinance(ticker, bundle)

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
    # Profile fallback (§19.8)
    # ------------------------------------------------------------------

    @staticmethod
    def _fill_profile_from_yfinance(ticker: str, bundle: CompanyDataBundle) -> bool:
        """Fill missing sector/industry/description (and exchange when absent)
        from yfinance ``Ticker.info``. Returns True when anything was filled;
        the source is noted with PROFILE_FALLBACK_WARNING."""
        info_obj = bundle.info
        if (
            info_obj.sector
            and info_obj.industry
            and info_obj.description
            and info_obj.exchange
        ):
            return False  # nothing to fill
        data = _yfinance_profile_info(ticker)
        if not data:
            return False
        filled = False
        if not info_obj.sector and data.get("sector"):
            info_obj.sector = str(data["sector"])
            filled = True
        if not info_obj.industry and data.get("industry"):
            info_obj.industry = str(data["industry"])
            filled = True
        if not info_obj.description and data.get("longBusinessSummary"):
            info_obj.description = str(data["longBusinessSummary"])
            filled = True
        exchange = data.get("fullExchangeName") or data.get("exchange")
        if not info_obj.exchange and exchange:
            info_obj.exchange = str(exchange)
            filled = True
        if filled and PROFILE_FALLBACK_WARNING not in bundle.warnings:
            bundle.warnings.append(PROFILE_FALLBACK_WARNING)
        return filled

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
