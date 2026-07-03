"""Risk-assessment orchestration: assemble the company + sector risk profile
from the bundle (financials), market stats, peers and the latest 10-K.

Financial risk is always computed from the cached bundle. Sector comparison and
the qualitative 10-K risk-factor extraction are best-effort — if peer data or
the filing cannot be loaded, the page still renders with the parts that could.
The full response is cached (it is expensive: peers + a 10-K download).
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings as global_settings
from app.market_stats import get_market_stats
from app.providers.base import DataProvider
from app.risk import (
    compute_financial_risk,
    compute_market_risk,
    compute_sector_risk,
    financial_band,
)
from app.risk.factors import extract_risk_factors
from app.schemas.risk import RiskFactor, RiskResponse
from app.services import company_service, filings_service, peers_service

_CACHE: dict[str, tuple[float, RiskResponse]] = {}
_TTL_SECONDS = 21600  # 6h — risk metrics move slowly and the fetch is expensive


def reset_cache() -> None:
    _CACHE.clear()


def compute_risks(ticker: str, db: Session, provider: DataProvider) -> RiskResponse:
    key = ticker.strip().upper()
    now = time.time()
    cached = _CACHE.get(key)
    if cached is not None and now - cached[0] < _TTL_SECONDS:
        return cached[1]

    bundle = company_service.get_bundle(key, db, provider)
    warnings: list[str] = []
    sources = ["SEC EDGAR (financial statements + 10-K)"]

    # Financial risk (always, from the statements).
    distress, fin_metrics, fin_warn = compute_financial_risk(bundle)
    warnings.extend(fin_warn)

    # Market risk (best-effort).
    stats = None
    try:
        stats = get_market_stats(key)
    except Exception:
        pass
    market_metrics = compute_market_risk(stats)
    if stats is not None and not _is_empty_market(stats):
        sources.append(stats.source)

    band, summary = financial_band(distress, fin_metrics)

    # Sector context (best-effort — peer loads can be slow or fail).
    sector_comparisons = []
    sector_note = ""
    try:
        pr = peers_service.get_peers(key, db, provider)
        sector_comparisons, sector_note = compute_sector_risk(pr.target, pr.peers)
    except Exception:
        sector_note = "Sector comparison is unavailable (peer data could not be loaded)."

    # Qualitative 10-K risk factors (best-effort).
    risk_factors: list[RiskFactor] = []
    categories: dict[str, int] = {}
    going_concern = False
    rf_source: str | None = None
    rf_period: str | None = None
    try:
        filings = filings_service.get_filings(key, provider)
        tenk = next(
            (f for f in filings.filings if f.form == "10-K" and f.url), None
        )
        if tenk is not None and tenk.url:
            rf_source = tenk.url
            year = (tenk.report_date or tenk.filed or "")[:4]
            rf_period = f"FY{year} 10-K" if year else "Latest 10-K"
            result = extract_risk_factors(
                tenk.url, global_settings.sec_edgar_user_agent
            )
            if result is not None:
                items, going_concern = result
                risk_factors = [RiskFactor(**it) for it in items]
                for it in items:
                    categories[it["category"]] = categories.get(it["category"], 0) + 1
                if not items:
                    warnings.append(
                        "Individual risk factors could not be parsed from the 10-K; "
                        "open the filing for the full Item 1A."
                    )
            else:
                warnings.append(
                    "The 10-K could not be fetched for risk-factor extraction."
                )
        else:
            warnings.append("No 10-K on file to extract risk factors from.")
    except Exception:
        warnings.append("Risk-factor extraction failed; the 10-K may be unavailable.")

    resp = RiskResponse(
        ticker=key,
        as_of=datetime.now(timezone.utc).date().isoformat(),
        financial_band=band,
        financial_summary=summary,
        distress=distress,
        financial_metrics=fin_metrics,
        market_metrics=market_metrics,
        sector_comparisons=sector_comparisons,
        sector_note=sector_note,
        risk_factors=risk_factors,
        risk_factor_categories=categories,
        going_concern_flagged=going_concern,
        risk_factors_source=rf_source,
        risk_factors_period=rf_period,
        warnings=warnings,
        sources=sorted(set(sources)),
    )
    _CACHE[key] = (now, resp)
    return resp


def _is_empty_market(stats) -> bool:
    return stats.stats.beta is None and stats.stats.fifty_two_week_low is None
