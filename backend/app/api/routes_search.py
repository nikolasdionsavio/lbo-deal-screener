"""GET /api/search — ticker or company-name search (spec §12)."""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_provider_dep, provider_errors_to_http
from app.providers.base import DataProvider
from app.schemas.company import SearchResult

router = APIRouter(tags=["search"])


@router.get("/search")
def search(
    q: str = Query("", description="Ticker or company-name fragment"),
    provider: DataProvider = Depends(get_provider_dep),
) -> list[SearchResult]:
    with provider_errors_to_http():
        return provider.search(q)
