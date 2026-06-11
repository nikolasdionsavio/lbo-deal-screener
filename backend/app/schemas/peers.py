"""Peer comparables schemas (spec §19.2)."""

from pydantic import BaseModel, Field

# Metrics summarised by interpolated quartile stats (spec §19.2).
PEER_STAT_METRICS = ("ev_ebitda", "ev_revenue", "pe", "ebitda_margin")


class PeerRow(BaseModel):
    """One company (target or peer) in the comparables table."""

    ticker: str
    name: str
    market_cap: float | None = None
    enterprise_value: float | None = None
    ev_ebitda: float | None = None
    ev_revenue: float | None = None
    pe: float | None = None
    ebitda_margin: float | None = None
    revenue_growth_yoy: float | None = None
    currency: str | None = None
    warnings: list[str] = Field(default_factory=list)


class PeerStats(BaseModel):
    """Interpolated five-number summary over valued peers (target excluded)."""

    min: float
    q1: float
    median: float
    q3: float
    max: float


class PeersResponse(BaseModel):
    """Response for GET /api/companies/{ticker}/peers (spec §19.2)."""

    ticker: str
    as_of: str
    peer_source: str | None = None
    target: PeerRow
    peers: list[PeerRow] = Field(default_factory=list)
    stats: dict[str, PeerStats] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
