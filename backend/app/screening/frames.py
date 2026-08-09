"""SEC XBRL "frames" API: cross-company annual financials in a handful of calls.

The per-company companyfacts endpoint answers "everything about one filer".
The frames endpoint inverts that: one call returns one fact per filer for a
given tag and period, which is what a screen needs. Roughly six calls cover the
whole US market instead of ~4,300 individual fetches.

    https://data.sec.gov/api/xbrl/frames/us-gaap/{tag}/USD/{period}.json

Two honesty rules are enforced here rather than left to callers:

* Revenue is reported under two different tags depending on the filer. The
  ASC 606 tag (RevenueFromContractWithCustomerExcludingAssessedTax) is a
  SUBSET of total revenue for companies that also earn interest, leasing or
  other non-contract revenue, so ``Revenues`` wins when a filer reports both.
  The tag actually used is recorded on the row.
* EBITDA is never filed. It is operating income plus D&A, so a filer that does
  not tag D&A separately has NO EBITDA. It is left as None rather than falling
  back to operating income, which would overstate cash earnings precisely for
  the asset-heavy companies where the two diverge most.

Note on fiscal years: the frames API assigns each filer the reporting period
that most closely fits the calendar frame, so companies with non-calendar year
ends (Apple's September, NVIDIA's January) are included, not dropped.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Iterable

import httpx

from app.providers.exceptions import ProviderConfigError, ProviderError

FRAMES_BASE = "https://data.sec.gov/api/xbrl/frames/us-gaap"
SUBMISSIONS_BASE = "https://data.sec.gov/submissions"
TIMEOUT_SECONDS = 60.0


class RevenueTag(StrEnum):
    """Which XBRL tag supplied a row's revenue (provenance for the source drawer)."""

    REVENUES = "Revenues"
    CONTRACT_REVENUE = "RevenueFromContractWithCustomerExcludingAssessedTax"


class Coverage(StrEnum):
    """How much of the income statement a filer tagged, and so what is screenable."""

    FULL = "full"  # revenue + operating income + D&A -> EBITDA available
    EBIT_ONLY = "ebit_only"  # revenue + operating income, D&A not tagged
    REVENUE_ONLY = "revenue_only"  # revenue only


class QualityFlag(StrEnum):
    """A filed figure that is arithmetically correct but misleading as filed."""

    # EBITDA above revenue. Almost always a one-off gain (an asset or spectrum
    # sale, a legal settlement, a bargain-purchase credit) reported inside
    # operating income, so the figure is not a proxy for operating earnings.
    # Anterix (ATEX) is the canonical case: $6.5m revenue, $93.9m operating
    # income. The row is kept and flagged rather than hidden or silently
    # ranked first, since the filing itself is not in question.
    EBITDA_EXCEEDS_REVENUE = "ebitda_exceeds_revenue"


OPERATING_INCOME_TAG = "OperatingIncomeLoss"
DEPRECIATION_TAG = "DepreciationDepletionAndAmortization"


@dataclass(frozen=True)
class ScreenRow:
    """One filer's annual figures for one period, as filed."""

    cik: int
    entity_name: str
    period: str  # e.g. "CY2025"
    period_end: str | None  # the filer's own period end date
    accession: str | None  # filing the revenue figure came from
    revenue: float
    revenue_tag: RevenueTag
    operating_income: float | None
    depreciation_amortization: float | None
    ebitda: float | None  # CALCULATED, never filed
    ebitda_margin: float | None
    coverage: Coverage
    quality_flag: QualityFlag | None = None


def _by_cik(frame: Iterable[dict[str, Any]] | None) -> dict[int, dict[str, Any]]:
    """Index a frames payload by CIK, ignoring rows without a usable value."""
    out: dict[int, dict[str, Any]] = {}
    for record in frame or []:
        cik = record.get("cik")
        value = record.get("val")
        if cik is None or not isinstance(value, (int, float)):
            continue
        out[int(cik)] = record
    return out


def merge_frames(
    *,
    period: str,
    revenues: Iterable[dict[str, Any]] | None,
    revenue_from_contracts: Iterable[dict[str, Any]] | None,
    operating_income: Iterable[dict[str, Any]] | None,
    depreciation_amortization: Iterable[dict[str, Any]] | None,
) -> list[ScreenRow]:
    """Join the four frames into one row per filer that reported revenue.

    Revenue is required: a company with no revenue figure cannot be screened on
    revenue and is excluded entirely rather than carried as a partial row.
    """
    total_rev = _by_cik(revenues)
    contract_rev = _by_cik(revenue_from_contracts)
    oi_by_cik = _by_cik(operating_income)
    dda_by_cik = _by_cik(depreciation_amortization)

    rows: list[ScreenRow] = []
    for cik in set(total_rev) | set(contract_rev):
        # Prefer the total-revenue tag; the ASC 606 tag is a subset for filers
        # with non-contract revenue.
        if cik in total_rev:
            rev_record, rev_tag = total_rev[cik], RevenueTag.REVENUES
        else:
            rev_record, rev_tag = contract_rev[cik], RevenueTag.CONTRACT_REVENUE

        revenue = float(rev_record["val"])
        oi_record = oi_by_cik.get(cik)
        dda_record = dda_by_cik.get(cik)
        oi = float(oi_record["val"]) if oi_record else None
        dda = float(dda_record["val"]) if dda_record else None

        # EBITDA needs BOTH components. Falling back to operating income here
        # would silently understate depreciation-heavy businesses.
        if oi is not None and dda is not None:
            ebitda: float | None = oi + dda
            coverage = Coverage.FULL
        else:
            ebitda = None
            coverage = Coverage.EBIT_ONLY if oi is not None else Coverage.REVENUE_ONLY

        margin = ebitda / revenue if (ebitda is not None and revenue) else None

        # Flag rather than drop: the filing is accurate, but EBITDA above
        # revenue signals a one-off gain inside operating income, so the row
        # must not read as a high-margin operating business.
        flag = (
            QualityFlag.EBITDA_EXCEEDS_REVENUE
            if (ebitda is not None and revenue > 0 and ebitda > revenue)
            else None
        )

        rows.append(
            ScreenRow(
                cik=cik,
                entity_name=str(rev_record.get("entityName") or "").strip(),
                period=period,
                period_end=rev_record.get("end"),
                accession=rev_record.get("accn"),
                revenue=revenue,
                revenue_tag=rev_tag,
                operating_income=oi,
                depreciation_amortization=dda,
                ebitda=ebitda,
                ebitda_margin=margin,
                coverage=coverage,
                quality_flag=flag,
            )
        )
    return rows


