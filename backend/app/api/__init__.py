"""API router (spec §12): health plus search/companies/auth/deals sub-routers."""

from fastapi import APIRouter

from app.api.deps import _resolve_provider
from app.api.routes_auth import router as auth_router
from app.api.routes_companies import router as companies_router
from app.api.routes_deals import router as deals_router
from app.api.routes_oauth import router as oauth_router
from app.api.routes_search import router as search_router
from app.core.config import settings

api_router = APIRouter(prefix="/api")


@api_router.get("/health")
def health() -> dict[str, str]:
    # Report the resolved effective provider via the shared singleton (no
    # per-request provider construction: that leaked an httpx.Client on every
    # health check / keep-alive ping and added needless CPU on free hosting).
    try:
        provider_name = _resolve_provider().name
    except Exception:
        provider_name = settings.data_provider
    return {"status": "ok", "provider": provider_name}


api_router.include_router(search_router)
api_router.include_router(companies_router)
api_router.include_router(auth_router)
api_router.include_router(oauth_router)
api_router.include_router(deals_router)
