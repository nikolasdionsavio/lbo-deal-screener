"""SEC frames merge logic for the US screening index.

The merge is where the honesty of the whole screen lives: EBITDA is CALCULATED
from operating income plus D&A, so a filer that does not tag D&A separately has
no EBITDA at all. It must be reported as undisclosed rather than approximated
by operating income, because a PE screen that silently treats EBIT as EBITDA
overstates cash earnings for exactly the asset-heavy companies where the gap is
widest.
"""

from typing import Any, Callable

from fastapi.testclient import TestClient

from app.db.models import ScreenIndexRow
from app.screening.frames import (
    RevenueTag,
    ScreenRow,
    merge_frames,
)
from app.screening.index_service import (
    coverage_summary,
    query_screen,
    rebuild_index,
)


def _frame(rows: list[tuple[int, str, float]], end: str = "2025-12-31") -> list[dict]:
    """Build a frames-API style payload: [{cik, entityName, val, end, accn}]."""
    return [
        {
            "cik": cik,
            "entityName": name,
            "val": val,
            "end": end,
            "accn": f"{cik:010d}-25-000001",
        }
        for cik, name, val in rows
    ]


def test_full_coverage_calculates_ebitda_and_margin() -> None:
    """Revenue + operating income + D&A gives a screenable EBITDA row."""
    rows = merge_frames(
        period="CY2025",
        revenues=_frame([(1, "Alpha Corp", 10_000_000.0)]),
        revenue_from_contracts=[],
        operating_income=_frame([(1, "Alpha Corp", 1_200_000.0)]),
        depreciation_amortization=_frame([(1, "Alpha Corp", 300_000.0)]),
    )
    assert len(rows) == 1
    row = rows[0]
    assert isinstance(row, ScreenRow)
    assert row.cik == 1
    assert row.revenue == 10_000_000.0
    assert row.operating_income == 1_200_000.0
    assert row.depreciation_amortization == 300_000.0
    # EBITDA is derived, never filed: operating income + D&A.
    assert row.ebitda == 1_500_000.0
    assert row.ebitda_margin == 0.15
    assert row.coverage == "full"
    assert row.period == "CY2025"
    assert row.period_end == "2025-12-31"


def test_missing_dna_leaves_ebitda_undisclosed_not_guessed() -> None:
    """No separately tagged D&A means no EBITDA. It must NOT fall back to EBIT."""
    rows = merge_frames(
        period="CY2025",
        revenues=_frame([(2, "Beta Inc", 8_000_000.0)]),
        revenue_from_contracts=[],
        operating_income=_frame([(2, "Beta Inc", 900_000.0)]),
        depreciation_amortization=[],
    )
    row = rows[0]
    assert row.operating_income == 900_000.0
    assert row.depreciation_amortization is None
    assert row.ebitda is None, "EBITDA must be undisclosed, not approximated by EBIT"
    assert row.ebitda_margin is None
    assert row.coverage == "ebit_only"


def test_revenue_only_company_is_kept_with_revenue_only_coverage() -> None:
    rows = merge_frames(
        period="CY2025",
        revenues=_frame([(3, "Gamma Ltd", 5_000_000.0)]),
        revenue_from_contracts=[],
        operating_income=[],
        depreciation_amortization=[],
    )
    row = rows[0]
    assert row.revenue == 5_000_000.0
    assert row.operating_income is None
    assert row.ebitda is None
    assert row.coverage == "revenue_only"


def test_revenues_tag_preferred_over_contract_revenue_and_recorded() -> None:
    """Filers report both tags; ``Revenues`` is the total, the ASC 606 tag is a
    subset. Prefer the total and record which tag supplied the figure."""
    rows = merge_frames(
        period="CY2025",
        revenues=_frame([(4, "Delta Co", 20_000_000.0)]),
        revenue_from_contracts=_frame([(4, "Delta Co", 18_000_000.0)]),
        operating_income=[],
        depreciation_amortization=[],
    )
    assert rows[0].revenue == 20_000_000.0
    assert rows[0].revenue_tag == RevenueTag.REVENUES


