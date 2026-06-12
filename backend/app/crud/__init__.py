"""Persistence helpers: users, company cache, peers cache, saved deals (spec §11, §19.8)."""

from app.crud.companies import get_cached, get_company_by_ticker, upsert_company
from app.crud.deals import (
    DuplicateDealError,
    create_saved_deal,
    delete_deal,
    list_for_user,
    update_assumptions,
)
from app.crud.peers import (
    PEERS_CACHE_TTL_DAYS,
    get_peers_cache,
    is_fresh,
    upsert_peers_cache,
)
from app.crud.users import DuplicateEmailError, create_user, get_by_email

__all__ = [
    "DuplicateDealError",
    "DuplicateEmailError",
    "PEERS_CACHE_TTL_DAYS",
    "create_saved_deal",
    "create_user",
    "delete_deal",
    "get_by_email",
    "get_cached",
    "get_company_by_ticker",
    "get_peers_cache",
    "is_fresh",
    "list_for_user",
    "update_assumptions",
    "upsert_company",
    "upsert_peers_cache",
]
