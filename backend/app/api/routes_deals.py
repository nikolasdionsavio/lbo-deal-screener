"""Saved-deals routes (spec §12) — Bearer-gated CRUD with §11 snapshots.

POST recomputes score + memo + LBO server-side and snapshots them; PUT
.../assumptions recomputes and appends a new lbo_outputs row; DELETE -> 204.
Duplicate (user, ticker) saves -> 409. Deals of other users -> 404.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_provider_dep, provider_errors_to_http
from app.auth.deps import get_current_user
from app.crud import companies as companies_crud
from app.crud import deals as deals_crud
from app.crud.deals import DuplicateDealError
from app.db.base import get_db
from app.db.models import SavedDeal as SavedDealModel
from app.db.models import User
from app.providers.base import DataProvider
from app.schemas.deal import (
    DealAssumptionsUpdateRequest,
    DealCreateRequest,
    SavedDeal,
)
from app.services import company_service, deal_service

router = APIRouter(prefix="/deals", tags=["deals"])

_NOT_FOUND = "Saved deal not found"


@router.get("")
def list_deals(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SavedDeal]:
    return deals_crud.list_for_user(db, user.id)


@router.post("")
def create_deal(
    body: DealCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    provider: DataProvider = Depends(get_provider_dep),
) -> SavedDeal:
    with provider_errors_to_http():
        bundle = company_service.get_bundle(body.ticker, db, provider)
    # The saved deal references a companies row; persist it even for the mock
    # provider (the §11 mock cache skip applies to reads, not this FK target).
    company = companies_crud.upsert_company(db, bundle)
    payloads = deal_service.compose_deal_payloads(bundle, body.lbo_assumptions)
    try:
        return deals_crud.create_saved_deal(
            db,
            user_id=user.id,
            company_id=company.id,
            ticker=bundle.info.ticker,
            company_name=bundle.info.name,
            **payloads,
        )
    except DuplicateDealError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.put("/{deal_id}/assumptions")
def update_deal_assumptions(
    deal_id: int,
    body: DealAssumptionsUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    provider: DataProvider = Depends(get_provider_dep),
) -> SavedDeal:
    deal = db.get(SavedDealModel, deal_id)
    if deal is None or deal.user_id != user.id:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)

    with provider_errors_to_http():
        bundle = company_service.get_bundle(deal.ticker, db, provider)
    try:
        lbo_payload = deal_service.compute_lbo(
            bundle, body.lbo_assumptions
        ).model_dump()
    except deal_service.MissingEntryDataError:
        lbo_payload = None  # store the assumptions even without runnable outputs

    updated = deals_crud.update_assumptions(
        db, deal_id, user.id, body.lbo_assumptions.model_dump(), lbo_payload
    )
    if updated is None:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return updated


@router.delete("/{deal_id}", status_code=204)
def delete_deal(
    deal_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    if not deals_crud.delete_deal(db, deal_id, user.id):
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
