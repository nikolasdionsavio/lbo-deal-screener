"""Persistence helpers: users, company cache, saved deals + snapshots (spec §11)."""

from app.crud.companies import get_cached, get_company_by_ticker, upsert_company
from app.crud.deals import (
    DuplicateDealError,
    create_saved_deal,
    delete_deal,
    list_for_user,
    update_assumptions,
)
from app.crud.users import DuplicateEmailError, create_user, get_by_email

__all__ = [
    "DuplicateDealError",
    "DuplicateEmailError",
    "create_saved_deal",
    "create_user",
    "delete_deal",
    "get_by_email",
    "get_cached",
    "get_company_by_ticker",
    "list_for_user",
    "update_assumptions",
    "upsert_company",
]
