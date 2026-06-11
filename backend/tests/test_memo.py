"""Investment memo tests (spec §15, against §10).

All inputs are built by hand from schema objects so the memo generator is
tested in isolation from app.kpis / app.valuation / app.lbo.
"""

import re

import pytest

from app.memo import generate_memo
from app.schemas.company import CompanyProfile
from app.schemas.kpi import KpiResponse, TracedValue
from app.schemas.lbo import (
    LboAssumptions,
    LboEntry,
    LboExit,
    LboResponse,
    LboSensitivities,
    LboYear,
    SensitivityGrid,
)
from app.schemas.memo import MEMO_SECTION_KEYS, MemoResponse
from app.schemas.valuation import ValuationAssumptions, ValuationCase, ValuationResponse
from app.scoring import compute_score

# TESTCO FY2025 KPI values (spec §15) as (value, unit, label).
TESTCO_KPIS: dict[str, tuple[float, str, str]] = {
    "revenue_growth_yoy": (1000 / 950 - 1, "percent", "Revenue Growth (YoY)"),
    "revenue_cagr_3y": ((1000 / 850) ** (1 / 3) - 1, "percent", "Revenue CAGR (3Y)"),
    "gross_margin": (0.40, "percent", "Gross Margin"),
    "ebitda_margin": (0.25, "percent", "EBITDA Margin"),
    "net_income_margin": (0.135, "percent", "Net Income Margin"),
    "fcf_margin": (0.18, "percent", "FCF Margin"),
    "fcf_conversion": (0.72, "percent", "FCF Conversion"),
    "capex_pct_revenue": (0.05, "percent", "Capex % of Revenue"),
    "net_debt_to_ebitda": (1.2, "multiple", "Net Debt / EBITDA"),
    "debt_to_ebitda": (1.6, "multiple", "Debt / EBITDA"),
    "interest_coverage": (12.5, "multiple", "Interest Coverage"),
    "roic": (0.1875, "percent", "Return on Invested Capital"),
    "current_ratio": (2.0, "ratio", "Current Ratio"),
    "nwc_pct_revenue": (0.15, "percent", "NWC % of Revenue"),
}


def make_tv(
    key: str,
    value: float | None,
    unit: str,
    label: str | None = None,
    warnings: list[str] | None = None,
) -> TracedValue:
    return TracedValue(
        key=key,
        label=label or key,
        value=value,
        unit=unit,  # type: ignore[arg-type]
        period="FY2025",
        formula="test fixture",
        inputs=[],
        warnings=warnings or [],
    )


def make_kpis(
    overrides: dict[str, float | None] | None = None,
    extra_warnings: dict[str, list[str]] | None = None,
) -> KpiResponse:
    overrides = overrides or {}
    extra_warnings = extra_warnings or {}
    kpis = []
    for key, (value, unit, label) in TESTCO_KPIS.items():
        v = overrides.get(key, value)
        kpis.append(make_tv(key, v, unit, label, extra_warnings.get(key)))
    return KpiResponse(
        ticker="TESTCO",
        as_of="2026-06-01",
        data_source="Sample data (illustrative figures)",
        kpis=kpis,
        series={},
    )


def make_profile(**overrides) -> CompanyProfile:
    base = dict(
        ticker="TESTCO",
        name="Testco Industrials Inc",
        sector="Industrials",
        industry="Industrial Machinery",
        exchange="NYSE",
        description="Synthetic test company used as the pytest fixture.",
        share_price=13.5,
        market_cap=1.35e9,
        enterprise_value=1.65e9,
        shares_outstanding=100e6,
        latest_fiscal_year=2025,
        revenue=1.0e9,
        ebitda=250e6,
        net_income=135e6,
        free_cash_flow=180e6,
        cash=100e6,
        total_debt=400e6,
        net_debt=300e6,
        data_source="Sample data (illustrative figures)",
        data_as_of="2026-06-01",
        warnings=[],
    )
    base.update(overrides)
    return CompanyProfile(**base)


def make_valuation(warnings: list[str] | None = None) -> ValuationResponse:
    multiples = [
        make_tv("ev_ebitda", 1650 / 250, "multiple", "EV / EBITDA"),
        make_tv("fcf_yield", 180 / 1350, "percent", "FCF Yield"),
        make_tv("market_cap", 1.35e9, "currency", "Market Capitalization"),
        make_tv("enterprise_value", 1.65e9, "currency", "Enterprise Value"),
    ]
    cases = []
    for name, multiple in (("low", 4.5), ("base", 6.5), ("high", 8.5)):
        implied_ev = multiple * 250e6
        implied_equity = implied_ev - 300e6
        implied_price = implied_equity / 100e6
        cases.append(
            ValuationCase(
                case=name,
                multiple=multiple,
                implied_ev=implied_ev,
                implied_equity=implied_equity,
                implied_share_price=implied_price,
                premium_vs_current=implied_price / 13.5 - 1,
            )
        )
    return ValuationResponse(
        ticker="TESTCO",
        as_of="2026-06-01",
        multiples=multiples,
        assumptions=ValuationAssumptions(low=4.5, base=6.5, high=8.5),
        range=cases,
        warnings=warnings or [],
    )


