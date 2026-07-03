"""Market-statistics schemas: a Bloomberg-style read (analyst view, ownership,
dividends, key stats) assembled from a single Yahoo Finance ``.info`` fetch.

Every field is optional: Yahoo populates these richly for large-cap US names and
sparsely for small / foreign listings, so the UI shows honest "unavailable"
states rather than fabricating coverage. Monetary fields are in the quote
currency (``currency``); rates are decimals (0.012 = 1.2%).
"""

from __future__ import annotations

from pydantic import BaseModel


class AnalystView(BaseModel):
    """Sell-side ratings, price targets and forward estimates (ANR / EE).

    Coverage is thin outside large-cap US: Yahoo aggregates broker research
    that is proprietary on Bloomberg, so these are best-effort and clearly
    labelled coverage-dependent in the UI.
    """

    rating: str | None = None  # recommendationKey, e.g. "buy"
    rating_score: float | None = None  # recommendationMean (1 strong buy .. 5 sell)
    analyst_count: int | None = None  # numberOfAnalystOpinions
    target_mean: float | None = None
    target_high: float | None = None
    target_low: float | None = None
    current_price: float | None = None
    implied_upside: float | None = None  # target_mean / current_price - 1
    forward_pe: float | None = None
    forward_eps: float | None = None
    trailing_eps: float | None = None
    earnings_growth: float | None = None  # expected, decimal
    revenue_growth: float | None = None  # decimal
    next_earnings_date: str | None = None  # ISO date (ERN)


class OwnershipView(BaseModel):
    """Institutional / insider ownership and short interest (HDS).

    Free data's strength for US filers: sourced from SEC 13F / Forms 3-4-5 that
    Yahoo wraps. No equivalent for non-US names.
    """

    held_pct_institutions: float | None = None  # decimal
    held_pct_insiders: float | None = None  # decimal
    float_shares: float | None = None
    shares_outstanding: float | None = None
    shares_short: float | None = None
    short_pct_of_float: float | None = None  # decimal
    short_pct_shares_out: float | None = None  # decimal
    short_ratio: float | None = None  # days to cover


class DividendView(BaseModel):
    """Dividend rate, yield, payout and ex-date (DVD)."""

    dividend_rate: float | None = None  # annual, per share
    dividend_yield: float | None = None  # decimal
    payout_ratio: float | None = None  # decimal
    five_year_avg_yield: float | None = None  # decimal
    ex_dividend_date: str | None = None  # ISO date
    last_dividend_value: float | None = None  # per share


class KeyStats(BaseModel):
    """Snapshot valuation, profitability and price statistics (DES tail)."""

    beta: float | None = None
    trailing_pe: float | None = None
    price_to_book: float | None = None
    ev_to_ebitda: float | None = None
    ev_to_revenue: float | None = None
    profit_margin: float | None = None  # decimal
    return_on_equity: float | None = None  # decimal
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    fifty_two_week_change: float | None = None  # decimal, price return
    sp_fifty_two_week_change: float | None = None  # S&P 500 same-window return
    fifty_day_average: float | None = None
    two_hundred_day_average: float | None = None


class MarketStats(BaseModel):
    ticker: str
    currency: str | None = None
    as_of: str
    source: str
    analysts: AnalystView
    ownership: OwnershipView
    dividends: DividendView
    stats: KeyStats
    warnings: list[str] = []
