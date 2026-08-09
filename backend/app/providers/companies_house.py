"""UK Companies House provider: search, profile, filings, and parsed accounts.

Wraps the free Companies House REST + document APIs. Auth is HTTP Basic with the
API key as the username and an empty password. The public REST API does NOT
return financial figures, so `latest_accounts` locates the most recent accounts
filing, downloads its iXBRL document, and parses it with `ixbrl.parse_ixbrl_accounts`.

Honest scope (per DESIGN.md / research):
- There is no financial-figure SEARCH endpoint. Cross-company "revenue £3-20m"
  screening needs a pre-indexed dataset (a separate bulk-ingestion phase);
  this provider is the per-company path.
- Small companies file no P&L, so turnover / profit are often absent; the parser
  reports that honestly and callers must show "not disclosed", never a guess.

Requires settings.companies_house_api_key; raises ProviderConfigError otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.providers.exceptions import (
    CompanyNotFoundError,
    ProviderConfigError,
    ProviderError,
)
from app.providers.ixbrl import IxbrlAccounts, parse_ixbrl_accounts

REST_BASE = "https://api.company-information.service.gov.uk"
DOC_BASE = "https://document-api.company-information.service.gov.uk"
TIMEOUT_SECONDS = 20.0


@dataclass
class UkCompany:
    company_number: str
    name: str
    status: str | None
    address: str | None
    sic_codes: list[str]


@dataclass
class UkCompanyProfile:
    company_number: str
    name: str
    status: str | None
    company_type: str | None
    incorporation_date: str | None
    sic_codes: list[str]
    address: str | None


class CompaniesHouseClient:
    name = "companies_house"

    def __init__(
        self, api_key: str, *, client: httpx.Client | None = None
    ) -> None:
        if not api_key or not api_key.strip():
            raise ProviderConfigError(
                "COMPANIES_HOUSE_API_KEY is required for UK company data. Create "
                "a free key at developer.company-information.service.gov.uk."
            )
        # Basic auth: key as username, empty password.
        self._auth = (api_key.strip(), "")
        self._client = client or httpx.Client(timeout=TIMEOUT_SECONDS)

    def _get(self, url: str, *, what: str, accept: str | None = None) -> httpx.Response:
        headers = {"Accept": accept} if accept else None
        try:
            resp = self._client.get(url, auth=self._auth, headers=headers, timeout=TIMEOUT_SECONDS)
        except httpx.HTTPError as exc:
            raise ProviderError(
                f"{what} failed: could not reach Companies House "
                f"({exc.__class__.__name__})."
            ) from exc
        if resp.status_code == 404:
            raise CompanyNotFoundError(f"{what}: not found (HTTP 404).")
        if resp.status_code == 401:
            raise ProviderConfigError(
                f"{what}: Companies House rejected the API key (HTTP 401)."
            )
        if resp.status_code == 429:
            raise ProviderError(
                f"{what}: Companies House is rate limiting (HTTP 429). "
                "The free tier allows 600 requests / 5 minutes."
            )
        if resp.status_code >= 400:
            raise ProviderError(f"{what}: Companies House returned HTTP {resp.status_code}.")
        return resp

    @staticmethod
    def _addr(node: dict | None) -> str | None:
        if not isinstance(node, dict):
            return None
        parts = [
            node.get("address_line_1"),
            node.get("locality"),
            node.get("postal_code"),
        ]
        joined = ", ".join(p for p in parts if p)
        return joined or None

    def search(self, query: str, limit: int = 20) -> list[UkCompany]:
        """Name/number search. No financial filtering (the API has none)."""
        q = query.strip()
        if not q:
            return []
        data = self._get(
            f"{REST_BASE}/search/companies?q={httpx.QueryParams({'q': q})['q']}"
            f"&items_per_page={max(1, min(limit, 100))}",
            what="Company search",
        ).json()
        out: list[UkCompany] = []
        for item in data.get("items", []):
            number = item.get("company_number")
            if not number:
                continue
            out.append(
                UkCompany(
                    company_number=number,
                    name=item.get("title") or number,
                    status=item.get("company_status"),
                    address=item.get("address_snippet"),
                    sic_codes=list(item.get("sic_codes") or []),
                )
            )
        return out

    def profile(self, number: str) -> UkCompanyProfile:
        data = self._get(
            f"{REST_BASE}/company/{number.strip()}", what="Company profile"
        ).json()
        return UkCompanyProfile(
            company_number=data.get("company_number") or number,
            name=data.get("company_name") or number,
            status=data.get("company_status"),
            company_type=data.get("type"),
            incorporation_date=data.get("date_of_creation"),
            sic_codes=list(data.get("sic_codes") or []),
            address=self._addr(data.get("registered_office_address")),
        )

    def latest_accounts(self, number: str) -> IxbrlAccounts | None:
        """Most recent accounts filing, downloaded and parsed. None if there is
        no accounts filing, or no machine-readable (iXBRL) document for it."""
        history = self._get(
            f"{REST_BASE}/company/{number.strip()}/filing-history"
            "?category=accounts&items_per_page=10",
            what="Filing history",
        ).json()
        for item in history.get("items", []):
            meta_url = (item.get("links") or {}).get("document_metadata")
            if not meta_url:
                continue
            if not meta_url.startswith("http"):
                meta_url = f"{DOC_BASE}{meta_url}"
            content = self._fetch_ixbrl(meta_url)
            if content is not None:
                return parse_ixbrl_accounts(content)
        return None

    def _fetch_ixbrl(self, metadata_url: str) -> bytes | None:
        """Follow a filing's document-metadata link to its iXBRL content, or None
        if the document isn't available as inline XBRL (e.g. a scanned PDF)."""
        try:
            meta = self._get(metadata_url, what="Document metadata").json()
        except (CompanyNotFoundError, ProviderError):
            return None
        resources = meta.get("resources") or {}
        if "application/xhtml+xml" not in resources:
            return None  # no machine-readable accounts (scanned / PDF only)
        doc_url = (meta.get("links") or {}).get("document")
        if not doc_url:
            return None
        if not doc_url.startswith("http"):
            doc_url = f"{DOC_BASE}{doc_url}"
        try:
            resp = self._get(
                doc_url, what="Accounts document", accept="application/xhtml+xml"
            )
        except (CompanyNotFoundError, ProviderError):
            return None
        return resp.content
