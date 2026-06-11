"""YahooProvider: global live coverage (US + UK + EU) via yfinance (spec §5).

yfinance talks to UNOFFICIAL Yahoo Finance endpoints — chosen because no
official API offers free US+UK+EU fundamentals. Every bundle therefore
carries an explicit warning to verify figures against filings.

- search: yfinance Search (Lookup fallback), equities only, top 8.
- fundamentals: Ticker.income_stmt / .balance_sheet / .cashflow (annual)
  mapped to FiscalYearFinancials via row-label preference lists (first label
  with data wins). Fiscal year = column end-date year. Missing rows -> None
  plus a warning. §4 normalization (derive gross profit / EBITDA / FCF) is
  applied after mapping.
- market/profile: Ticker.info with GBp normalization (price / 100 -> "GBP")
  and a market-cap cross-check: when the reported market cap disagrees with
  share_price × shares_outstanding by more than 5%, the computed value wins
  and a warning is recorded.
- reporting currency: Ticker.info["financialCurrency"].
- errors: unknown symbols (empty frames AND no market/profile data) raise
  CompanyNotFoundError; rate limits and network failures raise ProviderError
  with readable messages. No URLs or tracebacks in messages.

yfinance is imported lazily so the app still imports (and mock/live modes
still work) when the package is not installed. Tests inject a fake module
via the ``yf_module`` constructor argument — pytest must never hit the live
network.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.normalization import normalize_financials
from app.providers.base import DataProvider
from app.providers.exceptions import (
    CompanyNotFoundError,
    ProviderConfigError,
    ProviderError,
)
from app.schemas.company import (
    CompanyDataBundle,
    CompanyInfo,
    MarketData,
    SearchResult,
)
from app.schemas.financials import FiscalYearFinancials

DATA_SOURCE = "Yahoo Finance (unofficial endpoints, via yfinance)"
UNOFFICIAL_ENDPOINTS_WARNING = (
    "Data from unofficial Yahoo Finance endpoints; verify figures against "
    "filings before relying on them."
)
MARKET_CAP_CROSS_CHECK_TOLERANCE = 0.05
_MAX_YEARS = 5
_MAX_SEARCH_RESULTS = 8

# Row-label preference lists per spec §5 — first label with annual data wins.
INCOME_ROW_PREFERENCES: dict[str, list[str]] = {
    "revenue": ["Total Revenue"],
    "cost_of_revenue": ["Cost Of Revenue"],
    "gross_profit": ["Gross Profit"],
    "operating_income": ["Operating Income"],
    "interest_expense": ["Interest Expense"],
    "tax_expense": ["Tax Provision"],
    "net_income": ["Net Income"],
}
CASHFLOW_ROW_PREFERENCES: dict[str, list[str]] = {
    "depreciation_amortization": [
        "Depreciation Amortization Depletion",
        "Depreciation And Amortization",
        "Depreciation",
    ],
    "operating_cash_flow": [
        "Operating Cash Flow",
        "Cash Flow From Continuing Operating Activities",
    ],
    "capex": ["Capital Expenditure"],  # stored positive (abs)
}
BALANCE_ROW_PREFERENCES: dict[str, list[str]] = {
    "cash_and_equivalents": [
        "Cash And Cash Equivalents",
        "Cash Cash Equivalents And Short Term Investments",
    ],
    "current_assets": ["Current Assets"],
    "current_liabilities": ["Current Liabilities"],
    "total_equity": ["Stockholders Equity", "Common Stock Equity"],
}
_ABS_VALUE_FIELDS = {"capex", "interest_expense"}

TOTAL_DEBT_ROW = "Total Debt"
TOTAL_DEBT_COMPONENT_ROWS = ["Long Term Debt", "Current Debt"]


def _import_yfinance() -> Any:
    """Import yfinance lazily; raise a readable config error when absent."""
    try:
        import yfinance
    except ImportError as exc:
        raise ProviderConfigError(
            "The yfinance package is required for the Yahoo Finance provider; "
            "install it with 'pip install yfinance'."
        ) from exc
    return yfinance


def _transport_failure_message(exc: Exception) -> str | None:
    """Readable message for rate-limit / network failures, else None.

    Other exceptions (yfinance quirks for unknown symbols, parsing issues)
    are treated as missing data so the empty-everything check can raise
    CompanyNotFoundError instead.
    """
    name = type(exc).__name__
    text = str(exc).lower()
    if "ratelimit" in name.lower() or "429" in text or "too many requests" in text:
        return (
            "Yahoo Finance rate limited the request; wait a few minutes and "
            "try again."
        )
    if (
        "timeout" in name.lower()
        or "connection" in name.lower()
        or isinstance(exc, (ConnectionError, TimeoutError, OSError))
    ):
        return f"could not reach Yahoo Finance ({name})."
    return None


def _to_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result else None  # NaN -> None


class YahooProvider(DataProvider):
    name = "yahoo"

    def __init__(self, *, yf_module: Any | None = None) -> None:
        # Tests inject a fake module; production resolves yfinance lazily.
        self._yf_module = yf_module

    def _yf(self) -> Any:
        if self._yf_module is None:
            self._yf_module = _import_yfinance()
        return self._yf_module

    # ----- guarded yfinance access -----

    def _fetch(self, getter: Any, what: str) -> Any:
        """Run a yfinance call; map transport failures to ProviderError.

        Non-transport exceptions return None (missing data) — unknown symbols
        surface as empty frames/dicts rather than errors in yfinance.
        """
        try:
            return getter()
        except ProviderError:
            raise
        except Exception as exc:  # yfinance raises a wide exception surface
            message = _transport_failure_message(exc)
            if message is not None:
                raise ProviderError(f"{what} failed: {message}") from None
            return None

    # ----- DataProvider interface -----

    def search(self, query: str) -> list[SearchResult]:
        q = query.strip()
        if not q:
            return []
        yf = self._yf()
        quotes = self._fetch(
            lambda: getattr(yf.Search(q, max_results=_MAX_SEARCH_RESULTS), "quotes", []),
            what=f"Yahoo Finance search for '{q}'",
        )
        if not quotes and hasattr(yf, "Lookup"):
            quotes = self._fetch(
                lambda: self._lookup_quotes(yf, q),
                what=f"Yahoo Finance lookup for '{q}'",
            )
        results: list[SearchResult] = []
        for record in quotes or []:
            if not isinstance(record, dict):
                continue
            if str(record.get("quoteType", "")).upper() != "EQUITY":
                continue
            symbol = record.get("symbol")
            if not symbol:
                continue
            results.append(
                SearchResult(
                    ticker=str(symbol),
                    name=str(
                        record.get("shortname")
                        or record.get("longname")
                        or record.get("shortName")
                        or record.get("longName")
                        or symbol
                    ),
                    exchange=record.get("exchDisp")
                    or record.get("exchange")
                    or None,
                    source=self.name,
                )
            )
            if len(results) >= _MAX_SEARCH_RESULTS:
                break
        return results

    @staticmethod
    def _lookup_quotes(yf: Any, query: str) -> list[dict[str, Any]]:
        """Equity quotes from yfinance Lookup, shaped like Search quotes."""
        frame = yf.Lookup(query).get_stock(count=_MAX_SEARCH_RESULTS)
        if frame is None or getattr(frame, "empty", True):
            return []
        quotes: list[dict[str, Any]] = []
        for symbol, row in frame.iterrows():
            quotes.append(
                {
                    "symbol": str(symbol),
                    "shortname": row.get("shortName"),
                    "exchDisp": row.get("exchange"),
                    "quoteType": "EQUITY",
                }
            )
        return quotes

    def get_company(self, ticker: str) -> CompanyDataBundle:
        symbol = ticker.strip().upper()
        if not symbol:
            raise CompanyNotFoundError("A ticker symbol is required.")
        yf = self._yf()
        t = self._fetch(
            lambda: yf.Ticker(symbol), what=f"Yahoo Finance ticker {symbol}"
        )
        if t is None:
            raise CompanyNotFoundError(
                f"Ticker '{symbol}' was not found on Yahoo Finance."
            )
        warnings: list[str] = [UNOFFICIAL_ENDPOINTS_WARNING]

        what = f"Yahoo Finance data for {symbol}"
        income = self._fetch(lambda: t.income_stmt, what)
        balance = self._fetch(lambda: t.balance_sheet, what)
        cashflow = self._fetch(lambda: t.cashflow, what)
        info = self._fetch(lambda: t.info, what)
        info = info if isinstance(info, dict) else {}

        years = self._map_financials(income, balance, cashflow, warnings)
        market, company_info = self._market_and_profile(symbol, info, warnings)

        if not years and market is None:
            raise CompanyNotFoundError(
                f"Ticker '{symbol}' was not found on Yahoo Finance (no "
                "fundamentals or market data returned)."
            )
        if not years:
            warnings.append(
                "No annual financial statements available from Yahoo Finance "
                "for this company."
            )

        return CompanyDataBundle(
            info=company_info,
            market=market,
            financials=years,
            currency=(info.get("financialCurrency") or None),
            data_source=DATA_SOURCE,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            warnings=warnings,
        )

    def refresh_market(self, ticker: str) -> MarketData | None:
        """Light-weight quote refresh for §11 cache hits (fast_info, then info)."""
        symbol = ticker.strip().upper()
        yf = self._yf()
        t = self._fetch(
            lambda: yf.Ticker(symbol), what=f"Yahoo Finance ticker {symbol}"
        )
        if t is None:
            return None
        what = f"Yahoo Finance quote refresh for {symbol}"
        fast = self._fetch(lambda: t.fast_info, what)
        price = _to_float(self._attr(fast, "last_price", "lastPrice"))
        market_cap = _to_float(self._attr(fast, "market_cap", "marketCap"))
        shares = _to_float(self._attr(fast, "shares"))
        currency = self._attr(fast, "currency")
        if price is None and market_cap is None:
            info = self._fetch(lambda: t.info, what)
            info = info if isinstance(info, dict) else {}
            price = _to_float(info.get("currentPrice")) or _to_float(
                info.get("regularMarketPrice")
            )
            market_cap = _to_float(info.get("marketCap"))
            shares = shares or _to_float(info.get("sharesOutstanding"))
            currency = currency or info.get("currency")
        if price is None and market_cap is None:
            return None
        price, currency = _normalize_gbp_pence(price, currency)
        market_cap = self._cross_checked_market_cap(
            market_cap, price, shares, warnings=None
        )
        return MarketData(
            share_price=price,
            market_cap=market_cap,
            shares_outstanding=shares,
            as_of=datetime.now(timezone.utc).date().isoformat(),
            source=DATA_SOURCE,
            currency=(str(currency).upper() if currency else None),
        )

    @staticmethod
    def _attr(obj: Any, *names: str) -> Any:
        """First available attribute or mapping key from fast_info-like objects."""
        if obj is None:
            return None
        for name in names:
            value = getattr(obj, name, None)
            if value is None and hasattr(obj, "get"):
                try:
                    value = obj.get(name)
                except Exception:
                    value = None
            if value is not None:
                return value
        return None

    # ----- fundamentals mapping -----

    def _map_financials(
        self,
        income: Any,
        balance: Any,
        cashflow: Any,
        warnings: list[str],
    ) -> list[FiscalYearFinancials]:
        """Map the three annual statements to FiscalYearFinancials rows."""
        if all(
            frame is None or getattr(frame, "empty", True)
            for frame in (income, balance, cashflow)
        ):
            # No statements at all (unknown symbol or fund): one summary
            # warning is added by the caller instead of 15 per-field ones.
            return []
        field_series: dict[str, dict[Any, float]] = {}
        for frame, preferences in (
            (income, INCOME_ROW_PREFERENCES),
            (cashflow, CASHFLOW_ROW_PREFERENCES),
            (balance, BALANCE_ROW_PREFERENCES),
        ):
            for field, labels in preferences.items():
                values = _first_row_with_data(frame, labels)
                if values is None:
                    warnings.append(f"{field} unavailable from Yahoo Finance")
                    values = {}
                if field in _ABS_VALUE_FIELDS:
                    values = {col: abs(v) for col, v in values.items()}
                field_series[field] = values

        field_series["total_debt"] = self._total_debt_series(balance, warnings)

        all_columns = {
            col for series in field_series.values() for col in series
        }
        rows: list[FiscalYearFinancials] = []
        for col in sorted(all_columns, key=_column_sort_key):
            fiscal_year, period_end = _column_period(col)
            if fiscal_year is None:
                continue
            row = FiscalYearFinancials(fiscal_year=fiscal_year, period_end=period_end)
            for field, series in field_series.items():
                if col in series:
                    setattr(row, field, series[col])
            rows.append(row)
        # Ascending fiscal_year; a later period-end wins same-year collisions.
        by_year: dict[int, FiscalYearFinancials] = {}
        for row in rows:
            by_year[row.fiscal_year] = row
        years = [by_year[fy] for fy in sorted(by_year)][-_MAX_YEARS:]
        return normalize_financials(years)

    @staticmethod
    def _total_debt_series(balance: Any, warnings: list[str]) -> dict[Any, float]:
        """Per-period total debt: "Total Debt", else Long Term + Current Debt."""
        total = _first_row_with_data(balance, [TOTAL_DEBT_ROW])
        if total is not None:
            return total
        components = [
            _first_row_with_data(balance, [label]) or {}
            for label in TOTAL_DEBT_COMPONENT_ROWS
        ]
        columns = {col for series in components for col in series}
        if columns:
            return {
                col: sum(series[col] for series in components if col in series)
                for col in columns
            }
        warnings.append("total_debt unavailable from Yahoo Finance")
        return {}

    # ----- market / profile -----

    def _market_and_profile(
        self, symbol: str, info: dict[str, Any], warnings: list[str]
    ) -> tuple[MarketData | None, CompanyInfo]:
        company_info = CompanyInfo(
            ticker=symbol,
            name=str(
                info.get("longName") or info.get("shortName") or symbol
            ),
            sector=info.get("sector") or None,
            industry=info.get("industry") or None,
            exchange=info.get("fullExchangeName") or info.get("exchange") or None,
            description=info.get("longBusinessSummary") or None,
        )

        price = _to_float(info.get("currentPrice"))
        if price is None:
            price = _to_float(info.get("regularMarketPrice"))
        market_cap = _to_float(info.get("marketCap"))
        shares = _to_float(info.get("sharesOutstanding"))
        currency = info.get("currency") or None

        if price is None and market_cap is None and shares is None:
            warnings.append("Market data unavailable from Yahoo Finance")
            return None, company_info

        price, currency = _normalize_gbp_pence(price, currency)
        market_cap = self._cross_checked_market_cap(
            market_cap, price, shares, warnings
        )
        market = MarketData(
            share_price=price,
            market_cap=market_cap,
            shares_outstanding=shares,
            as_of=datetime.now(timezone.utc).date().isoformat(),
            source=DATA_SOURCE,
            currency=(str(currency).upper() if currency else None),
        )
        return market, company_info

    @staticmethod
    def _cross_checked_market_cap(
        reported: float | None,
        price: float | None,
        shares: float | None,
        warnings: list[str] | None,
    ) -> float | None:
        """Spec §4 cross-check: computed price × shares wins when >5% apart."""
        if price is None or not shares:
            return reported
        computed = price * shares
        if reported is None or reported <= 0:
            return computed
        if abs(computed - reported) / reported > MARKET_CAP_CROSS_CHECK_TOLERANCE:
            if warnings is not None:
                warnings.append(
                    "Reported market cap differs from share price × shares "
                    "outstanding by more than 5%; using the computed value."
                )
            return computed
        return reported


def _normalize_gbp_pence(
    price: float | None, currency: Any
) -> tuple[float | None, Any]:
    """Yahoo quotes LSE stocks in pence ("GBp"): price / 100, currency GBP.

    Only the literal pence code "GBp" (or "GBX") triggers the division; the
    ISO code "GBP" already means pounds and must pass through untouched.
    """
    if isinstance(currency, str) and currency.strip() in ("GBp", "GBX"):
        return (price / 100.0 if price is not None else None), "GBP"
    return price, currency


def _first_row_with_data(frame: Any, labels: list[str]) -> dict[Any, float] | None:
    """First preference label present in the frame with at least one value.

    Returns {column -> float} (NaN cells dropped) or None when no label has
    data. Tolerates None / empty frames.
    """
    if frame is None or getattr(frame, "empty", True):
        return None
    for label in labels:
        try:
            if label not in frame.index:
                continue
            series = frame.loc[label]
        except (KeyError, TypeError, ValueError):
            continue
        # Duplicate row labels yield a DataFrame; take the first row.
        if hasattr(series, "iloc") and getattr(series, "ndim", 1) > 1:
            series = series.iloc[0]
        values: dict[Any, float] = {}
        for col in series.index:
            value = _to_float(series[col])
            if value is not None:
                values[col] = value
        if values:
            return values
    return None


def _column_period(col: Any) -> tuple[int | None, str | None]:
    """(fiscal_year, period_end ISO date) from a statement column label."""
    year = getattr(col, "year", None)
    if year is not None:
        date_obj = col.date() if hasattr(col, "date") else None
        return int(year), (date_obj.isoformat() if date_obj else str(col)[:10])
    text = str(col)
    if len(text) >= 4 and text[:4].isdigit():
        return int(text[:4]), (text[:10] if len(text) >= 10 else None)
    return None, None


def _column_sort_key(col: Any) -> str:
    return str(col)