def test_contract_revenue_used_when_total_revenues_absent() -> None:
    rows = merge_frames(
        period="CY2025",
        revenues=[],
        revenue_from_contracts=_frame([(5, "Epsilon SA", 12_000_000.0)]),
        operating_income=[],
        depreciation_amortization=[],
    )
    assert rows[0].revenue == 12_000_000.0
    assert rows[0].revenue_tag == RevenueTag.CONTRACT_REVENUE


def test_company_without_revenue_is_excluded() -> None:
    """Operating income alone cannot be screened on revenue, so it is not a row."""
    rows = merge_frames(
        period="CY2025",
        revenues=[],
        revenue_from_contracts=[],
        operating_income=_frame([(6, "Zeta Trust", 400_000.0)]),
        depreciation_amortization=_frame([(6, "Zeta Trust", 50_000.0)]),
    )
    assert rows == []


def test_negative_ebitda_is_kept_and_margin_signed() -> None:
    """Loss-making companies stay in the index; the screen filters them, not
    the ingest, so 'positive EBITDA' remains a user choice."""
    rows = merge_frames(
        period="CY2025",
        revenues=_frame([(7, "Eta Bio", 4_000_000.0)]),
        revenue_from_contracts=[],
        operating_income=_frame([(7, "Eta Bio", -2_400_000.0)]),
        depreciation_amortization=_frame([(7, "Eta Bio", 400_000.0)]),
    )
    row = rows[0]
    assert row.ebitda == -2_000_000.0
    assert row.ebitda_margin == -0.5
    assert row.coverage == "full"


def test_zero_revenue_does_not_divide_by_zero() -> None:
    rows = merge_frames(
        period="CY2025",
        revenues=_frame([(8, "Theta Shell", 0.0)]),
        revenue_from_contracts=[],
        operating_income=_frame([(8, "Theta Shell", -100_000.0)]),
        depreciation_amortization=_frame([(8, "Theta Shell", 10_000.0)]),
    )
    row = rows[0]
    assert row.revenue == 0.0
    assert row.ebitda == -90_000.0
    assert row.ebitda_margin is None, "margin is undefined at zero revenue"


def test_rows_carry_accession_for_source_linking() -> None:
    """Every figure must be traceable to the filing it came from."""
    rows = merge_frames(
        period="CY2025",
        revenues=_frame([(9, "Iota Corp", 7_000_000.0)]),
        revenue_from_contracts=[],
        operating_income=[],
        depreciation_amortization=[],
    )
    assert rows[0].accession == "0000000009-25-000001"


# --------------------------------------------------------------- index query --


def _seed(session_factory: Callable[[], Any]) -> None:
    """Four companies spanning every coverage level.

    Kappa is the one that matters most: it is profitable on EBIT and would look
    like a strong screen hit, but it never tagged D&A, so it has no EBITDA and
    must stay out of EBITDA-filtered results.
    """
    db = session_factory()
    db.add_all(
        [
            ScreenIndexRow(
                cik=101, ticker="ALPH", entity_name="Alpha Precision Corp",
                sic="3559", sic_description="Special Industry Machinery",
                exchange="Nasdaq", period="CY2025", period_end="2025-12-31",
                accession="0000000101-25-000001", revenue=10_000_000.0,
                revenue_tag="Revenues", operating_income=1_200_000.0,
                depreciation_amortization=300_000.0, ebitda=1_500_000.0,
                ebitda_margin=0.15, coverage="full",
            ),
            ScreenIndexRow(
                cik=102, ticker="BETA", entity_name="Beta Engineering Inc",
                sic="3559", sic_description="Special Industry Machinery",
                exchange="NYSE", period="CY2025", period_end="2025-12-31",
                accession="0000000102-25-000001", revenue=18_000_000.0,
                revenue_tag="Revenues", operating_income=-500_000.0,
                depreciation_amortization=200_000.0, ebitda=-300_000.0,
                ebitda_margin=-0.016667, coverage="full",
            ),
            ScreenIndexRow(
                cik=103, ticker="KAPP", entity_name="Kappa Industrial Ltd",
                sic="3559", sic_description="Special Industry Machinery",
                exchange="Nasdaq", period="CY2025", period_end="2025-12-31",
                accession="0000000103-25-000001", revenue=12_000_000.0,
                revenue_tag="Revenues", operating_income=2_000_000.0,
                depreciation_amortization=None, ebitda=None,
                ebitda_margin=None, coverage="ebit_only",
            ),
            ScreenIndexRow(
                cik=104, ticker="OMEG", entity_name="Omega Software Corp",
                sic="7372", sic_description="Prepackaged Software",
                exchange="Nasdaq", period="CY2025", period_end="2025-12-31",
                accession="0000000104-25-000001", revenue=900_000_000.0,
                revenue_tag="RevenueFromContractWithCustomerExcludingAssessedTax",
                operating_income=None, depreciation_amortization=None,
                ebitda=None, ebitda_margin=None, coverage="revenue_only",
            ),
        ]
    )
    db.commit()
    db.close()


