"""YahooQuoteProvider: keyless market-data tail for the live chain (spec §19.4).

Quote-only adapter for CompositeLiveProvider, appended unconditionally as the
LAST adapter in the chain: when every key-gated adapter fails or has no quote
(e.g. the FMP free plan answers HTTP 402 for ADRs like BUD), this tail still
returns a price via yfinance's unofficial Yahoo Finance endpoints
(fast_info, then info), with the same GBp -> GBP pence normalization the
YahooProvider applies.

Failure semantics match the other adapters: transport failures raise
ProviderError (recorded as a bundle warning by the chain), everything else —
unknown symbols, empty payloads, even a missing yfinance package — degrades
silently to None. yfinance is imported lazily; tests inject a fake module via
the ``yf_module`` constructor argument so pytest never hits the live network.
"""

from __future__ import annotations

from typing import Any

from app.providers.exceptions import ProviderConfigError
from app.providers.yahoo import YahooProvider
from app.schemas.company import MarketData


class YahooQuoteProvider:
    """Keyless MarketDataAdapter delegating to YahooProvider.refresh_market.

    Reuses the YahooProvider quote path wholesale: fast_info/info access,
    the shared ``_normalize_gbp_pence`` helper, the market-cap cross-check,
    and the "Yahoo Finance (unofficial endpoints, via yfinance)" source label.
    """

    name = "yahoo_quote"

    def __init__(self, *, yf_module: Any | None = None) -> None:
        self._yahoo = YahooProvider(yf_module=yf_module)

    def get_quote(self, ticker: str) -> MarketData | None:
        try:
            return self._yahoo.refresh_market(ticker)
        except ProviderConfigError:
            # yfinance not installed: this adapter is always in the chain, so
            # a missing optional dependency must not poison every bundle.
            return None
