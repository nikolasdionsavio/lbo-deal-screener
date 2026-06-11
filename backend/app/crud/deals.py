"""Saved-deal persistence with snapshot rows (spec §11, §12).

The services layer computes the payload dicts (KPI/score/memo/LBO responses,
already ``model_dump()``-ed); this module only persists and reconstructs them.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import (
    DealScore,
    InvestmentMemo,
    KpiSnapshot,
    LboAssumptionsRecord,
    LboOutputRecord,
    SavedDeal,
    utcnow,
)
from app.schemas.deal import SavedDeal as SavedDealSchema
from app.schemas.lbo import LboAssumptions
from app.schemas.memo import MemoResponse


class DuplicateDealError(Exception):
    """The user already saved this ticker — routes map this to HTTP 409."""


def _latest_assumptions(deal: SavedDeal) -> LboAssumptionsRecord | None:
    if not deal.lbo_assumptions:
        return None
    return max(deal.lbo_assumptions, key=lambda row: row.id)


def _to_schema(db: Session, deal: SavedDeal) -> SavedDealSchema:
    """Reconstruct the SavedDeal schema with embedded latest memo + assumptions."""
    assumptions_row = _latest_assumptions(deal)
    memo_payload: dict[str, Any] | None = None
    if deal.memo_id is not None:
        memo = db.get(InvestmentMemo, deal.memo_id)
        if memo is not None:
            memo_payload = memo.payload
    return SavedDealSchema(
        id=deal.id,
        ticker=deal.ticker,
        company_name=deal.company_name,
        score=deal.score,
        rating=deal.rating,
        created_at=deal.created_at,
        updated_at=deal.updated_at,
        lbo_assumptions=(
            LboAssumptions.model_validate(assumptions_row.payload)
            if assumptions_row is not None
            else None
        ),
        memo=(
            MemoResponse.model_validate(memo_payload)
            if memo_payload is not None
            else None
        ),
    )


def _get_owned(db: Session, deal_id: int, user_id: int) -> SavedDeal | None:
    return db.scalar(
        select(SavedDeal).where(SavedDeal.id == deal_id, SavedDeal.user_id == user_id)
    )


def create_saved_deal(
    db: Session,
    *,
    user_id: int,
    company_id: int,
    ticker: str,
    company_name: str,
    kpi_payload: dict[str, Any] | None = None,
    score_payload: dict[str, Any] | None = None,
    memo_payload: dict[str, Any] | None = None,
    lbo_assumptions_payload: dict[str, Any] | None = None,
    lbo_output_payload: dict[str, Any] | None = None,
) -> SavedDealSchema:
    """Create a saved deal plus its snapshot rows from pre-computed payloads.

    Raises DuplicateDealError on a second save of the same (user, ticker).
    """
    ticker = ticker.upper()
    duplicate = db.scalar(
        select(SavedDeal).where(
            SavedDeal.user_id == user_id, SavedDeal.ticker == ticker
        )
    )
    if duplicate is not None:
        raise DuplicateDealError(f"deal already saved for ticker {ticker}")

    try:
        if kpi_payload is not None:
            db.add(
                KpiSnapshot(
                    company_id=company_id,
                    as_of=kpi_payload.get("as_of"),
                    payload=kpi_payload,
                )
            )
        if score_payload is not None:
            db.add(
                DealScore(
                    company_id=company_id,
                    total=score_payload.get("total"),
                    rating=score_payload.get("rating"),
                    payload=score_payload,
                )
            )

        memo: InvestmentMemo | None = None
        if memo_payload is not None:
            memo = InvestmentMemo(
                company_id=company_id,
                rating=memo_payload.get("rating"),
                payload=memo_payload,
            )
            db.add(memo)
            db.flush()  # assign memo.id for the deal row

        deal = SavedDeal(
            user_id=user_id,
            company_id=company_id,
            ticker=ticker,
            company_name=company_name,
            score=score_payload.get("total") if score_payload else None,
            rating=score_payload.get("rating") if score_payload else None,
            memo_id=memo.id if memo is not None else None,
        )
        db.add(deal)
        db.flush()  # assign deal.id; unique(user_id, ticker) enforced here

        if lbo_assumptions_payload is not None:
            assumptions = LboAssumptionsRecord(
                saved_deal_id=deal.id, payload=lbo_assumptions_payload
            )
            db.add(assumptions)
            db.flush()
            if lbo_output_payload is not None:
                db.add(
                    LboOutputRecord(
                        lbo_assumptions_id=assumptions.id,
                        payload=lbo_output_payload,
                    )
                )
        db.commit()
    except IntegrityError as exc:  # concurrent duplicate save race
        db.rollback()
        raise DuplicateDealError(f"deal already saved for ticker {ticker}") from exc

    db.refresh(deal)
    return _to_schema(db, deal)


def list_for_user(db: Session, user_id: int) -> list[SavedDealSchema]:
    """All saved deals for the user, newest first, with embedded snapshots."""
    deals = db.scalars(
        select(SavedDeal)
        .where(SavedDeal.user_id == user_id)
        .order_by(SavedDeal.created_at.desc(), SavedDeal.id.desc())
    ).all()
    return [_to_schema(db, deal) for deal in deals]


def update_assumptions(
    db: Session,
    deal_id: int,
    user_id: int,
    assumptions_payload: dict[str, Any],
    lbo_output_payload: dict[str, Any] | None = None,
) -> SavedDealSchema | None:
    """Store new assumptions (and an lbo_outputs row) for an owned deal.

    Returns None when the deal does not exist or belongs to another user
    (routes map that to 404).
    """
    deal = _get_owned(db, deal_id, user_id)
    if deal is None:
        return None

    assumptions = _latest_assumptions(deal)
    if assumptions is None:
        assumptions = LboAssumptionsRecord(
            saved_deal_id=deal.id, payload=assumptions_payload
        )
        db.add(assumptions)
    else:
        assumptions.payload = assumptions_payload
        assumptions.updated_at = utcnow()
    db.flush()

    if lbo_output_payload is not None:
        db.add(
            LboOutputRecord(
                lbo_assumptions_id=assumptions.id, payload=lbo_output_payload
            )
        )

    deal.updated_at = utcnow()
    db.commit()
    db.refresh(deal)
    return _to_schema(db, deal)


def delete_deal(db: Session, deal_id: int, user_id: int) -> bool:
    """Delete an owned deal (cascades assumptions + outputs). False if absent."""
    deal = _get_owned(db, deal_id, user_id)
    if deal is None:
        return False
    db.delete(deal)
    db.commit()
    return True


# Spec §11 scope names this operation "delete"; keep an alias for callers.
delete = delete_deal
