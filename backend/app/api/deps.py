"""Shared API dependencies and provider error mapping (spec §12).

Error mapping: CompanyNotFoundError -> 404, ProviderError / ProviderConfigError
-> 502 with a readable detail. Validation errors stay FastAPI's default 422.
"""

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


def get_provider_dep() -> DataProvider:
    """Build the configured data provider; tests override this dependency."""
    with provider_errors_to_http():
        return get_provider(settings)
