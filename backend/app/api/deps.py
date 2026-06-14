"""Shared API dependencies and provider error mapping (spec §12).

Error mapping: CompanyNotFoundError -> 404, ProviderError / ProviderConfigError
-> 502 with a readable detail. Validation errors stay FastAPI's default 422.
"""

import threading
from contextlib import contextmanager
from typing import Iterator

from fastapi import HTTPException

from app.core.config import settings
from app.providers.base import DataProvider
from app.providers.exceptions import CompanyNotFoundError, ProviderError
from app.providers.factory import get_provider


@contextmanager
def provider_errors_to_http() -> Iterator[None]:
    """Map provider exceptions raised inside the block to §12 HTTP errors."""
    try:
        yield
    except CompanyNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProviderError as exc:  # ProviderConfigError subclasses ProviderError
        raise HTTPException(status_code=502, detail=str(exc)) from exc


# Process-level provider singleton. Building the provider also builds the
# in-memory SEC ticker search index (~10k entries); rebuilding it per request
# is CPU-heavy and, on burst-throttled free hosting, made autocomplete take
# 15-30s. The provider is stateless apart from read-mostly caches and a
# thread-safe httpx.Client, so one instance is safely shared across requests.
_provider_lock = threading.Lock()
_provider_singleton: DataProvider | None = None


def _resolve_provider() -> DataProvider:
    global _provider_singleton
    if _provider_singleton is None:
        with _provider_lock:
            if _provider_singleton is None:
                _provider_singleton = get_provider(settings)
    return _provider_singleton


def get_provider_dep() -> DataProvider:
    """Return the shared data provider; tests override this dependency."""
    with provider_errors_to_http():
        return _resolve_provider()


def warm_provider() -> None:
    """Build the provider and its ticker search index at startup so the first
    search request is instant (not paying a cold index build on the request
    path). Best-effort: never blocks startup on a provider/config error."""
    try:
        provider = _resolve_provider()
        provider.search("a")  # forces the SEC ticker index to build once
    except Exception:  # noqa: BLE001 - startup warm-up must never crash boot
        pass
