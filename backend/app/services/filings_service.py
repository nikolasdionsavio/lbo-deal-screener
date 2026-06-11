"""SEC filings retrieval for the API and memo (spec §19.3).

Filings come from EDGAR only, so they exist in live mode for US filers:
- mock mode (or no SEC_EDGAR_USER_AGENT configured) -> 200 with an empty list
  plus the live-only warning, no network traffic;
- unresolvable tickers (sample tickers, non-US listings) -> same empty + warning;
- EDGAR failures raise ProviderError (routes map to 502), except on the
  best-effort memo path, which never raises.
"""

from __future__ import annotations

from app.core.config import Settings
from app.core.config import settings as global_settings
from app.providers.base import DataProvider
from app.providers.edgar_filings import EdgarFilingsProvider
from app.providers.exceptions import CompanyNotFoundError
from app.providers.mock import MockProvider
from app.schemas.filings import Filing, FilingsResponse

LIVE_ONLY_WARNING = "Filings are available in live mode for US filers only."


def _build_filings_provider(app_settings: Settings) -> EdgarFilingsProvider:
    """Factory split out so tests can monkeypatch in a MockTransport client."""
    return EdgarFilingsProvider(app_settings.sec_edgar_user_agent)


def _empty(ticker: str) -> FilingsResponse:
    return FilingsResponse(ticker=ticker, warnings=[LIVE_ONLY_WARNING])


def get_filings(
    ticker: str,
    provider: DataProvider,
    app_settings: Settings | None = None,
    filings_provider: EdgarFilingsProvider | None = None,
) -> FilingsResponse:
    """Latest §19.3 filings; empty + warning when EDGAR cannot serve them.

    Raises ProviderError on EDGAR failures (routes map to 502).
    """
    app_settings = app_settings or global_settings
    ticker = ticker.strip().upper()

    if filings_provider is None:
        if isinstance(provider, MockProvider):
            return _empty(ticker)  # sample tickers have no CIK; skip the network
        if not app_settings.sec_edgar_user_agent.strip():
            return _empty(ticker)
        filings_provider = _build_filings_provider(app_settings)

    try:
        cik, filings = filings_provider.get_filings(ticker)
    except CompanyNotFoundError:
        return _empty(ticker)  # not in the EDGAR ticker map (non-US / mock ticker)
    return FilingsResponse(ticker=ticker, cik=cik, filings=filings)


def get_filings_for_memo(
    ticker: str,
    provider: DataProvider,
    app_settings: Settings | None = None,
) -> list[Filing] | None:
    """Best-effort filings for memo links — failures never break the memo."""
    try:
        return get_filings(ticker, provider, app_settings).filings
    except Exception:
        return None
