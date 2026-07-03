"""Bloomberg-style market statistics from a single Yahoo Finance ``.info`` fetch.

Covers the analyst view (ANR / EE / ERN), ownership (HDS), dividends (DVD) and a
key-stats snapshot — the Bloomberg equity functions the app did not yet surface.
Deliberately independent of the provider abstraction: it is one best-effort
``.info`` read, cached briefly to spare Yahoo's unofficial endpoints, and every
field degrades to None so small / foreign names show honest "unavailable" states.

``_fetch_info`` is module-level so tests stub it (pytest must never hit the live
network).
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from app.schemas.market_stats import (
    AnalystView,
    DividendView,
    KeyStats,
    MarketStats,
    OwnershipView,
)

DATA_SOURCE = "Yahoo Finance (unofficial endpoints, via yfinance)"
_TTL_SECONDS = 900  # 15-minute in-process cache
_PENCE_CODES = {"GBp", "GBX"}

# ticker -> (fetched_at_epoch, MarketStats | None)
_CACHE: dict[str, tuple[float, MarketStats | None]] = {}


def _fetch_info(ticker: str) -> dict[str, Any] | None:
    """Best-effort ``yfinance.Ticker(ticker).info``; None on any failure.

    Lazy import keeps yfinance optional; module-level so tests stub it.
    """
    try:
        import yfinance  # lazy: optional dependency
    except ImportError:
        return None
    try:
        info = yfinance.Ticker(ticker).info
    except Exception:  # unofficial endpoints fail in many shapes
        return None
    return info if isinstance(info, dict) else None


def _f(value: Any) -> float | None:
    """Float or None (NaN, non-numeric and infinities collapse to None)."""
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if result != result or result in (float("inf"), float("-inf")):
        return None
    return result


def _int(value: Any) -> int | None:
    f = _f(value)
    return int(f) if f is not None else None


def _epoch_to_date(value: Any) -> str | None:
    """Unix-seconds timestamp -> ISO date; None when absent or invalid."""
    ts = _f(value)
    if ts is None or ts <= 0:
        return None
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def get_market_stats(ticker: str) -> MarketStats | None:
    """Cached market stats for a ticker.

    Always returns a MarketStats for a non-empty ticker: when the live feed
    returns nothing (e.g. Yahoo rate-limits the request from a datacenter IP),
    the fields are null and a warning names the gap, so the pages show honest
    "unavailable" states rather than a hard error. None only for an empty ticker.
    """
    key = ticker.strip().upper()
    if not key:
        return None
    now = time.time()
    cached = _CACHE.get(key)
    if cached is not None and now - cached[0] < _TTL_SECONDS:
        return cached[1]
    info = _fetch_info(key)
    stats = _build(key, info if isinstance(info, dict) else {})
    _CACHE[key] = (now, stats)
    return stats


def reset_cache() -> None:
    """Clear the in-process cache (tests)."""
    _CACHE.clear()


def _build(ticker: str, info: dict[str, Any]) -> MarketStats:
    warnings: list[str] = []
    if not info:
        # The live feed returned nothing (commonly Yahoo rate-limiting the
        # request from a datacenter IP). Return an empty-but-valid snapshot so
        # the pages render honest "unavailable" states.
        return MarketStats(
            ticker=ticker,
            currency=None,
            as_of=datetime.now(timezone.utc).date().isoformat(),
            source=DATA_SOURCE,
            analysts=AnalystView(),
            ownership=OwnershipView(),
            dividends=DividendView(),
            stats=KeyStats(),
            warnings=[
                "Live analyst, ownership and dividend figures are unavailable "
                "for this company right now (the market-data feed returned no "
                "data)."
            ],
        )
    currency = info.get("currency") or None
    pence = isinstance(currency, str) and currency.strip() in _PENCE_CODES

    def price(*keys: str) -> float | None:
        """A price-per-share field, normalised from pence to pounds on the LSE."""
        for k in keys:
            v = _f(info.get(k))
            if v is not None:
                return v / 100.0 if pence else v
        return None

    current_price = price("currentPrice", "regularMarketPrice")
    target_mean = price("targetMeanPrice")
    implied_upside = (
        target_mean / current_price - 1.0
        if target_mean is not None and current_price not in (None, 0)
        else None
    )

    analysts = AnalystView(
        rating=(info.get("recommendationKey") or None),
        rating_score=_f(info.get("recommendationMean")),
        analyst_count=_int(info.get("numberOfAnalystOpinions")),
        target_mean=target_mean,
        target_high=price("targetHighPrice"),
        target_low=price("targetLowPrice"),
        current_price=current_price,
        implied_upside=implied_upside,
        forward_pe=_f(info.get("forwardPE")),
        forward_eps=price("forwardEps"),
        trailing_eps=price("trailingEps"),
        earnings_growth=_f(info.get("earningsGrowth")),
        revenue_growth=_f(info.get("revenueGrowth")),
        next_earnings_date=_epoch_to_date(info.get("earningsTimestamp")),
    )

    ownership = OwnershipView(
        held_pct_institutions=_f(info.get("heldPercentInstitutions")),
        held_pct_insiders=_f(info.get("heldPercentInsiders")),
        float_shares=_f(info.get("floatShares")),
        shares_outstanding=_f(info.get("sharesOutstanding")),
        shares_short=_f(info.get("sharesShort")),
        short_pct_of_float=_f(info.get("shortPercentOfFloat")),
        short_pct_shares_out=_f(info.get("sharesPercentSharesOut")),
        short_ratio=_f(info.get("shortRatio")),
    )

    # yfinance's dividendYield unit has drifted over time (decimal vs percent),
    # so derive the yield from rate / price when possible (both already
    # currency-normalised); fall back to the reported field otherwise.
    dividend_rate = price("dividendRate")
    if dividend_rate is not None and current_price not in (None, 0):
        dividend_yield = dividend_rate / current_price
    else:
        dividend_yield = _normalize_yield(info.get("dividendYield"))

    dividends = DividendView(
        dividend_rate=dividend_rate,
        dividend_yield=dividend_yield,
        payout_ratio=_f(info.get("payoutRatio")),
        five_year_avg_yield=_pct_to_decimal(info.get("fiveYearAvgDividendYield")),
        ex_dividend_date=_epoch_to_date(info.get("exDividendDate")),
        last_dividend_value=price("lastDividendValue"),
    )

    stats = KeyStats(
        beta=_f(info.get("beta")),
        trailing_pe=_f(info.get("trailingPE")),
        price_to_book=_f(info.get("priceToBook")),
        ev_to_ebitda=_f(info.get("enterpriseToEbitda")),
        ev_to_revenue=_f(info.get("enterpriseToRevenue")),
        profit_margin=_f(info.get("profitMargins")),
        return_on_equity=_f(info.get("returnOnEquity")),
        fifty_two_week_high=price("fiftyTwoWeekHigh"),
        fifty_two_week_low=price("fiftyTwoWeekLow"),
        fifty_two_week_change=_f(info.get("52WeekChange")),
        sp_fifty_two_week_change=_f(info.get("SandP52WeekChange")),
        fifty_day_average=price("fiftyDayAverage"),
        two_hundred_day_average=price("twoHundredDayAverage"),
    )

    if analysts.target_mean is None and analysts.analyst_count is None:
        warnings.append(
            "Analyst coverage is unavailable for this company (common outside "
            "large-cap US names)."
        )

    return MarketStats(
        ticker=ticker,
        currency=("GBP" if pence else (str(currency).upper() if currency else None)),
        as_of=datetime.now(timezone.utc).date().isoformat(),
        source=DATA_SOURCE,
        analysts=analysts,
        ownership=ownership,
        dividends=dividends,
        stats=stats,
        warnings=warnings,
    )


def _pct_to_decimal(value: Any) -> float | None:
    """A percentage reported as a number (1.2 -> 0.012)."""
    v = _f(value)
    return v / 100.0 if v is not None else None


def _normalize_yield(value: Any) -> float | None:
    """Dividend yield to a decimal, tolerating Yahoo's percent/decimal drift."""
    v = _f(value)
    if v is None:
        return None
    return v / 100.0 if v > 1.0 else v