def test_positive_ebitda_screen_excludes_undisclosed_ebitda(client: TestClient) -> None:
    """The core guarantee: a profitable-on-EBIT company with no D&A tag does NOT
    appear in a positive-EBITDA screen. Silently admitting it would be a guess."""
    _seed(client.session_factory)
    db = client.session_factory()
    rows, total = query_screen(
        db, revenue_min=3_000_000, revenue_max=20_000_000, ebitda_positive=True
    )
    db.close()
    tickers = [r.ticker for r in rows]
    assert tickers == ["ALPH"], "only the company with a real EBITDA qualifies"
    assert total == 1
    assert "KAPP" not in tickers, "EBIT must never stand in for EBITDA"
    assert "BETA" not in tickers, "negative EBITDA is correctly filtered out"


def test_revenue_band_matches_the_worked_example(client: TestClient) -> None:
    _seed(client.session_factory)
    db = client.session_factory()
    rows, total = query_screen(db, revenue_min=3_000_000, revenue_max=20_000_000)
    db.close()
    assert total == 3, "Omega at $900m revenue is outside the band"
    assert {r.ticker for r in rows} == {"ALPH", "BETA", "KAPP"}


def test_sector_filter_is_case_insensitive_substring(client: TestClient) -> None:
    _seed(client.session_factory)
    db = client.session_factory()
    rows, _ = query_screen(db, sector="machinery")
    db.close()
    assert {r.ticker for r in rows} == {"ALPH", "BETA", "KAPP"}


def test_margin_filter_excludes_unknown_margins(client: TestClient) -> None:
    _seed(client.session_factory)
    db = client.session_factory()
    rows, _ = query_screen(db, margin_min=0.10)
    db.close()
    assert [r.ticker for r in rows] == ["ALPH"]


def test_sort_and_pagination(client: TestClient) -> None:
    _seed(client.session_factory)
    db = client.session_factory()
    page_one, total = query_screen(db, sort="revenue", direction="desc", limit=2)
    page_two, _ = query_screen(db, sort="revenue", direction="desc", limit=2, offset=2)
    db.close()
    assert total == 4
    assert [r.ticker for r in page_one] == ["OMEG", "BETA"]
    assert [r.ticker for r in page_two] == ["KAPP", "ALPH"]


def test_sort_by_ebitda_puts_unknown_last_not_first(client: TestClient) -> None:
    """Ascending sort must not let NULL EBITDA masquerade as the smallest value."""
    _seed(client.session_factory)
    db = client.session_factory()
    rows, _ = query_screen(db, sort="ebitda", direction="asc")
    db.close()
    assert [r.ticker for r in rows][:2] == ["BETA", "ALPH"]
    assert {r.ticker for r in rows[2:]} == {"KAPP", "OMEG"}


def test_coverage_summary_counts_each_level(client: TestClient) -> None:
    _seed(client.session_factory)
    db = client.session_factory()
    summary = coverage_summary(db)
    db.close()
    assert summary["total"] == 4
    assert summary["with_ebitda"] == 2
    assert summary["ebit_only"] == 1
    assert summary["revenue_only"] == 1
    assert summary["refreshed_at"]


# ------------------------------------------------------------ index rebuild --


class _FakeClient:
    """Stands in for SecFramesClient: no network, scripted frames."""

    def __init__(self, rows_by_period: dict[str, list[ScreenRow]], tickers: dict[int, str]):
        self._rows = rows_by_period
        self._tickers = tickers

    def fetch_period_rows(self, period: str) -> list[ScreenRow]:
        return self._rows.get(period, [])

    def fetch_ticker_map(self) -> dict[int, str]:
        return self._tickers


