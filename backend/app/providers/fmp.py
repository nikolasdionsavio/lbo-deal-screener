"""FmpProvider: market data, company profile and search from FMP (spec §5).

Official JSON endpoints on https://financialmodelingprep.com (the "stable" API;
the /api/v3 endpoints are legacy-only for accounts created before 2025-08-31):
- GET /stable/profile?symbol=     -> company profile (sector, industry, ...)
- GET /stable/quote?symbol=       -> share price / market cap / shares
- GET /stable/search-name?query=  -> ticker search (post-filtered to US venues)

This is a market-data component used by CompositeLiveProvider, not a full
DataProvider (it has no fundamentals). All HTTP: 15s timeout, errors mapped to
ProviderError with readable messages (API key is never echoed in messages).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.providers.exceptions import ProviderConfigError, ProviderError
from app.schemas.company import CompanyInfo, MarketData, SearchResult

BASE_URL = "https://financialmodelingprep.com"
TIMEOUT_SECONDS = 15.0
US_EXCHANGES = {"NASDAQ", "NYSE", "AMEX"}
DATA_SOURCE = "Financial Modeling Prep"


class FmpProvider:
    name = "fmp"

    def __init__(self, api_key: str, *, client: httpx.Client | None = None) -> None:
        if not api_key or not api_key.strip():
            raise ProviderConfigError(
                "FMP_API_KEY is required for Financial Modeling Prep requests."
            )
        self.api_key = api_key.strip()
        self._client = client or httpx.Client(timeout=TIMEOUT_SECONDS)

    def _request_json(self, path: str, params: dict[str, str], *, what: str) -> Any:
        params = {**params, "apikey": self.api_key}
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
                    f"{what} failed: Financial Modeling Prep rejected the API key "
                    f"(HTTP {status})."
                ) from None  # severed: chained httpx error embeds the API key URL
            raise ProviderError(
                f"{what} failed: Financial Modeling Prep returned HTTP {status}."
            ) from None  # severed: chained httpx error embeds the API key URL
        except httpx.HTTPError as exc:
            raise ProviderError(
                f"{what} failed: could not reach Financial Modeling Prep "
                f"({exc.__class__.__name__})."
            ) from None  # severed: chained httpx error embeds the API key URL
        except ValueError as exc:
            raise ProviderError(
                f"{what} failed: Financial Modeling Prep returned invalid JSON."
            ) from None  # severed: chained httpx error embeds the API key URL

    def get_profile(self, ticker: str) -> CompanyInfo | None:
        """Company profile, or None when FMP has no record for the ticker."""
        symbol = ticker.strip().upper()
        data = self._request_json(
            "/stable/profile", {"symbol": symbol}, what=f"FMP profile for {symbol}"
        )
        if not isinstance(data, list) or not data:
            return None
        record = data[0]
        return CompanyInfo(
            ticker=str(record.get("symbol") or symbol),
            name=str(record.get("companyName") or symbol),
            sector=record.get("sector") or None,
            industry=record.get("industry") or None,
            exchange=record.get("exchange") or record.get("exchangeShortName") or None,
            description=record.get("description") or None,
            cik=record.get("cik") or None,
        )

    def get_quote(self, ticker: str) -> MarketData | None:
        """Latest quote as MarketData, or None when FMP has no quote."""
        symbol = ticker.strip().upper()
        data = self._request_json(
            "/stable/quote", {"symbol": symbol}, what=f"FMP quote for {symbol}"
        )
        if not isinstance(data, list) or not data:
            return None
        record = data[0]
        timestamp = record.get("timestamp")
        if timestamp:
            as_of = datetime.fromtimestamp(float(timestamp), tz=timezone.utc).date().isoformat()
        else:
            as_of = datetime.now(timezone.utc).date().isoformat()
        return MarketData(
            share_price=_to_float(record.get("price")),
            market_cap=_to_float(record.get("marketCap")),
            shares_outstanding=_to_float(record.get("sharesOutstanding")),
            as_of=as_of,
            source=DATA_SOURCE,
        )

    def search(self, query: str) -> list[SearchResult]:
        q = query.strip()
        if not q:
            return []
        # Query symbols and names separately — the stable API split them, so a
        # ticker like "nvda" never matches search-name. Symbol hits rank first.
        records: list[dict[str, Any]] = []
        for path in ("/stable/search-symbol", "/stable/search-name"):
            data = self._request_json(
                path, {"query": q, "limit": "20"}, what=f"FMP search for '{q}'"
            )
            if isinstance(data, list):
                records.extend(r for r in data if isinstance(r, dict))

        results: list[SearchResult] = []
        seen: set[str] = set()
        for record in records:
            symbol = record.get("symbol")
            # The stable search has no server-side venue filter; keep US listings
            # only (product scope) and drop suffixed cross-listings like HD.SW.
            if not symbol or symbol in seen or record.get("exchange") not in US_EXCHANGES:
                continue
            seen.add(symbol)
            results.append(
                SearchResult(
                    ticker=str(symbol),
                    name=str(record.get("name") or symbol),
                    exchange=record.get("exchangeFullName")
                    or record.get("exchange")
                    or None,
                    source=self.name,
                )
            )
            if len(results) >= 8:
                break
        return results


def _to_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
