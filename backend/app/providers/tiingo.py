"""TiingoProvider: market quotes from Tiingo (spec §19.4).

Official JSON endpoints on https://api.tiingo.com (Authorization: Token header):
- GET /tiingo/daily/{t}         -> ticker metadata (validates the symbol)
- GET /tiingo/daily/{t}/prices  -> latest end-of-day bar (the quote)

This is a key-gated market-data adapter used by CompositeLiveProvider, not a
full DataProvider (it has no fundamentals). The daily endpoints carry no
market cap or share count, so MarketData is price-only. All HTTP: 15s
timeout, errors mapped to ProviderError with readable messages (API key is
never echoed in messages). HTTP 404 means an unknown ticker -> None.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.providers.exceptions import ProviderConfigError, ProviderError
from app.schemas.company import MarketData

BASE_URL = "https://api.tiingo.com"
TIMEOUT_SECONDS = 15.0
DATA_SOURCE = "Tiingo"


class TiingoProvider:
    name = "tiingo"

    def __init__(self, api_key: str, *, client: httpx.Client | None = None) -> None:
        if not api_key or not api_key.strip():
            raise ProviderConfigError(
                "TIINGO_API_KEY is required for Tiingo requests."
            )
        self.api_key = api_key.strip()
        self._client = client or httpx.Client(timeout=TIMEOUT_SECONDS)

    def _request_json(self, path: str, *, what: str) -> Any:
        """JSON payload, or None on HTTP 404 (unknown ticker)."""
        headers = {"Authorization": f"Token {self.api_key}"}
        try:
            response = self._client.get(
                f"{BASE_URL}{path}", headers=headers, timeout=TIMEOUT_SECONDS
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status in (401, 403):
                raise ProviderError(
                    f"{what} failed: Tiingo rejected the API key "
                    f"(HTTP {status})."
                ) from None  # severed: chained httpx error embeds the API key
            raise ProviderError(
                f"{what} failed: Tiingo returned HTTP {status}."
            ) from None  # severed: chained httpx error embeds the API key
        except httpx.HTTPError as exc:
            raise ProviderError(
                f"{what} failed: could not reach Tiingo "
                f"({exc.__class__.__name__})."
            ) from None  # severed: chained httpx error embeds the API key
        except ValueError:
            raise ProviderError(
                f"{what} failed: Tiingo returned invalid JSON."
            ) from None  # severed: chained httpx error embeds the API key

    def get_quote(self, ticker: str) -> MarketData | None:
        """Latest end-of-day close as MarketData, or None when Tiingo does not
        know the ticker or has no price bars for it."""
        symbol = ticker.strip().lower()
        if not symbol:
            return None

        meta = self._request_json(
            f"/tiingo/daily/{symbol}", what=f"Tiingo metadata for {symbol.upper()}"
        )
        if not isinstance(meta, dict) or not meta:
            return None

        prices = self._request_json(
            f"/tiingo/daily/{symbol}/prices",
            what=f"Tiingo prices for {symbol.upper()}",
        )
        if not isinstance(prices, list) or not prices:
            return None
        bar = prices[-1]
        if not isinstance(bar, dict):
            return None
        close = _to_float(bar.get("close"))
        if close is None:
            return None

        bar_date = str(bar.get("date") or "").strip()
        as_of = (
            bar_date[:10]
            if len(bar_date) >= 10
            else datetime.now(timezone.utc).date().isoformat()
        )
        return MarketData(
            share_price=close,
            market_cap=None,
            shares_outstanding=None,
            as_of=as_of,
            source=DATA_SOURCE,
            currency="USD",
        )


def _to_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