def make_lbo(warnings: list[str] | None = None) -> LboResponse:
    assumptions = LboAssumptions(
        entry_multiple=8.0,
        debt_multiple=4.0,
        revenue_growth=[0.05] * 5,
        ebitda_margin=[0.25] * 5,
        capex_pct_revenue=0.05,
        nwc_pct_revenue=0.02,
        tax_rate=0.25,
        interest_rate=0.08,
        mandatory_repayment_pct=0.05,
        exit_multiple=8.0,
        holding_period=5,
    )
    years = [
        LboYear(
            year=t,
            revenue=1.0e9 * 1.05**t,
            ebitda=0.25 * 1.0e9 * 1.05**t,
            capex=0.05 * 1.0e9 * 1.05**t,
            delta_nwc=1.0e6,
            interest=8.0e7,
            taxes=3.0e7,
            fcf=9.0e7,
            debt_repaid=9.0e7,
            ending_debt=max(0.0, 1.0e9 - 9.0e7 * t),
            ending_cash=0.0,
        )
        for t in range(1, 6)
    ]
    grid = SensitivityGrid(
        row_label="Exit multiple",
        col_label="Growth shift",
        rows=[8.0],
        cols=[0.0],
        values=[[0.2]],
    )
    return LboResponse(
        ticker="TESTCO",
        entry=LboEntry(
            entry_ebitda=250e6,
            entry_revenue=1.0e9,
            entry_ev=2.0e9,
            opening_debt=1.0e9,
            sponsor_equity=1.0e9,
            equity_pct=0.5,
        ),
        years=years,
        exit=LboExit(
            exit_ebitda=319e6,
            exit_ev=2.552e9,
            ending_debt=550e6,
            ending_cash=0.0,
            exit_equity=2.002e9,
            mom=2.002,
            irr=0.1489,
        ),
        sensitivities=LboSensitivities(
            irr_exit_vs_growth=grid,
            irr_entry_vs_exit=grid,
            mom_exit_vs_margin=grid,
        ),
        assumptions=assumptions,
        warnings=warnings or [],
    )


def full_memo(**kwargs) -> MemoResponse:
    profile = kwargs.get("profile", make_profile())
    kpis = kwargs.get("kpis", make_kpis())
    valuation = kwargs.get("valuation", make_valuation())
    lbo = kwargs.get("lbo", make_lbo())
    score = kwargs.get(
        "score", compute_score(kpis, valuation.multiples if valuation else None)
    )
    return generate_memo(profile, kpis, valuation, lbo, score)


def section_map(memo: MemoResponse) -> dict[str, str]:
    return {s.key: s.content for s in memo.sections}


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------


def test_all_nine_sections_present_in_order() -> None:
    memo = full_memo()
    assert [s.key for s in memo.sections] == MEMO_SECTION_KEYS
    assert len(memo.sections) == 9
    for section in memo.sections:
        assert section.title
        assert section.content.strip()


def test_rating_mirrors_score_and_ticker() -> None:
    kpis = make_kpis()
    valuation = make_valuation()
    score = compute_score(kpis, valuation.multiples)
    memo = generate_memo(make_profile(), kpis, valuation, make_lbo(), score)
    assert memo.rating == score.rating
    assert memo.ticker == "TESTCO"
    assert memo.disclaimer == (
        "Screening tool for educational and research purposes. Not investment advice."
    )


# ---------------------------------------------------------------------------
# Data gaps
# ---------------------------------------------------------------------------


def test_injected_warnings_appear_in_data_gaps() -> None:
    profile_warning = "Market data unavailable"
    kpi_warning = "EBITDA derived as Operating income + D&A"
    valuation_warning = "EV/EBITDA unavailable; default base 8.0x applied"
    lbo_warning = "Negative FCF in year 2; no revolver modeled"

    memo = full_memo(
        profile=make_profile(warnings=[profile_warning]),
        kpis=make_kpis(extra_warnings={"ebitda_margin": [kpi_warning]}),
        valuation=make_valuation(warnings=[valuation_warning]),
        lbo=make_lbo(warnings=[lbo_warning]),
    )
    for warning in (profile_warning, kpi_warning, valuation_warning, lbo_warning):
        assert warning in memo.data_gaps
    gaps_content = section_map(memo)["data_gaps"]
    for warning in (profile_warning, kpi_warning, valuation_warning, lbo_warning):
        assert warning in gaps_content


def test_no_gaps_line_when_clean() -> None:
    memo = full_memo()
    assert memo.data_gaps == []
    assert section_map(memo)["data_gaps"] == (
        "No material data gaps identified in the fields used."
    )


# ---------------------------------------------------------------------------
# Never the literal strings "None" / "nan"
# ---------------------------------------------------------------------------


def assert_no_none_or_nan(memo: MemoResponse) -> None:
    for section in memo.sections:
        for text in (section.title, section.content):
            assert not re.search(r"\bNone\b", text), (section.key, text)
            assert not re.search(r"\bnan\b", text), (section.key, text)


