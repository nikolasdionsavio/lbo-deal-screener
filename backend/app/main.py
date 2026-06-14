"""FastAPI application entry point (spec §3, §12, §13)."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.api.deps import warm_provider
from app.core.config import settings
from app.db.base import init_db

logger = logging.getLogger("lbo_screener")

_DEFAULT_JWT_SECRET = "dev-secret-change-me"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    if settings.jwt_secret == _DEFAULT_JWT_SECRET:
        logger.warning(
            "JWT_SECRET is the built-in development default. Set a random "
            "secret of at least 32 bytes before exposing this server."
        )
    # Build the shared provider + ticker search index once, at startup, so the
    # first autocomplete request is instant rather than paying a cold build.
    warm_provider()
    yield


app = FastAPI(title="LBO Deal Screener API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
