"""Provider exceptions (spec §5)."""


class ProviderError(Exception):
    """A data provider failed (network, upstream error, bad payload).

    Routes map this to HTTP 502 with a human-readable message.
    """


class CompanyNotFoundError(ProviderError):
    """The requested ticker is unknown to the provider (HTTP 404)."""


class ProviderConfigError(ProviderError):
    """The provider is misconfigured (e.g. missing SEC_EDGAR_USER_AGENT)."""
