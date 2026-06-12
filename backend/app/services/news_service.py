"""Company news chain: FMP -> yfinance -> empty + warning (spec §19.6, §19.8).

Resolution order:
1. FMP /stable/news/stock when ``fmp_api_key`` is set. The free plan gates
   this endpoint behind a "Restricted Endpoint" body (or HTTP 402/403):
   FmpProvider.get_news returns None for that, which means "fall through",
   never an error. Quota hits (§19.8) raise a typed ProviderError and fall
   through with a warning like any other FMP failure.
2. yfinance ``Ticker(t).get_news(count=...)`` (keyless; imported lazily so
   the dependency stays optional). Items arrive under a ``content`` dict.
3. Mock mode or no source available -> 200 with empty items + the live-only
   warning.

Items are sorted newest first and capped at ``limit`` (§19.8: clamped to
1..60, default 30) on every path.
"""

from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.core.config import settings as global_settings
from app.providers.base import DataProvider
from app.providers.exceptions import ProviderError
from app.providers.fmp import DATA_SOURCE as FMP_PROVIDER_LABEL
from app.providers.fmp import FmpProvider
from app.providers.mock import MockProvider
from app.schemas.news import NewsItem, NewsResponse

DEFAULT_LIMIT = 30
MAX_LIMIT = 60
LIVE_ONLY_WARNING = "News is available in live mode only."
YFINANCE_PROVIDER_LABEL = "Yahoo Finance (unofficial endpoints, via yfinance)"
NO_PROVIDER_LABEL = "none"
FMP_RESTRICTED_WARNING = (
    "Financial Modeling Prep news is not available on the configured plan "
    "(Restricted Endpoint)."
)


def _build_fmp(app_settings: Settings) -> FmpProvider:
    """Factory split out so tests can monkeypatch in a MockTransport client."""
    return FmpProvider(app_settings.fmp_api_key)


def clamp_limit(limit: int) -> int:
    """Clamp the §19.8 news limit into 1..MAX_LIMIT (never rejects)."""
    return max(1, min(MAX_LIMIT, int(limit)))


def _sorted_capped(items: list[NewsItem], limit: int) -> list[NewsItem]:
    """Newest first (ISO timestamps sort lexicographically), capped at limit."""
    return sorted(items, key=lambda item: item.published_at or "", reverse=True)[
        :limit
    ]


def _fmp_item(record: dict[str, Any]) -> NewsItem | None:
    title = record.get("title")
    url = record.get("url")
    if not title or not url:
        return None
    published = record.get("publishedDate")
    return NewsItem(
        title=str(title),
        url=str(url),
        source=record.get("publisher") or record.get("site") or None,
        # FMP uses "YYYY-MM-DD HH:MM:SS"; normalize to ISO-8601.
        published_at=str(published).replace(" ", "T") if published else None,
        summary=record.get("text") or None,
    )


def _fmp_news(
    ticker: str, app_settings: Settings, warnings: list[str], limit: int
) -> list[NewsItem]:
    try:
        raw = _build_fmp(app_settings).get_news(ticker, limit=limit)
    except ProviderError as exc:
        warnings.append(f"News unavailable from Financial Modeling Prep: {exc}")
        return []
    if raw is None:
        warnings.append(FMP_RESTRICTED_WARNING)
        return []
    return _sorted_capped(
        [item for item in (_fmp_item(r) for r in raw) if item is not None], limit
    )


def _yfinance_item(record: dict[str, Any]) -> NewsItem | None:
    content = record.get("content")
    if not isinstance(content, dict):
        return None
    title = content.get("title")
    url_holder = content.get("canonicalUrl") or content.get("clickThroughUrl") or {}
    url = url_holder.get("url") if isinstance(url_holder, dict) else None
    if not title or not url:
        return None
    provider = content.get("provider")
    source = provider.get("displayName") if isinstance(provider, dict) else None
    return NewsItem(
        title=str(title),
        url=str(url),
        source=source or None,
        published_at=content.get("pubDate") or None,
        summary=content.get("summary") or None,
    )


def _yfinance_news(ticker: str, warnings: list[str], limit: int) -> list[NewsItem]:
    try:
        import yfinance  # lazy: the dependency stays optional
    except ImportError:
        warnings.append("News unavailable: yfinance is not installed.")
        return []
    try:
        raw = yfinance.Ticker(ticker).get_news(count=limit) or []
    except Exception as exc:  # unofficial endpoints fail in many shapes
        warnings.append(
            f"News unavailable from Yahoo Finance ({exc.__class__.__name__})."
        )
        return []
    return _sorted_capped(
        [
            item
            for item in (_yfinance_item(r) for r in raw if isinstance(r, dict))
            if item is not None
        ],
        limit,
    )


def get_news(
    ticker: str,
    provider: DataProvider,
    app_settings: Settings | None = None,
    limit: int = DEFAULT_LIMIT,
) -> NewsResponse:
    """Resolve the §19.6 news chain; never raises for missing sources.

    ``limit`` (§19.8) is clamped to 1..60 and forwarded to FMP (``limit``)
    and yfinance (``get_news(count=...)``).
    """
    app_settings = app_settings or global_settings
    ticker = ticker.strip().upper()
    limit = clamp_limit(limit)

    if isinstance(provider, MockProvider):
        return NewsResponse(
            ticker=ticker,
            items=[],
            provider=NO_PROVIDER_LABEL,
            warnings=[LIVE_ONLY_WARNING],
        )

    warnings: list[str] = []
    if app_settings.fmp_api_key.strip():
        items = _fmp_news(ticker, app_settings, warnings, limit)
        if items:
            return NewsResponse(
                ticker=ticker,
                items=items,
                provider=FMP_PROVIDER_LABEL,
                warnings=warnings,
            )

    items = _yfinance_news(ticker, warnings, limit)
    if items:
        return NewsResponse(
            ticker=ticker,
            items=items,
            provider=YFINANCE_PROVIDER_LABEL,
            warnings=warnings,
        )

    if LIVE_ONLY_WARNING not in warnings:
        warnings.append(LIVE_ONLY_WARNING)
    return NewsResponse(
        ticker=ticker, items=[], provider=NO_PROVIDER_LABEL, warnings=warnings
    )
