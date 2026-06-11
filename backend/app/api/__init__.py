"""API router (spec §12): health plus search/companies/auth/deals sub-routers."""

from fastapi import APIRouter

from app.api.routes_auth import router as auth_router
from app.api.routes_companies import router as companies_router
from app.api.routes_deals import router as deals_router
from app.api.routes_search import router as search_router
from app.core.config import settings
from app.providers.factory import get_provider

api_router = APIRouter(prefix="/api")


@api_router.get("/health")
def health() -> dict[str, str]:
    # Report the resolved effective provider (e.g. "mock"), not the raw mode
    # string, so "auto" deployments can see which source is actually serving.
    try:
        provider_name = get_provider(settings).name
    except Exception:
        provider_name = settings.data_provider
    return {"status": "ok", "provider": provider_name}


api_router.include_router(search_router)
api_router.include_router(companies_router)
api_router.include_router(auth_router)
api_router.include_router(deals_router)