def _row(cik: int, revenue: float, period: str = "CY2025") -> ScreenRow:
    return ScreenRow(
        cik=cik, entity_name=f"Company {cik}", period=period,
        period_end="2025-12-31", accession=f"{cik:010d}-25-000001",
        revenue=revenue, revenue_tag=RevenueTag.REVENUES,
        operating_income=100.0, depreciation_amortization=50.0,
        ebitda=150.0, ebitda_margin=150.0 / revenue, coverage="full",
    )


def test_rebuild_keeps_only_listed_filers(client: TestClient) -> None:
    """Companies with no listed ticker (funds, debt-only filers) are not a
    US-listed screen universe, so they are dropped."""
    fake = _FakeClient({"CY2025": [_row(201, 5e6), _row(202, 6e6)]}, {201: "AAA"})
    db = client.session_factory()
    result = rebuild_index(db, fake, periods=("CY2025",))
    rows, _ = query_screen(db)
    db.close()
    assert result.fetched == 2
    assert result.listed == 1
    assert [r.ticker for r in rows] == ["AAA"]


def test_rebuild_is_idempotent_and_updates_in_place(client: TestClient) -> None:
    db = client.session_factory()
    rebuild_index(db, _FakeClient({"CY2025": [_row(201, 5e6)]}, {201: "AAA"}), periods=("CY2025",))
    rebuild_index(db, _FakeClient({"CY2025": [_row(201, 7e6)]}, {201: "AAA"}), periods=("CY2025",))
    rows, total = query_screen(db)
    db.close()
    assert total == 1, "a refresh updates the row rather than duplicating it"
    assert rows[0].revenue == 7e6


def test_rebuild_prefers_newest_period_but_keeps_prior_year_filers(
    client: TestClient,
) -> None:
    """A company that has not filed for CY2025 yet keeps its CY2024 figures,
    and each row states its own period so the table never implies one year."""
    fake = _FakeClient(
        {
            "CY2025": [_row(201, 5e6, "CY2025")],
            "CY2024": [_row(201, 4e6, "CY2024"), _row(202, 9e6, "CY2024")],
        },
        {201: "AAA", 202: "BBB"},
    )
    db = client.session_factory()
    rebuild_index(db, fake, periods=("CY2025", "CY2024"))
    rows, total = query_screen(db, sort="ticker", direction="asc")
    db.close()
    assert total == 2
    by_ticker = {r.ticker: r for r in rows}
    assert by_ticker["AAA"].revenue == 5e6 and by_ticker["AAA"].period == "CY2025"
    assert by_ticker["BBB"].revenue == 9e6 and by_ticker["BBB"].period == "CY2024"


# --------------------------------------------------------------- API surface --


def test_screen_endpoint_returns_rows_with_coverage_and_source(
    client: TestClient,
) -> None:
    _seed(client.session_factory)
    body = client.get("/api/screen", params={"limit": 10}).json()
    assert body["total"] == 4
    assert body["source"] == "SEC EDGAR (XBRL company facts)"
    assert body["coverage"]["with_ebitda"] == 2
    assert body["coverage"]["ebit_only"] == 1
    first = body["rows"][0]
    assert set(first) >= {
        "cik", "ticker", "name", "sector", "period", "revenue",
        "ebitda", "ebitda_margin", "coverage", "coverage_note", "filing_url",
    }


def test_screen_endpoint_worked_example_query(client: TestClient) -> None:
    """The query the feature was asked for: revenue band plus positive EBITDA."""
    _seed(client.session_factory)
    body = client.get(
        "/api/screen",
        params={
            "revenue_min": 3_000_000,
            "revenue_max": 20_000_000,
            "ebitda_positive": "true",
            "sort": "revenue",
            "direction": "desc",
        },
    ).json()
    assert [r["ticker"] for r in body["rows"]] == ["ALPH"]
    assert "excludes companies that do not disclose" in body["note"]


def test_screen_endpoint_states_undisclosed_ebitda(client: TestClient) -> None:
    """An EBIT-only company appears in an unfiltered screen with a null EBITDA
    and a note explaining why, rather than being silently dropped or guessed."""
    _seed(client.session_factory)
    body = client.get("/api/screen", params={"q": "Kappa"}).json()
    row = body["rows"][0]
    assert row["ebitda"] is None
    assert row["operating_income"] == 2_000_000.0
    assert row["coverage"] == "ebit_only"
    assert "not disclosed" in row["coverage_note"]


