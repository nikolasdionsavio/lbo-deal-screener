"""Provider factory honoring DATA_PROVIDER=auto|mock|live|yahoo (spec §5).

- mock  -> MockProvider.
- live  -> CompositeLiveProvider; raises ProviderConfigError when
  SEC_EDGAR_USER_AGENT is missing.
- yahoo -> YahooCompositeProvider (global coverage, no key required); raises
  ProviderConfigError only when yfinance is not importable. EDGAR enrichment
  for US-style tickers activates automatically when SEC_EDGAR_USER_AGENT is set.
- auto  -> yahoo when yfinance imports, else live when SEC_EDGAR_USER_AGENT is
  set, else MockProvider whose bundles carry MOCK_MODE_WARNING so every page
  can surface the active mode.
"""

import importlib.util

from app.core.config import Settings
from app.providers.base import DataProvider
from app.providers.edgar import SecEdgarProvider
from app.providers.exceptions import ProviderConfigError
from app.providers.fmp import FmpProvider
from app.providers.live import CompositeLiveProvider
from app.providers.mock import MockProvider
from app.providers.yahoo import YahooProvider
from app.providers.yahoo_composite import YahooCompositeProvider

MOCK_MODE_WARNING = (
    "Using bundled sample data; set SEC_EDGAR_USER_AGENT and FMP_API_KEY "
    "for live data."
)


def _yfinance_importable() -> bool:
    """True when the yfinance package can be imported (without importing it)."""
    try:
        return importlib.util.find_spec("yfinance") is not None
    except (ImportError, ValueError):
        return False


def _build_live(settings: Settings) -> CompositeLiveProvider:
    edgar = SecEdgarProvider(settings.sec_edgar_user_agent)
    fmp = FmpProvider(settings.fmp_api_key) if settings.fmp_api_key.strip() else None
    return CompositeLiveProvider(edgar, fmp)


def _build_yahoo(settings: Settings) -> YahooCompositeProvider:
    edgar = (
        SecEdgarProvider(settings.sec_edgar_user_agent)
        if settings.sec_edgar_user_agent.strip()
        else None
    )
    return YahooCompositeProvider(YahooProvider(), edgar)


def get_provider(settings: Settings) -> DataProvider:
    mode = settings.data_provider
    if mode == "mock":
        return MockProvider()
    if mode == "live":
        if not settings.sec_edgar_user_agent.strip():
            raise ProviderConfigError(
                "DATA_PROVIDER=live requires SEC_EDGAR_USER_AGENT to be set "
                "(e.g. 'Your Name your.email@example.com')."
            )
        return _build_live(settings)
    if mode == "yahoo":
        if not _yfinance_importable():
            raise ProviderConfigError(
                "DATA_PROVIDER=yahoo requires the yfinance package; install "
                "it with 'pip install yfinance'."
            )
        return _build_yahoo(settings)
    if mode == "auto":
        if _yfinance_importable():
            return _build_yahoo(settings)
        if settings.sec_edgar_user_agent.strip():
            return _build_live(settings)
        return MockProvider(extra_warnings=[MOCK_MODE_WARNING])
    raise ProviderConfigError(f"Unknown DATA_PROVIDER mode: {mode!r}.")
