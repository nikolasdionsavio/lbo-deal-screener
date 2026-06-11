"""PolygonProvider: market quotes from Polygon.io (spec §19.4).

Official JSON endpoints on https://api.polygon.io:
- GET /v2/aggs/ticker/{T}/prev          -> previous-day close (the quote)
- GET /v3/reference/tickers/{T}         -> market_cap / weighted shares

This is a key-gated market-data adapter used by CompositeLiveProvider, not a
full DataProvider (it has no fundamentals). All HTTP: 15s timeout, errors
mapped to ProviderError with readable messages (API key is never echoed in
messages). Reference-endpoint failures degrade silently to a quote-only
MarketData.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.providers.exceptions import ProviderConfigError, ProviderError
from app.schemas.company import MarketData

BASE_URL = "https://api.polygon.io"
TIMEOUT_SECONDS = 15.0
DATA_SOURCE = "Polygon.io"


class PolygonProvider:
    name = "polygon"

    def __init__(self, api_key: str, *, client: httpx.Client | None = None) -> None:
        if not api_key or not api_key.strip():
            raise ProviderConfigError(
                "POLYGON_API_KEY is required for Polygon.io requests."
            )
        self.api_key = api_key.strip()
        self._client = client or httpx.Client(timeout=TIMEOUT_SECONDS)

    def _request_json(self, path: str, *, what: str) -> Any:
        params = {"apiKey": self.api_key}
        try:
            response = self._client.get(
                f"{BASE_URL}{path}", params=params, timeout=TIMEOUT_SECONDS
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status in (401, 403):
                raise ProviderError(
                    f"{what} failed: Polygon.io rejected the API key "
                    f"(HTTP {status})."
                ) from None  # severed: chained httpx error embeds the API key URL
            raise ProviderError(
                f"{what} failed: Polygon.io returned HTTP {status}."
            ) from None  # severed: chained httpx error embeds the API key URL
        except httpx.HTTPError as exc:
            raise ProviderError(
                f"{what} failed: could not reach Polygon.io "
                f"({exc.__class__.__name__})."
            ) from None  # severed: chained httpx error embeds the API key URL
        except ValueError:
            raise ProviderError(
                f"{what} failed: Polygon.io returned invalid JSON."
            ) from None  # severed: chained httpx error embeds the API key URL

    def get_quote(self, ticker: str) -> MarketData | None:
        """Previous-day close as MarketData, or None when Polygon has no bar."""
        symbol = ticker.strip().upper()
        data = self._request_json(
            f"/v2/aggs/ticker/{symbol}/prev", what=f"Polygon quote for {symbol}"
        )
        if not isinstance(data, dict):
            return None
        results = data.get("results")
        if not isinstance(results, list) or not results:
            return None
        bar = results[0]
        if not isinstance(bar, dict):
            return None
        close = _to_float(bar.get("c"))
        if close is None:
            return None

        timestamp_ms = _to_float(bar.get("t"))
        if timestamp_ms is not None:
            as_of = (
                datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc)
                .date()
                .isoformat()
            )
        else:
            as_of = datetime.now(timezone.utc).date().isoformat()

        market_cap, shares = self._reference_details(symbol)
        return MarketData(
            share_price=close,
            market_cap=market_cap,
            shares_outstanding=shares,
            as_of=as_of,
            source=DATA_SOURCE,
            currency="USD",
        )

    def _reference_details(self, symbol: str) -> tuple[float | None, float | None]:
        """(market_cap, shares) from the reference endpoint; failures are
        silent — a quote without shares still beats no quote at all."""
        try:
            data = self._request_json(
                f"/v3/reference/tickers/{symbol}",
                what=f"Polygon reference data for {symbol}",
            )
        except ProviderError:
            return None, None
        if not isinstance(data, dict):
            return None, None
        record = data.get("results")
        if not isinstance(record, dict):
            return None, None
        return (
            _to_float(record.get("market_cap")),
            _to_float(record.get("weighted_shares_outstanding")),
        )


def _to_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