class SecFramesClient:
    """Thin SEC frames/submissions client with the SEC's required User-Agent.

    The SEC rate-limits by IP (10 requests/second, stricter from shared cloud
    egress), so 429s are retried with a short backoff rather than failed.
    """

    def __init__(self, user_agent: str, *, client: httpx.Client | None = None) -> None:
        if not user_agent or not user_agent.strip():
            raise ProviderConfigError(
                "SEC_EDGAR_USER_AGENT is required for SEC frames requests "
                "(e.g. 'Your Name your.email@example.com')."
            )
        self.user_agent = user_agent.strip()
        self._client = client or httpx.Client(timeout=TIMEOUT_SECONDS)

    def _get_json(self, url: str, *, what: str) -> Any | None:
        """GET and parse, or None when the resource simply does not exist.

        A missing frame (404) is normal: not every tag is reported in every
        period. That is absence of data, not an error, so callers get None.
        """
        headers = {"User-Agent": self.user_agent}
        attempts = 3
        for attempt in range(1, attempts + 1):
            try:
                response = self._client.get(url, headers=headers, timeout=TIMEOUT_SECONDS)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status == 404:
                    return None
                if status == 429 and attempt < attempts:
                    time.sleep(attempt * 2.0)
                    continue
                raise ProviderError(
                    f"{what} failed: SEC returned HTTP {status}."
                ) from exc
            except httpx.HTTPError as exc:
                raise ProviderError(
                    f"{what} failed: could not reach the SEC "
                    f"({exc.__class__.__name__})."
                ) from exc
            except ValueError as exc:
                raise ProviderError(f"{what} failed: SEC returned invalid JSON.") from exc
        raise ProviderError(f"{what} failed: SEC retries exhausted.")

    def fetch_frame(self, tag: str, period: str) -> list[dict[str, Any]]:
        """One tag for one period across every filer. [] when not published."""
        payload = self._get_json(
            f"{FRAMES_BASE}/{tag}/USD/{period}.json",
            what=f"SEC frame {tag} {period}",
        )
        if not isinstance(payload, dict):
            return []
        data = payload.get("data")
        return data if isinstance(data, list) else []

    def fetch_period_rows(self, period: str) -> list[ScreenRow]:
        """All four frames for one period, merged into screen rows."""
        return merge_frames(
            period=period,
            revenues=self.fetch_frame(RevenueTag.REVENUES.value, period),
            revenue_from_contracts=self.fetch_frame(
                RevenueTag.CONTRACT_REVENUE.value, period
            ),
            operating_income=self.fetch_frame(OPERATING_INCOME_TAG, period),
            depreciation_amortization=self.fetch_frame(DEPRECIATION_TAG, period),
        )

    def fetch_submission(self, cik: int) -> dict[str, Any] | None:
        """Company metadata (SIC sector, exchange, ticker) for one filer."""
        return self._get_json(
            f"{SUBMISSIONS_BASE}/CIK{cik:010d}.json",
            what=f"SEC submissions for CIK {cik}",
        )

    def fetch_ticker_map(self) -> dict[int, str]:
        """CIK -> ticker for every listed US filer, in a single call.

        Filers absent from this file have no listed ticker (funds, and private
        companies that file only because they have public debt), which is how
        the index distinguishes listed companies from the rest.
        """
        payload = self._get_json(
            "https://www.sec.gov/files/company_tickers.json",
            what="SEC ticker map",
        )
        if not isinstance(payload, dict):
            return {}
        out: dict[int, str] = {}
        for record in payload.values():
            if not isinstance(record, dict):
                continue
            cik, ticker = record.get("cik_str"), record.get("ticker")
            if cik is None or not ticker:
                continue
            # The file lists share classes separately (GOOG/GOOGL share a CIK);
            # first occurrence wins so a CIK maps to one primary ticker.
            out.setdefault(int(cik), str(ticker).strip().upper())
        return out


def latest_rows_by_cik(period_rows: list[list[ScreenRow]]) -> list[ScreenRow]:
    """Collapse several periods to one row per filer, newest period winning.

    ``period_rows`` is ordered newest period first. A filer that has not yet
    filed for the newest period keeps its prior-year row, which is why every
    row carries its own ``period``: the table can state the year per company
    instead of implying they all share one.
    """
    chosen: dict[int, ScreenRow] = {}
    for rows in period_rows:
        for row in rows:
            chosen.setdefault(row.cik, row)
    return list(chosen.values())
