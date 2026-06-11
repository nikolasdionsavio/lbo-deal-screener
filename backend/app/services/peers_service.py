"""Peer comparables composition (spec §19.2).

Peer discovery is duck-typed: the active provider's ``get_peers`` is used when
present (MockProvider and FmpProvider expose it); otherwise an FmpProvider is
constructed from settings when ``fmp_api_key`` is set; otherwise peers are
unavailable (warning + empty list, never an error).

Market cap / price for each peer come from the peers payload itself (no extra
quote calls). Per-peer fundamentals go through the cached
``company_service.get_bundle`` with per-peer try/except -> skip + warning, so
one bad peer never breaks the table. Quartile stats are computed over valued
peers only (target excluded), skipping None metric values, with linear
interpolation.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.config import settings as global_settings
from app.normalization import reporting_currency
from app.providers.base import DataProvider
from app.providers.exceptions import ProviderError
from app.providers.fmp import DATA_SOURCE as FMP_DATA_SOURCE
from app.providers.fmp import FmpProvider
from app.providers.mock import MockProvider
from app.schemas.company import CompanyDataBundle
from app.schemas.financials import FiscalYearFinancials
from app.schemas.peers import PEER_STAT_METRICS, PeerRow, PeersResponse, PeerStats
from app.services import company_service

MAX_PEERS = 6
NO_SOURCE_WARNING = (
    "Peer discovery unavailable: the active data provider has no peer source "
    "and FMP_API_KEY is not set."
)
MOCK_PEER_SOURCE = "Sample data (illustrative figures)"

PeerPayload = list[dict[str, Any]]


def _build_fmp(app_settings: Settings) -> FmpProvider:
    """Factory split out so tests can monkeypatch in a MockTransport client."""
    return FmpProvider(app_settings.fmp_api_key)


def _source_label(provider: DataProvider) -> str:
    if isinstance(provider, MockProvider):
        return MOCK_PEER_SOURCE
    if isinstance(provider, FmpProvider):
        return FMP_DATA_SOURCE
    return getattr(provider, "name", "provider")


def _resolve_peer_source(
    provider: DataProvider, app_settings: Settings
) -> tuple[Callable[[str], PeerPayload] | None, str | None]:
    """(get_peers callable, source label) per the §19.2 resolution order."""
    get_peers = getattr(provider, "get_peers", None)
    if callable(get_peers):
        return get_peers, _source_label(provider)
    if app_settings.fmp_api_key.strip():
        return _build_fmp(app_settings).get_peers, FMP_DATA_SOURCE
    return None, None


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _build_row(
    ticker: str,
    name: str,
    market_cap: float | None,
    price: float | None,
    bundle: CompanyDataBundle,
) -> PeerRow:
    """PeerRow metrics from the bundle's latest fiscal years + the given quote."""
    financials = sorted(bundle.financials, key=lambda y: y.fiscal_year)
    latest: FiscalYearFinancials | None = financials[-1] if financials else None
    prior: FiscalYearFinancials | None = financials[-2] if len(financials) > 1 else None

    shares: float | None = None
    if bundle.market is not None and bundle.market.shares_outstanding:
        shares = bundle.market.shares_outstanding
    elif latest is not None and latest.shares_outstanding:
        shares = latest.shares_outstanding
    if market_cap is None and price is not None and shares:
        market_cap = price * shares

    revenue = latest.revenue if latest is not None else None
    ebitda = latest.ebitda if latest is not None else None
    net_income = latest.net_income if latest is not None else None
    total_debt = latest.total_debt if latest is not None else None
    cash = latest.cash_and_equivalents if latest is not None else None
    net_debt = (
        total_debt - cash if total_debt is not None and cash is not None else None
    )
    enterprise_value = (
        market_cap + net_debt
        if market_cap is not None and net_debt is not None
        else None
    )
    prior_revenue = prior.revenue if prior is not None else None

    row = PeerRow(
        ticker=ticker,
        name=name,
        market_cap=market_cap,
        enterprise_value=enterprise_value,
        ev_ebitda=_ratio(enterprise_value, ebitda),
        ev_revenue=_ratio(enterprise_value, revenue),
        pe=_ratio(market_cap, net_income),
        ebitda_margin=_ratio(ebitda, revenue),
        revenue_growth_yoy=(
            revenue / prior_revenue - 1
            if revenue is not None and prior_revenue
            else None
        ),
        currency=reporting_currency(bundle),
    )
    for metric in (
        "market_cap",
        "enterprise_value",
        "ev_ebitda",
        "ev_revenue",
        "pe",
        "ebitda_margin",
        "revenue_growth_yoy",
    ):
        if getattr(row, metric) is None:
            row.warnings.append(f"{metric} unavailable")
    return row


def _quantile(sorted_values: list[float], q: float) -> float:
    """Linearly interpolated quantile over an ascending-sorted list."""
    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]
    position = (n - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    fraction = position - lower
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * fraction


def _stats(peers: list[PeerRow]) -> dict[str, PeerStats]:
    """Five-number summaries per §19.2 metric; metrics with no values omitted."""
    stats: dict[str, PeerStats] = {}
    for metric in PEER_STAT_METRICS:
        values = sorted(
            v for v in (getattr(row, metric) for row in peers) if v is not None
        )
        if not values:
            continue
        stats[metric] = PeerStats(
            min=values[0],
            q1=_quantile(values, 0.25),
            median=_quantile(values, 0.5),
            q3=_quantile(values, 0.75),
            max=values[-1],
        )
    return stats


def get_peers(
    ticker: str,
    db: Session,
    provider: DataProvider,
    app_settings: Settings | None = None,
) -> PeersResponse:
    """Build the §19.2 peers response.

    Raises CompanyNotFoundError / ProviderError only for the TARGET company
    (routes map them to 404/502); peer-level failures degrade to warnings.
    """
    app_settings = app_settings or global_settings
    ticker = ticker.strip().upper()
    warnings: list[str] = []

    target_bundle = company_service.get_bundle(ticker, db, provider)
    target_market = target_bundle.market
    target = _build_row(
        target_bundle.info.ticker.upper(),
        target_bundle.info.name,
        target_market.market_cap if target_market is not None else None,
        target_market.share_price if target_market is not None else None,
        target_bundle,
    )

    source, peer_source = _resolve_peer_source(provider, app_settings)
    raw_peers: PeerPayload = []
    if source is None:
        warnings.append(NO_SOURCE_WARNING)
    else:
        try:
            raw_peers = source(ticker) or []
        except ProviderError as exc:
            warnings.append(f"Peer discovery failed: {exc}")
    if source is not None and not raw_peers and not warnings:
        warnings.append(f"No peers found for {ticker}.")

    peers: list[PeerRow] = []
    for raw in raw_peers:
        if len(peers) >= MAX_PEERS:
            break
        symbol = str(raw.get("symbol") or "").strip().upper()
        if not symbol or symbol == ticker:
            continue
        try:
            bundle = company_service.get_bundle(symbol, db, provider)
        except Exception as exc:  # per-peer: skip + warning, never fail the table
            warnings.append(f"Peer {symbol} skipped: {exc}")
            continue
        peers.append(
            _build_row(
                symbol,
                str(raw.get("name") or bundle.info.name),
                raw.get("mktCap"),
                raw.get("price"),
                bundle,
            )
        )

    return PeersResponse(
        ticker=ticker,
        as_of=datetime.now(timezone.utc).isoformat(),
        peer_source=peer_source,
        target=target,
        peers=peers,
        stats=_stats(peers),
        warnings=warnings,
    )
