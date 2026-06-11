"""API router. Sub-routers (companies, auth, deals, search) are added by later
modules; for now only the health route lives here (spec §12)."""

from fastapi import APIRouter

from app.core.config import settings

api_router = APIRouter(prefix="/api")


@api_router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "provider": settings.data_provider}
