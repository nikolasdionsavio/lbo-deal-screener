"""EdgarFilingsProvider: latest SEC filings from the submissions feed (spec §19.3).

- Submissions via https://data.sec.gov/submissions/CIK{cik:010d}.json (UA
  header, same 429-retry pattern as providers/edgar.py).
- Ticker -> CIK reuses SecEdgarProvider's bundled ticker map (read-only).
- Forms kept: 10-K, 10-Q, 8-K, DEF 14A; latest 10 (the "recent" arrays are
  newest-first already).
- Document URL: https://www.sec.gov/Archives/edgar/data/{int(cik)}/
  {accession without dashes}/{primaryDocument}.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.providers.edgar import SecEdgarProvider
from app.providers.exceptions import CompanyNotFoundError, ProviderError
from app.schemas.filings import Filing

SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
DOCUMENT_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{document}"

TIMEOUT_SECONDS = 15.0
FILING_FORMS = {"10-K", "10-Q", "8-K", "DEF 14A"}
MAX_FILINGS = 10


class EdgarFilingsProvider:
    """Filings intelligence component (not a full DataProvider)."""

    name = "sec_edgar_filings"

    def __init__(
        self,
        user_agent: str,
        *,
        client: httpx.Client | None = None,
        cache_dir: str | None = None,
    ) -> None:
        self._client = client or httpx.Client(timeout=TIMEOUT_SECONDS)
        # Reused for its ticker -> CIK map only (read-only); it also validates
        # the user agent (ProviderConfigError when blank).
        self._edgar = SecEdgarProvider(
            user_agent, client=self._client, cache_dir=cache_dir
        )
        self.user_agent = self._edgar.user_agent

    # ----- HTTP (429-retry pattern from providers/edgar.py) -----

    def _request_json(self, url: str, *, what: str) -> Any:
        headers = {"User-Agent": self.user_agent}
        # SEC rate-limits aggressively by IP (shared cloud egress IPs especially);
        # 429s are usually transient, so retry briefly before failing.
        attempts = 3
        for attempt in range(1, attempts + 1):
            try:
                response = self._client.get(url, headers=headers, timeout=TIMEOUT_SECONDS)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status == 404:
                    raise CompanyNotFoundError(
                        f"{what}: not found on SEC EDGAR (HTTP 404)."
                    ) from exc
                if status == 429 and attempt < attempts:
                    time.sleep(attempt * 2.0)
                    continue
                if status == 429:
                    raise ProviderError(
                        f"{what} failed: SEC EDGAR is rate limiting requests "
                        "(HTTP 429). Try again in a minute."
                    ) from exc
                raise ProviderError(
                    f"{what} failed: SEC EDGAR returned HTTP {status}."
                ) from exc
            except httpx.HTTPError as exc:
                raise ProviderError(
                    f"{what} failed: could not reach SEC EDGAR "
                    f"({exc.__class__.__name__})."
                ) from exc
            except ValueError as exc:
                raise ProviderError(
                    f"{what} failed: SEC EDGAR returned invalid JSON."
                ) from exc
        raise ProviderError(f"{what} failed: SEC EDGAR retries exhausted.")

    # ----- public API -----

    def resolve_cik(self, ticker: str) -> int:
        """Ticker -> CIK via the bundled EDGAR ticker map.

        Raises CompanyNotFoundError when the ticker is not a US filer (e.g.
        mock/sample tickers).
        """
        cik, _title = self._edgar._resolve_cik(ticker)  # read-only map access
        return cik

    def get_filings(self, ticker: str) -> tuple[str, list[Filing]]:
        """(zero-padded CIK, latest filings) for the §19.3 form set.

        Raises CompanyNotFoundError when the ticker has no CIK, ProviderError
        on EDGAR failures.
        """
        cik = self.resolve_cik(ticker)
        doc = self._request_json(
            SUBMISSIONS_URL.format(cik=cik),
            what=f"SEC EDGAR submissions for {ticker.strip().upper()}",
        )
        recent = doc.get("filings", {}).get("recent", {})
        forms = recent.get("form") or []
        filed_dates = recent.get("filingDate") or []
        report_dates = recent.get("reportDate") or []
        accessions = recent.get("accessionNumber") or []
        documents = recent.get("primaryDocument") or []

        filings: list[Filing] = []
        for form, filed, report_date, accession, document in zip(
            forms, filed_dates, report_dates, accessions, documents
        ):
            if form not in FILING_FORMS:
                continue
            url = (
                DOCUMENT_URL.format(
                    cik=int(cik),
                    accession=str(accession).replace("-", ""),
                    document=document,
                )
                if accession and document
                else None
            )
            filings.append(
                Filing(
                    form=str(form),
                    filed=str(filed) if filed else None,
                    report_date=str(report_date) if report_date else None,
                    accession=str(accession) if accession else None,
                    primary_document=str(document) if document else None,
                    url=url,
                )
            )
            if len(filings) >= MAX_FILINGS:
                break
        return f"{cik:010d}", filings
