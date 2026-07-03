"""Finnhub client for the market-stats module (free tier: 60 req/min, no daily
cap, works from datacenter IPs — unlike Yahoo .info, and far more generous than
FMP's 250/day).

Only the free-tier endpoints are used: quote, company profile2, basic financial
metrics, and analyst recommendation trends. Price targets, institutional
ownership and insider transactions are Finnhub premium and are not called.

Each method returns parsed JSON (dict/list) or raises on transport/HTTP error;
callers tolerate per-call failures so one endpoint failing does not sink the
others. The API token authenticates the request (query param), never an IP.
"""

from __future__ import annotations

from typing import Any

import httpx

BASE_URL = "https://finnhub.io/api/v1"
TIMEOUT_SECONDS = 15.0


class FinnhubClient:
    name = "finnhub"

    def __init__(self, api_key: str, *, client: httpx.Client | None = None) -> None:
        self.api_key = api_key.strip()
        self._client = client or httpx.Client(timeout=TIMEOUT_SECONDS)

    def _get(self, path: str, params: dict[str, str]) -> Any:
        response = self._client.get(
            f"{BASE_URL}{path}",
            params={**params, "token": self.api_key},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()

    def quote(self, symbol: str) -> dict[str, Any]:
        """Real-time US quote: c=current, h/l/o, pc=prev close."""
        data = self._get("/quote", {"symbol": symbol.strip().upper()})
        return data if isinstance(data, dict) else {}

    def profile2(self, symbol: str) -> dict[str, Any]:
        """Free company profile: currency, marketCapitalization, shareOutstanding."""
        data = self._get("/stock/profile2", {"symbol": symbol.strip().upper()})
        return data if isinstance(data, dict) else {}

    def metrics(self, symbol: str) -> dict[str, Any]:
        """Basic financials (metric=all): the `metric` object holds beta,
        52WeekHigh/Low, peTTM, pbAnnual, margins, ROE, dividend fields."""
        data = self._get(
            "/stock/metric", {"symbol": symbol.strip().upper(), "metric": "all"}
        )
        if isinstance(data, dict) and isinstance(data.get("metric"), dict):
            return data["metric"]
        return {}

    def recommendations(self, symbol: str) -> list[dict[str, Any]]:
        """Analyst recommendation trends, newest period first: each row has
        strongBuy / buy / hold / sell / strongSell counts."""
        data = self._get("/stock/recommendation", {"symbol": symbol.strip().upper()})
        return [r for r in data if isinstance(r, dict)] if isinstance(data, list) else []
