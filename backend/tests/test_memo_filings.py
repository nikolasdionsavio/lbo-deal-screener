"""Memo 10-K link lines (spec §19.3): with/without filings.

Reuses the hand-built schema fixtures from tests/test_memo.py so the memo
generator stays isolated from app.kpis / app.valuation / app.lbo.
"""

from app.memo import generate_memo
from app.schemas.filings import Filing
from app.schemas.memo import MemoResponse
from app.scoring import compute_score
from tests.test_memo import (
    assert_no_none_or_nan,
    make_kpis,
    make_lbo,
    make_profile,
    make_valuation,
    section_map,
)

TEN_K_URL = (
    "https://www.sec.gov/Archives/edgar/data/320193/000032019325000123/"
    "aapl-20250927.htm"
)
OLD_TEN_K_URL = (
    "https://www.sec.gov/Archives/edgar/data/320193/000032019324000100/"
    "aapl-20240928.htm"
)

FILINGS = [
    Filing(
        form="8-K",
        filed="2025-12-01",
        accession="0000320193-25-000200",
        primary_document="event.htm",
        url="https://www.sec.gov/Archives/edgar/data/320193/000032019325000200/event.htm",
    ),
    Filing(
        form="10-K",
        filed="2025-11-01",
        report_date="2025-09-27",
        accession="0000320193-25-000123",
        primary_document="aapl-20250927.htm",
        url=TEN_K_URL,
    ),
    Filing(
        form="10-K",
        filed="2024-11-01",
        report_date="2024-09-28",
        accession="0000320193-24-000100",
        primary_document="aapl-20240928.htm",
        url=OLD_TEN_K_URL,
    ),
]


def memo(filings: list[Filing] | None) -> MemoResponse:
    kpis = make_kpis()
    valuation = make_valuation()
    score = compute_score(kpis, valuation.multiples)
    return generate_memo(
        make_profile(), kpis, valuation, make_lbo(), score, filings=filings
    )


def contents(filings: list[Filing] | None) -> dict[str, str]:
    return section_map(memo(filings))


# ---------------------------------------------------------------------------
# With filings: link lines per §19.3
# ---------------------------------------------------------------------------


def test_overview_appends_latest_10k_line_with_link() -> None:
    overview = contents(FILINGS)["company_overview"]
    assert "Latest 10-K filed 2025-11-01" in overview
    assert f"]({TEN_K_URL})" in overview  # markdown link to the document
    assert OLD_TEN_K_URL not in overview  # the LATEST 10-K wins


def test_key_risks_appends_item_1a_pointer_with_link() -> None:
    risks = contents(FILINGS)["key_risks"]
    assert "Item 1A" in risks
    assert f"]({TEN_K_URL})" in risks
    # The unconditional public-market line is still present.
    assert "Public-market valuation may already reflect" in risks


def test_no_none_or_nan_literals_with_filings() -> None:
    assert_no_none_or_nan(memo(FILINGS))


# ---------------------------------------------------------------------------
# Without filings (or without a usable 10-K): byte-identical output
# ---------------------------------------------------------------------------


def test_absent_empty_and_no_10k_filings_are_byte_identical() -> None:
    baseline = contents(None)
    assert contents([]) == baseline
    assert contents([FILINGS[0]]) == baseline  # 8-K only: no 10-K to link
    # Unlinkable 10-Ks (no url / no filed date) are ignored defensively.
    assert contents([Filing(form="10-K", filed="2025-11-01")]) == baseline
    assert contents([Filing(form="10-K", url=TEN_K_URL)]) == baseline


def test_link_lines_absent_without_filings() -> None:
    sections = contents(None)
    assert "Latest 10-K" not in sections["company_overview"]
    assert "Item 1A" not in sections["key_risks"]
    assert "sec.gov" not in sections["company_overview"]
    assert "sec.gov" not in sections["key_risks"]


def test_legacy_positional_call_unchanged() -> None:
    """The pre-§19.3 call signature (no filings argument) still works."""
    kpis = make_kpis()
    valuation = make_valuation()
    score = compute_score(kpis, valuation.multiples)
    legacy = generate_memo(make_profile(), kpis, valuation, make_lbo(), score)
    assert section_map(legacy) == contents(None)
