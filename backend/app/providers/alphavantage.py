"""AlphaVantageProvider: market quotes from Alpha Vantage (spec §19.4).

Official JSON endpoints on https://www.alphavantage.co/query:
- function=GLOBAL_QUOTE  -> latest price (the quote)
- function=OVERVIEW      -> SharesOutstanding / MarketCapitalization

This is a key-gated market-data adapter used by CompositeLiveProvider, not a
full DataProvider (it has no fundamentals). All HTTP: 15s timeout, errors
mapped to ProviderError with readable messages (API key is never echoed in
messages). Alpha Vantage signals rate limiting with an HTTP 200 carrying a
{"Note": ...} or {"Information": ...} body — treated as "no quote" (None),
never an error. OVERVIEW is only called after a successful quote, and its
failures degrade silently to a quote-only MarketData.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.providers.exceptions import ProviderConfigError, ProviderError
from app.schemas.company import MarketData

BASE_URL = "https://www.alphavantage.co"
TIMEOUT_SECONDS = 15.0
DATA_SOURCE = "Alpha Vantage"
_THROTTLE_KEYS = ("Note", "Information")


class AlphaVantageProvider:
    name = "alphavantage"

    def __init__(self, api_key: str, *, client: httpx.Client | None = None) -> None:
        if not api_key or not api_key.strip():
            raise ProviderConfigError(
                "ALPHAVANTAGE_API_KEY is required for Alpha Vantage requests."
            )
        self.api_key = api_key.strip()
        self._client = client or httpx.Client(timeout=TIMEOUT_SECONDS)

    def _request_json(self, params: dict[str, str], *, what: str) -> Any:
        params = {**params, "apikey": self.api_key}
        try:
            response = self._client.get(
                f"{BASE_URL}/query", params=params, timeout=TIMEOUT_SECONDS
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status in (401, 403):
                raise ProviderError(
                    f"{what} failed: Alpha Vantage rejected the API key "
                    f"(HTTP {status})."
                ) from None  # severed: chained httpx error embeds the API key URL
            raise ProviderError(
                f"{what} failed: Alpha Vantage returned HTTP {status}."
            ) from None  # severed: chained httpx error embeds the API key URL
        except httpx.HTTPError as exc:
            raise ProviderError(
                f"{what} failed: could not reach Alpha Vantage "
                f"({exc.__class__.__name__})."
            ) from None  # severed: chained httpx error embeds the API key URL
        except ValueError:
            raise ProviderError(
                f"{what} failed: Alpha Vantage returned invalid JSON."
            ) from None  # severed: chained httpx error embeds the API key URL

    def get_quote(self, ticker: str) -> MarketData | None:
        """Latest quote as MarketData, or None when AV has no quote (including
        the rate-limit Note/Information responses)."""
        symbol = ticker.strip().upper()
        data = self._request_json(
            {"function": "GLOBAL_QUOTE", "symbol": symbol},
            what=f"Alpha Vantage quote for {symbol}",
        )
        if not isinstance(data, dict) or _is_throttled(data):
            return None
        quote = data.get("Global Quote")
        if not isinstance(quote, dict) or not quote:
            return None
        price = _to_float(quote.get("05. price"))
        if price is None:
            return None
        as_of = (
            str(quote.get("07. latest trading day") or "").strip()
            or datetime.now(timezone.utc).date().isoformat()
        )

        market_cap, shares = self._overview_details(symbol)
        return MarketData(
            share_price=price,
            market_cap=market_cap,
            shares_outstanding=shares,
            as_of=as_of,
            source=DATA_SOURCE,
            currency="USD",
        )

    def _overview_details(self, symbol: str) -> tuple[float | None, float | None]:
        """(market_cap, shares) from OVERVIEW; failures and throttling are
        silent — a quote without shares still beats no quote at all."""
        try:
            data = self._request_json(
                {"function": "OVERVIEW", "symbol": symbol},
                what=f"Alpha Vantage overview for {symbol}",
            )
        except ProviderError:
            return None, None
        if not isinstance(data, dict) or _is_throttled(data):
            return None, None
        return (
            _to_float(data.get("MarketCapitalization")),
            _to_float(data.get("SharesOutstanding")),
        )


def _is_throttled(data: dict[str, Any]) -> bool:
    """Alpha Vantage rate-limit / advisory body (HTTP 200 with Note text)."""
    return any(key in data for key in _THROTTLE_KEYS)


def _to_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
