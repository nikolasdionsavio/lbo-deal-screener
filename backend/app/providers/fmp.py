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

import time
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
        # FMP free-plan rate limits surface as transient 429s; retry briefly
        # (2 retries, 2s/4s backoff) before failing — mirrors EDGAR (§19.7).
        attempts = 3
        for attempt in range(1, attempts + 1):
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
                if status == 429 and attempt < attempts:
                    time.sleep(attempt * 2.0)
                    continue
                if status == 429:
                    raise ProviderError(
                        f"{what} failed: Financial Modeling Prep is rate limiting "
                        "requests (HTTP 429). Try again in a minute."
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
        raise ProviderError(
            f"{what} failed: Financial Modeling Prep retries exhausted."
        )

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

    def get_peers(self, ticker: str) -> list[dict[str, Any]]:
        """Peer companies via GET /stable/stock-peers (duck-typed, spec §19.2).

        Returns the §19.2 payload shape ``[{symbol, name, price, mktCap}]``
        (FMP's ``companyName`` is mapped to ``name``); the target symbol is
        excluded and an unknown ticker yields ``[]``. VERIFIED working on the
        free plan (the company-screener endpoint is NOT).
        """
        symbol = ticker.strip().upper()
        data = self._request_json(
            "/stable/stock-peers",
            {"symbol": symbol},
            what=f"FMP peers for {symbol}",
        )
        if not isinstance(data, list):
            return []
        peers: list[dict[str, Any]] = []
        for record in data:
            if not isinstance(record, dict):
                continue
            peer_symbol = record.get("symbol")
            if not peer_symbol or str(peer_symbol).upper() == symbol:
                continue
            peers.append(
                {
                    "symbol": str(peer_symbol),
                    "name": str(record.get("companyName") or peer_symbol),
                    "price": _to_float(record.get("price")),
                    "mktCap": _to_float(record.get("mktCap")),
                }
            )
        return peers

    def get_news(self, ticker: str, limit: int = 12) -> list[dict[str, Any]] | None:
        """Stock news via GET /stable/news/stock, or None when plan-gated (§19.6).

        The FMP free plan answers this endpoint with a "Restricted Endpoint"
        body (and sometimes HTTP 402/403). That is "unavailable", not an
        error: return None so callers fall through to the next news source.
        Other failures map to ProviderError like every FMP call.
        """
        symbol = ticker.strip().upper()
        what = f"FMP news for {symbol}"
        params = {"symbols": symbol, "limit": str(limit), "apikey": self.api_key}
        try:
            response = self._client.get(
                f"{BASE_URL}/stable/news/stock",
                params=params,
                timeout=TIMEOUT_SECONDS,
            )
            if response.status_code in (402, 403) or "Restricted Endpoint" in response.text:
                return None  # plan-gated endpoint — unavailable, never an error
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                f"{what} failed: Financial Modeling Prep returned HTTP "
                f"{exc.response.status_code}."
            ) from None  # severed: chained httpx error embeds the API key URL
        except httpx.HTTPError as exc:
            raise ProviderError(
                f"{what} failed: could not reach Financial Modeling Prep "
                f"({exc.__class__.__name__})."
            ) from None  # severed: chained httpx error embeds the API key URL
        except ValueError:
            raise ProviderError(
                f"{what} failed: Financial Modeling Prep returned invalid JSON."
            ) from None  # severed: chained httpx error embeds the API key URL
        if not isinstance(data, list):
            return None
        return [record for record in data if isinstance(record, dict)]

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
