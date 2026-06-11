"""Currency contract helpers (spec §4).

`MarketData.currency` is the quote currency after normalization (GBp quotes
are converted to GBP upstream); `CompanyDataBundle.currency` is the financial
reporting currency. `None` means a legacy/sample payload and is treated as
USD. When the two differ, mixed-currency figures (EV, EV-based multiples,
P/E, FCF yield, premium vs current) are suppressed — there is no FX
conversion in the MVP.
"""

from __future__ import annotations

from app.schemas.company import CompanyDataBundle

DEFAULT_CURRENCY = "USD"


def reporting_currency(bundle: CompanyDataBundle) -> str:
    """Financial reporting currency of the bundle (None ≡ USD)."""
    return (bundle.currency or DEFAULT_CURRENCY).upper()


def quote_currency(bundle: CompanyDataBundle) -> str:
    """Normalized quote currency of the bundle's market data (None ≡ USD)."""
    market = bundle.market
    if market is None or not market.currency:
        return DEFAULT_CURRENCY
    return market.currency.upper()


def currency_mismatch_warning(bundle: CompanyDataBundle) -> str | None:
    """The exact spec §4 warning when quote and reporting currencies differ.

    Returns None when they match (the normal, single-currency case).
    """
    quote = quote_currency(bundle)
    reporting = reporting_currency(bundle)
    if quote == reporting:
        return None
    return (
        f"Quote currency ({quote}) differs from reporting currency "
        f"({reporting}); mixed currency multiples suppressed "
        "(no FX conversion in MVP)"
    )
