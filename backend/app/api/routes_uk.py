"""UK (Companies House) routes: name search + per-company profile and accounts.

Gated on settings.companies_house_api_key: every endpoint returns 503 with a
clear message until the free key is configured. There is deliberately no
revenue/EBITDA screening endpoint here — the Companies House API cannot query by
financial figures; that needs a separately-indexed dataset (a later phase).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.config import settings
from app.providers.companies_house import CompaniesHouseClient
from app.providers.exceptions import (
    CompanyNotFoundError,
    ProviderConfigError,
    ProviderError,
)

router = APIRouter(prefix="/uk", tags=["uk"])


class UkSearchItem(BaseModel):
    company_number: str
    name: str
    status: str | None = None
    address: str | None = None
    sic_codes: list[str] = []


class UkAccounts(BaseModel):
    period_end: str | None = None
    currency: str | None = None
    turnover: float | None = None
    gross_profit: float | None = None
    operating_profit: float | None = None
    profit_before_tax: float | None = None
    profit_for_period: float | None = None
    net_assets: float | None = None
    cash: float | None = None
    # True when the filing carries no profit-and-loss (small-company exemption).
    no_profit_and_loss: bool = False


class UkCompanyResponse(BaseModel):
    company_number: str
    name: str
    status: str | None = None
    company_type: str | None = None
    incorporation_date: str | None = None
    sic_codes: list[str] = []
    address: str | None = None
    accounts: UkAccounts | None = None
    # Honest note about what is (not) disclosed.
    accounts_note: str


def _client() -> CompaniesHouseClient:
    try:
        return CompaniesHouseClient(settings.companies_house_api_key)
    except ProviderConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/search")
def uk_search(q: str = Query("", description="Company name or number")) -> list[UkSearchItem]:
    client = _client()
    try:
        results = client.search(q)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return [
        UkSearchItem(
            company_number=r.company_number,
            name=r.name,
            status=r.status,
            address=r.address,
            sic_codes=r.sic_codes,
        )
        for r in results
    ]


@router.get("/company/{number}")
def uk_company(number: str) -> UkCompanyResponse:
    client = _client()
    try:
        profile = client.profile(number)
        accounts = client.latest_accounts(number)
    except CompanyNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if accounts is None:
        note = (
            "No machine-readable (iXBRL) accounts are on file for this company, "
            "so financial figures are not available here."
        )
        acc = None
    elif accounts.no_profit_and_loss:
        note = (
            "This company files under the small-company exemption: its public "
            "accounts contain a balance sheet only, with no profit-and-loss "
            "account, so turnover and profit are not disclosed."
        )
        acc = UkAccounts(**accounts.__dict__)
    else:
        note = "Figures parsed from the latest iXBRL accounts filed at Companies House."
        acc = UkAccounts(**accounts.__dict__)

    return UkCompanyResponse(
        company_number=profile.company_number,
        name=profile.name,
        status=profile.status,
        company_type=profile.company_type,
        incorporation_date=profile.incorporation_date,
        sic_codes=profile.sic_codes,
        address=profile.address,
        accounts=acc,
        accounts_note=note,
    )
