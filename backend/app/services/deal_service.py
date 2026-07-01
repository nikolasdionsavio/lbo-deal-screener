"""Deal composition: KPIs, score, valuation, LBO and memo from one bundle (§12).

`compose_deal_payloads` produces the already-``model_dump()``-ed payload dicts
that `crud.deals.create_saved_deal` / `update_assumptions` expect when a deal
is saved or its assumptions change (spec §11 snapshot rows).
"""

from typing import Any

from app.kpis import compute_kpis
from app.lbo import derive_defaults, run_lbo
from app.memo import generate_memo
from app.schemas.company import CompanyDataBundle
from app.schemas.filings import Filing
from app.schemas.financials import FiscalYearFinancials
from app.schemas.lbo import LboAssumptions, LboResponse
from app.schemas.memo import MemoResponse
from app.scoring import compute_score
from app.services.company_service import build_profile
from app.valuation import compute_valuation


class MissingEntryDataError(Exception):
    """The LBO entry base (latest-FY revenue) is missing or non-positive.

    Revenue is the one field with no fallback: without it there is no basis at
    all (a non-positive EBITDA is handled by the revenue valuation basis).
    Routes map this to HTTP 422 with a readable detail.
    """


def _latest(bundle: CompanyDataBundle) -> FiscalYearFinancials | None:
    financials = sorted(bundle.financials, key=lambda y: y.fiscal_year)
    return financials[-1] if financials else None


def resolve_assumptions(
    bundle: CompanyDataBundle, assumptions: LboAssumptions | None
) -> LboAssumptions:
    """Caller-supplied assumptions, or §8 defaults derived from the bundle."""
    if assumptions is not None:
        return assumptions
    derived, _basis = derive_defaults(bundle)
    return derived


def compute_lbo(
    bundle: CompanyDataBundle, assumptions: LboAssumptions | None = None
) -> LboResponse:
    """Run the full §8 LBO (defaults when assumptions is None).

    Raises MissingEntryDataError when the entry base is unusable.
    """
    assumptions = resolve_assumptions(bundle, assumptions)
    latest = _latest(bundle)
    if latest is None or latest.revenue is None or latest.revenue <= 0:
        raise MissingEntryDataError(
            "LBO model requires revenue for the latest fiscal year; it is "
            "unavailable for this company."
        )
    # Non-positive EBITDA is modeled on the revenue basis. If the caller passed
    # EBITDA-basis assumptions for such a company, override to the revenue basis
    # so the engine prices entry on EV/Revenue rather than on a negative EBITDA.
    entry_ebitda = latest.ebitda if latest.ebitda is not None else 0.0
    if entry_ebitda <= 0 and assumptions.valuation_basis != "revenue":
        derived, _basis = derive_defaults(bundle)
        assumptions = derived
    return run_lbo(
        entry_ebitda,
        latest.revenue,
        assumptions,
        ticker=bundle.info.ticker.upper(),
    )


def compose_memo(
    bundle: CompanyDataBundle,
    assumptions: LboAssumptions | None = None,
    filings: list[Filing] | None = None,
) -> MemoResponse:
    """Memo from computed data: profile, KPIs, valuation, LBO, score (§10).

    `filings` is best-effort 10-K context (spec §19.3); callers pass None when
    filings could not be fetched and the memo is unchanged.
    """
    profile = build_profile(bundle)
    kpis = compute_kpis(bundle)
    valuation = compute_valuation(bundle)  # default multiples
    score = compute_score(kpis, valuation.multiples)
    try:
        lbo: LboResponse | None = compute_lbo(bundle, assumptions)
    except MissingEntryDataError:
        lbo = None  # memo states the gap instead of failing
    return generate_memo(
        profile, kpis, valuation, lbo, score, currency=bundle.currency, filings=filings
    )


def compose_deal_payloads(
    bundle: CompanyDataBundle, lbo_assumptions: LboAssumptions | None = None
) -> dict[str, Any]:
    """Snapshot payload dicts for crud.deals (KPI, score, memo, LBO) — §11, §12."""
    profile = build_profile(bundle)
    kpis = compute_kpis(bundle)
    valuation = compute_valuation(bundle)
    score = compute_score(kpis, valuation.multiples)
    assumptions = resolve_assumptions(bundle, lbo_assumptions)
    try:
        lbo: LboResponse | None = compute_lbo(bundle, assumptions)
    except MissingEntryDataError:
        lbo = None
    memo = generate_memo(profile, kpis, valuation, lbo, score, currency=bundle.currency)
    return {
        "kpi_payload": kpis.model_dump(),
        "score_payload": score.model_dump(),
        "memo_payload": memo.model_dump(),
        "lbo_assumptions_payload": assumptions.model_dump(),
        "lbo_output_payload": lbo.model_dump() if lbo is not None else None,
    }