def test_no_none_or_nan_with_full_data() -> None:
    assert_no_none_or_nan(full_memo())


def test_no_none_or_nan_with_sparse_data() -> None:
    sparse_profile = make_profile(
        sector=None,
        industry=None,
        exchange=None,
        description=None,
        share_price=None,
        market_cap=None,
        enterprise_value=None,
        shares_outstanding=None,
        latest_fiscal_year=None,
        revenue=None,
        ebitda=None,
        net_income=None,
        free_cash_flow=None,
        cash=None,
        total_debt=None,
        net_debt=None,
        data_as_of=None,
        warnings=["Market data unavailable"],
    )
    sparse_kpis = make_kpis(overrides={k: None for k in TESTCO_KPIS})
    score = compute_score(sparse_kpis, None)
    memo = generate_memo(sparse_profile, sparse_kpis, None, None, score)
    assert [s.key for s in memo.sections] == MEMO_SECTION_KEYS
    assert_no_none_or_nan(memo)
    # Missing values are stated as missing, not interpolated.
    assert "not available" in section_map(memo)["kpi_summary"]


# ---------------------------------------------------------------------------
# Thesis / risk rules
# ---------------------------------------------------------------------------


def test_thesis_bullets_with_strong_metrics() -> None:
    thesis = section_map(full_memo())["investment_thesis"]
    assert "Strong cash conversion supports deleveraging" in thesis
    assert "72.0%" in thesis  # FCF conversion cited as a formatted value
    assert "Limited affirmative thesis support" not in thesis


def test_thesis_fallback_when_fewer_than_two_bullets() -> None:
    weak = make_kpis(
        overrides={
            "fcf_conversion": 0.30,
            "revenue_cagr_3y": 0.01,
            "ebitda_margin": 0.10,
            "net_debt_to_ebitda": 3.5,
        }
    )
    memo = full_memo(kpis=weak, score=compute_score(weak, make_valuation().multiples))
    thesis = section_map(memo)["investment_thesis"]
    assert "Limited affirmative thesis support from available data." in thesis


def test_key_risks_always_include_public_market_line() -> None:
    line = "Public-market valuation may already reflect the qualities identified above."
    assert line in section_map(full_memo())["key_risks"]
    sparse_kpis = make_kpis(overrides={k: None for k in TESTCO_KPIS})
    sparse_memo = generate_memo(
        make_profile(), sparse_kpis, None, None, compute_score(sparse_kpis, None)
    )
    assert line in section_map(sparse_memo)["key_risks"]


def test_risk_rules_fire_with_cited_values() -> None:
    risky = make_kpis(
        overrides={
            "net_debt_to_ebitda": 3.8,
            "revenue_growth_yoy": -0.04,
            "fcf_margin": 0.02,
            "interest_coverage": 2.1,
        }
    )
    memo = full_memo(kpis=risky, score=compute_score(risky, make_valuation().multiples))
    risks = section_map(memo)["key_risks"]
    assert "3.8x" in risks  # leverage risk
    assert "-4.0%" in risks  # declining revenue
    assert "2.0%" in risks  # weak FCF margin
    assert "2.1x" in risks  # thin coverage


# ---------------------------------------------------------------------------
# Formatting and section content
# ---------------------------------------------------------------------------


def test_number_formatting_conventions() -> None:
    sections = section_map(full_memo())
    highlights = sections["financial_highlights"]
    assert "$1.0bn" in highlights  # revenue 1,000m auto-scaled
    assert "$250.0m" in highlights  # EBITDA
    kpi_summary = sections["kpi_summary"]
    assert "25.0%" in kpi_summary  # ebitda margin
    assert "1.2x" in kpi_summary  # net debt / EBITDA
    overview = sections["company_overview"]
    assert "$13.50" in overview  # share price
    assert "Sample data (illustrative figures)" in overview  # source cited


def test_lbo_and_valuation_sections_cite_model_outputs() -> None:
    sections = section_map(full_memo())
    lbo = sections["lbo_case_summary"]
    assert "8.0x" in lbo  # entry multiple
    assert "$2.0bn" in lbo  # entry EV
    assert "2.0x" in lbo  # MoM
    valuation = sections["valuation_view"]
    assert "6.5x" in valuation  # base multiple
    assert "$13.25" in valuation  # base implied share price


def test_lbo_none_states_unavailable() -> None:
    kpis = make_kpis()
    valuation = make_valuation()
    memo = generate_memo(
        make_profile(), kpis, valuation, None, compute_score(kpis, valuation.multiples)
    )
    content = section_map(memo)["lbo_case_summary"]
    assert "not available" in content
    assert_no_none_or_nan(memo)


def test_screening_view_cites_score_and_rating() -> None:
    kpis = make_kpis()
    valuation = make_valuation()
    score = compute_score(kpis, valuation.multiples)
    memo = generate_memo(make_profile(), kpis, valuation, make_lbo(), score)
    view = section_map(memo)["screening_view"]
    assert f"{score.total:.1f}/100" in view
    assert score.rating in view
    assert score.disclaimer in view
