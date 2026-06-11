"""API router (spec §12): health plus search/companies/auth/deals sub-routers."""

from fastapi import APIRouter

from app.api.routes_auth import router as auth_router
from app.api.routes_companies import router as companies_router
from app.api.routes_deals import router as deals_router
from app.api.routes_search import router as search_router
from app.core.config import settings

api_router = APIRouter(prefix="/api")


@api_router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "provider": settings.data_provider}


api_router.include_router(search_router)
api_router.include_router(companies_router)
api_router.include_router(auth_router)
api_router.include_router(deals_router)
