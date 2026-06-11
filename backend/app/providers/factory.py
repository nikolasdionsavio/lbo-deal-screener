"""Provider factory honoring DATA_PROVIDER=auto|mock|live (spec §5).

- mock -> MockProvider.
- live -> CompositeLiveProvider; raises ProviderConfigError when
  SEC_EDGAR_USER_AGENT is missing.
- auto -> live when SEC_EDGAR_USER_AGENT is set, else MockProvider whose
  bundles carry MOCK_MODE_WARNING so every page can surface the active mode.
"""

from app.core.config import Settings
from app.providers.base import DataProvider
from app.providers.edgar import SecEdgarProvider
from app.providers.exceptions import ProviderConfigError
from app.providers.fmp import FmpProvider
from app.providers.live import CompositeLiveProvider
from app.providers.mock import MockProvider

MOCK_MODE_WARNING = (
    "Using bundled sample data; set SEC_EDGAR_USER_AGENT and FMP_API_KEY "
    "for live data."
)


def _build_live(settings: Settings) -> CompositeLiveProvider:
    edgar = SecEdgarProvider(settings.sec_edgar_user_agent)
    fmp = FmpProvider(settings.fmp_api_key) if settings.fmp_api_key.strip() else None
    return CompositeLiveProvider(edgar, fmp)


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
    if mode == "auto":
        if settings.sec_edgar_user_agent.strip():
            return _build_live(settings)
        return MockProvider(extra_warnings=[MOCK_MODE_WARNING])
    raise ProviderConfigError(f"Unknown DATA_PROVIDER mode: {mode!r}.")
