"""Company analysis routes (spec §12) — public, no auth required.

Tickers are case-insensitive (uppercased in the services layer). Unknown
tickers -> 404, provider failures -> 502, body validation -> 422.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_provider_dep, provider_errors_to_http
from app.db.base import get_db
from app.kpis import compute_kpis
from app.lbo import derive_defaults
from app.providers.base import DataProvider
from app.schemas.company import CompanyDataBundle, CompanyProfile
from app.schemas.financials import FinancialsResponse
from app.schemas.kpi import KpiResponse
from app.schemas.lbo import LboAssumptions, LboDefaultsResponse, LboResponse
from app.schemas.memo import MemoRequest, MemoResponse
from app.schemas.score import ScoreResponse
from app.schemas.valuation import ValuationRequest, ValuationResponse
from app.scoring import compute_score
from app.services import company_service, deal_service
from app.valuation import compute_valuation

router = APIRouter(prefix="/companies", tags=["companies"])


def _bundle(ticker: str, db: Session, provider: DataProvider) -> CompanyDataBundle:
    with provider_errors_to_http():
        return company_service.get_bundle(ticker, db, provider)


@router.get("/{ticker}/profile")
def get_profile(
    ticker: str,
    db: Session = Depends(get_db),
    provider: DataProvider = Depends(get_provider_dep),
) -> CompanyProfile:
    return company_service.build_profile(_bundle(ticker, db, provider))


@router.get("/{ticker}/financials")
def get_financials(
    ticker: str,
    db: Session = Depends(get_db),
    provider: DataProvider = Depends(get_provider_dep),
) -> FinancialsResponse:
    bundle = _bundle(ticker, db, provider)
    return FinancialsResponse(
        ticker=bundle.info.ticker.upper(),
        years=bundle.financials,
        data_source=bundle.data_source,
        fetched_at=bundle.fetched_at,
        warnings=bundle.warnings,
    )


@router.get("/{ticker}/kpis")
def get_kpis(
    ticker: str,
    db: Session = Depends(get_db),
    provider: DataProvider = Depends(get_provider_dep),
) -> KpiResponse:
    return compute_kpis(_bundle(ticker, db, provider))


@router.post("/{ticker}/valuation")
def post_valuation(
    ticker: str,
    request: ValuationRequest | None = None,  # {low, base, high}, all optional
    db: Session = Depends(get_db),
    provider: DataProvider = Depends(get_provider_dep),
) -> ValuationResponse:
    return compute_valuation(_bundle(ticker, db, provider), request)


@router.get("/{ticker}/lbo/defaults")
def get_lbo_defaults(
    ticker: str,
    db: Session = Depends(get_db),
    provider: DataProvider = Depends(get_provider_dep),
) -> LboDefaultsResponse:
    assumptions, basis = derive_defaults(_bundle(ticker, db, provider))
    return LboDefaultsResponse(assumptions=assumptions, basis=basis)


@router.post("/{ticker}/lbo")
def post_lbo(
    ticker: str,
    assumptions: LboAssumptions,
    db: Session = Depends(get_db),
    provider: DataProvider = Depends(get_provider_dep),
) -> LboResponse:
    bundle = _bundle(ticker, db, provider)
    try:
        return deal_service.compute_lbo(bundle, assumptions)
    except deal_service.MissingEntryDataError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{ticker}/score")
def get_score(
    ticker: str,
    db: Session = Depends(get_db),
    provider: DataProvider = Depends(get_provider_dep),
) -> ScoreResponse:
    bundle = _bundle(ticker, db, provider)
    kpis = compute_kpis(bundle)
    valuation = compute_valuation(bundle)
    return compute_score(kpis, valuation.multiples)


@router.post("/{ticker}/memo")
def post_memo(
    ticker: str,
    request: MemoRequest | None = None,  # {lbo_assumptions | null}
    db: Session = Depends(get_db),
    provider: DataProvider = Depends(get_provider_dep),
) -> MemoResponse:
    bundle = _bundle(ticker, db, provider)
    assumptions = request.lbo_assumptions if request is not None else None
    return deal_service.compose_memo(bundle, assumptions)