def test_screen_row_links_to_the_source_filing(client: TestClient) -> None:
    _seed(client.session_factory)
    body = client.get("/api/screen", params={"q": "ALPH"}).json()
    url = body["rows"][0]["filing_url"]
    assert url == (
        "https://www.sec.gov/Archives/edgar/data/101/"
        "000000010125000001/0000000101-25-000001-index.htm"
    )


def test_sectors_endpoint_ranks_by_count(client: TestClient) -> None:
    _seed(client.session_factory)
    body = client.get("/api/screen/sectors").json()
    assert body[0]["name"] == "Special Industry Machinery"
    assert body[0]["count"] == 3
    assert {s["name"] for s in body} == {
        "Special Industry Machinery",
        "Prepackaged Software",
    }


def test_screen_empty_index_returns_empty_not_error(client: TestClient) -> None:
    """Before the first backfill the endpoint must answer cleanly."""
    body = client.get("/api/screen").json()
    assert body["rows"] == []
    assert body["total"] == 0
    assert body["coverage"]["total"] == 0


# ------------------------------------------------------- filing-artifact flag --


def test_ebitda_above_revenue_is_flagged_not_dropped() -> None:
    """Anterix's real shape: $6.5m revenue, $93.9m operating income from a
    one-off gain. The filing is accurate, so the row stays, but it must not
    read as a 1,452% operating margin."""
    rows = merge_frames(
        period="CY2025",
        revenues=_frame([(10, "Anterix Inc.", 6_501_000.0)]),
        revenue_from_contracts=[],
        operating_income=_frame([(10, "Anterix Inc.", 93_930_000.0)]),
        depreciation_amortization=_frame([(10, "Anterix Inc.", 464_000.0)]),
    )
    row = rows[0]
    assert row.ebitda == 94_394_000.0, "the filed arithmetic is preserved"
    assert row.quality_flag == "ebitda_exceeds_revenue"


def test_ordinary_high_margin_company_is_not_flagged() -> None:
    """A 60% margin is a real business, not an artifact. Only EBITDA above
    revenue trips the flag."""
    rows = merge_frames(
        period="CY2025",
        revenues=_frame([(11, "Software Co", 10_000_000.0)]),
        revenue_from_contracts=[],
        operating_income=_frame([(11, "Software Co", 5_500_000.0)]),
        depreciation_amortization=_frame([(11, "Software Co", 500_000.0)]),
    )
    assert rows[0].ebitda_margin == 0.6
    assert rows[0].quality_flag is None


def test_exclude_flagged_removes_artifact_rows(client: TestClient) -> None:
    db = client.session_factory()
    db.add(
        ScreenIndexRow(
            cik=110, ticker="ATEX", entity_name="Anterix Inc.",
            period="CY2025", period_end="2026-03-31", revenue=6_501_000.0,
            operating_income=93_930_000.0, depreciation_amortization=464_000.0,
            ebitda=94_394_000.0, ebitda_margin=14.52, coverage="full",
            quality_flag="ebitda_exceeds_revenue",
        )
    )
    db.commit()
    _, kept = query_screen(db, ebitda_positive=True)
    _, filtered = query_screen(db, ebitda_positive=True, exclude_flagged=True)
    db.close()
    assert kept == 1, "flagged rows are shown by default, not hidden"
    assert filtered == 0, "and can be excluded on request"


def test_flagged_row_carries_an_explanation_through_the_api(
    client: TestClient,
) -> None:
    db = client.session_factory()
    db.add(
        ScreenIndexRow(
            cik=110, ticker="ATEX", entity_name="Anterix Inc.",
            period="CY2025", revenue=6_501_000.0, operating_income=93_930_000.0,
            depreciation_amortization=464_000.0, ebitda=94_394_000.0,
            ebitda_margin=14.52, coverage="full",
            quality_flag="ebitda_exceeds_revenue",
        )
    )
    db.commit()
    db.close()
    body = client.get("/api/screen", params={"q": "Anterix"}).json()
    row = body["rows"][0]
    assert row["quality_flag"] == "ebitda_exceeds_revenue"
    assert "one-off gain" in row["quality_note"]
    assert body["coverage"]["flagged"] == 1
