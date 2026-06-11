"""KPI and PE-diagnostics tests (spec §15, §19.1) against the TESTCO fixture."""

import pytest

from app.kpis import compute_kpis
from app.schemas.company import CompanyDataBundle
from app.schemas.kpi import TracedValue

REL = 1e-6

EXPECTED_KEYS = {
    "revenue_growth_yoy",
    "revenue_cagr_3y",
    "gross_margin",
    "ebitda_margin",
    "net_income_margin",
    "fcf_margin",
    "fcf_conversion",
    "capex_pct_revenue",
    "net_debt_to_ebitda",
    "debt_to_ebitda",
    "interest_coverage",
    "roic",
    "current_ratio",
    "nwc_pct_revenue",
}


def kpi_map(bundle: CompanyDataBundle) -> dict[str, TracedValue]:
    response = compute_kpis(bundle)
    return {k.key: k for k in response.kpis}


def test_all_14_kpis_present(testco_bundle: CompanyDataBundle) -> None:
    response = compute_kpis(testco_bundle)
    assert len(response.kpis) == 14
    assert {k.key for k in response.kpis} == EXPECTED_KEYS
    assert response.ticker == "TESTCO"
    assert response.data_source == "Sample data (illustrative figures)"


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("ebitda_margin", 0.25),
        ("fcf_conversion", 0.72),
        ("net_debt_to_ebitda", 1.2),
        ("interest_coverage", 12.5),
        ("revenue_growth_yoy", 1000 / 950 - 1),
        ("revenue_cagr_3y", (1000 / 850) ** (1 / 3) - 1),
        ("current_ratio", 2.0),
        ("capex_pct_revenue", 0.05),
        ("gross_margin", 0.40),
        ("net_income_margin", 0.135),
        ("fcf_margin", 0.18),
        ("debt_to_ebitda", 1.6),
        # effective tax = 45 / (135 + 45) = 0.25 -> 200 * 0.75 / (400 + 500 - 100)
        ("roic", 0.1875),
        ("nwc_pct_revenue", 0.15),
    ],
)
def test_testco_kpi_values(
    testco_bundle: CompanyDataBundle, key: str, expected: float
) -> None:
    kpi = kpi_map(testco_bundle)[key]
    assert kpi.value == pytest.approx(expected, rel=REL)
    assert kpi.warnings == []


def test_traceability_metadata(testco_bundle: CompanyDataBundle) -> None:
    kpis = kpi_map(testco_bundle)
    em = kpis["ebitda_margin"]
    assert em.unit == "percent"
    assert em.period == "FY2025"
    assert em.formula == "EBITDA / Revenue"
    input_fields = {i.field for i in em.inputs}
    assert input_fields == {"ebitda", "revenue"}
    assert {i.value for i in em.inputs} == {250e6, 1000e6}

    assert kpis["net_debt_to_ebitda"].unit == "multiple"
    assert kpis["interest_coverage"].unit == "multiple"
    assert kpis["current_ratio"].unit == "ratio"

    growth = kpis["revenue_growth_yoy"]
    assert growth.period == "FY2024→FY2025"

    cagr = kpis["revenue_cagr_3y"]
    assert cagr.period == "FY2022→FY2025"
    cagr_input_periods = {i.period for i in cagr.inputs}
    assert cagr_input_periods == {"FY2022", "FY2025"}


def test_missing_field_gives_none_and_warning(testco_bundle: CompanyDataBundle) -> None:
    bundle = testco_bundle.model_copy(deep=True)
    bundle.financials[-1].ebitda = None
    kpis = kpi_map(bundle)  # must not raise
    for key in ("ebitda_margin", "fcf_conversion", "net_debt_to_ebitda",
                "debt_to_ebitda", "interest_coverage"):
        assert kpis[key].value is None, key
        assert kpis[key].warnings, key
    # Unrelated KPIs unaffected.
    assert kpis["gross_margin"].value == pytest.approx(0.40, rel=REL)


def test_missing_revenue_everywhere(testco_bundle: CompanyDataBundle) -> None:
    bundle = testco_bundle.model_copy(deep=True)
    for year in bundle.financials:
        year.revenue = None
    kpis = kpi_map(bundle)
    for key in ("revenue_growth_yoy", "revenue_cagr_3y", "gross_margin",
                "ebitda_margin", "net_income_margin", "fcf_margin",
                "capex_pct_revenue", "nwc_pct_revenue"):
        assert kpis[key].value is None, key
        assert kpis[key].warnings, key


def test_empty_financials_never_raises(testco_bundle: CompanyDataBundle) -> None:
    bundle = testco_bundle.model_copy(deep=True)
    bundle.financials = []
    response = compute_kpis(bundle)
    assert len(response.kpis) == 14
    for kpi in response.kpis:
        assert kpi.value is None
        assert kpi.warnings
    assert response.series == {}


def test_interest_coverage_zero_interest(testco_bundle: CompanyDataBundle) -> None:
    bundle = testco_bundle.model_copy(deep=True)
    bundle.financials[-1].interest_expense = 0.0
    kpi = kpi_map(bundle)["interest_coverage"]
    assert kpi.value is None
    assert kpi.warnings


def test_roic_effective_tax_fallback(testco_bundle: CompanyDataBundle) -> None:
    bundle = testco_bundle.model_copy(deep=True)
    bundle.financials[-1].tax_expense = None
    kpi = kpi_map(bundle)["roic"]
    # Fallback 0.25 happens to equal TESTCO's actual effective tax.
    assert kpi.value == pytest.approx(0.1875, rel=REL)
    assert any("fallback" in w for w in kpi.warnings)


def test_roic_effective_tax_clamped_high(testco_bundle: CompanyDataBundle) -> None:
    bundle = testco_bundle.model_copy(deep=True)
    bundle.financials[-1].tax_expense = 100e6
    bundle.financials[-1].net_income = 50e6
    # raw effective tax = 100/150 ≈ 0.667 -> clamped to 0.5
    kpi = kpi_map(bundle)["roic"]
    assert kpi.value == pytest.approx(200e6 * 0.5 / 800e6, rel=REL)
    assert any("clamped" in w for w in kpi.warnings)


def test_roic_effective_tax_clamped_low(testco_bundle: CompanyDataBundle) -> None:
    bundle = testco_bundle.model_copy(deep=True)
    bundle.financials[-1].tax_expense = -10e6
    bundle.financials[-1].net_income = 135e6
    # raw effective tax = -10/125 < 0 -> clamped to 0
    kpi = kpi_map(bundle)["roic"]
    assert kpi.value == pytest.approx(200e6 / 800e6, rel=REL)


def test_cagr_uses_available_span(testco_bundle: CompanyDataBundle) -> None:
    bundle = testco_bundle.model_copy(deep=True)
    bundle.financials = bundle.financials[-2:]  # FY2024, FY2025 only
    kpi = kpi_map(bundle)["revenue_cagr_3y"]
    assert kpi.value == pytest.approx(1000 / 950 - 1, rel=REL)
    assert kpi.period == "FY2024→FY2025"
    assert kpi.warnings  # shorter span flagged


def test_series_keys_and_lengths(testco_bundle: CompanyDataBundle) -> None:
    response = compute_kpis(testco_bundle)
    expected_series = {
        "revenue", "ebitda", "free_cash_flow", "total_debt",
        "dividends_paid", "share_buybacks",
        "gross_margin", "ebitda_margin", "net_income_margin", "fcf_margin",
        "net_debt_to_ebitda",
    }
    assert set(response.series) == expected_series
    for name in expected_series:
        assert len(response.series[name]) == 5, name
        assert [p.fiscal_year for p in response.series[name]] == list(range(2021, 2026))


def test_series_values_spot_check(testco_bundle: CompanyDataBundle) -> None:
    series = compute_kpis(testco_bundle).series
    assert [p.value for p in series["revenue"]] == [
        800e6, 850e6, 900e6, 950e6, 1000e6,
    ]
    assert [p.value for p in series["ebitda"]] == [
        180e6, 200e6, 215e6, 235e6, 250e6,
    ]
    assert series["free_cash_flow"][-1].value == pytest.approx(180e6, rel=REL)
    assert series["total_debt"][0].value == pytest.approx(460e6, rel=REL)
    assert series["gross_margin"][-1].value == pytest.approx(0.40, rel=REL)
    assert series["ebitda_margin"][-1].value == pytest.approx(0.25, rel=REL)
    assert series["net_income_margin"][-1].value == pytest.approx(0.135, rel=REL)
    assert series["fcf_margin"][-1].value == pytest.approx(0.18, rel=REL)
    # FY2021: (460 - 60) / 180
    assert series["net_debt_to_ebitda"][0].value == pytest.approx(400 / 180, rel=REL)
    assert series["net_debt_to_ebitda"][-1].value == pytest.approx(1.2, rel=REL)


def test_series_skips_years_with_missing_inputs(
    testco_bundle: CompanyDataBundle,
) -> None:
    bundle = testco_bundle.model_copy(deep=True)
    bundle.financials[2].ebitda = None  # FY2023
    series = compute_kpis(bundle).series
    for name in ("ebitda", "ebitda_margin", "net_debt_to_ebitda"):
        years = [p.fiscal_year for p in series[name]]
        assert years == [2021, 2022, 2024, 2025], name
    assert len(series["revenue"]) == 5  # untouched series keep all years


# ---------------------------------------------------------------------------
# PE diagnostics (spec §19.1)
# ---------------------------------------------------------------------------

DIAG_REL = 1e-4

EXPECTED_DIAGNOSTIC_KEYS = [
    "dso",
    "dsi",
    "dpo",
    "cash_conversion_cycle",
    "capital_return_pct_fcf",
    "buyback_pct_fcf",
    "incremental_ebitda_margin",
]


def diag_map(bundle: CompanyDataBundle) -> dict[str, TracedValue]:
    response = compute_kpis(bundle)
    return {d.key: d for d in response.diagnostics}


def test_all_7_diagnostics_present_with_units(
    testco_bundle: CompanyDataBundle,
) -> None:
    response = compute_kpis(testco_bundle)
    assert [d.key for d in response.diagnostics] == EXPECTED_DIAGNOSTIC_KEYS
    units = {d.key: d.unit for d in response.diagnostics}
    for key in ("dso", "dsi", "dpo", "cash_conversion_cycle"):
        assert units[key] == "days", key
    for key in (
        "capital_return_pct_fcf", "buyback_pct_fcf", "incremental_ebitda_margin",
    ):
        assert units[key] == "percent", key


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        # TESTCO FY2025 bindings (spec §19.1): receivables 120m, inventory 80m,
        # payables 90m, dividends 30m, buybacks 50m over revenue 1000m,
        # COGS 600m, FCF 180m; ΔEBITDA 15m / Δrevenue 50m.
        ("dso", 43.8),
        ("dsi", 48.6667),
        ("dpo", 54.75),
        ("cash_conversion_cycle", 37.7167),
        # 0.4444 per §19.1; exact 4/9 = 0.44444… sits just outside rel=1e-4 of
        # the 4-decimal rounding, so the exact fraction is pinned instead.
        ("capital_return_pct_fcf", 80 / 180),
        ("buyback_pct_fcf", 0.2778),
        ("incremental_ebitda_margin", 0.30),
    ],
)
def test_testco_diagnostic_values(
    testco_bundle: CompanyDataBundle, key: str, expected: float
) -> None:
    diag = diag_map(testco_bundle)[key]
    assert diag.value == pytest.approx(expected, rel=DIAG_REL)
    assert diag.warnings == []


def test_diagnostic_periods(testco_bundle: CompanyDataBundle) -> None:
    diags = diag_map(testco_bundle)
    for key in EXPECTED_DIAGNOSTIC_KEYS[:-1]:
        assert diags[key].period == "FY2025", key
    assert diags["incremental_ebitda_margin"].period == "FY2024→FY2025"


def test_ccc_inputs_are_component_day_metrics(
    testco_bundle: CompanyDataBundle,
) -> None:
    ccc = diag_map(testco_bundle)["cash_conversion_cycle"]
    by_field = {i.field: i.value for i in ccc.inputs}
    assert by_field == {
        "dso": pytest.approx(43.8, rel=DIAG_REL),
        "dsi": pytest.approx(48.6667, rel=DIAG_REL),
        "dpo": pytest.approx(54.75, rel=DIAG_REL),
    }


def test_missing_receivables_nones_dso_and_ccc_only(
    testco_bundle: CompanyDataBundle,
) -> None:
    bundle = testco_bundle.model_copy(deep=True)
    bundle.financials[-1].receivables = None
    diags = diag_map(bundle)  # must not raise
    for key in ("dso", "cash_conversion_cycle"):
        assert diags[key].value is None, key
        assert diags[key].warnings, key
    # Unrelated diagnostics unaffected.
    assert diags["dsi"].value == pytest.approx(48.6667, rel=DIAG_REL)
    assert diags["dpo"].value == pytest.approx(54.75, rel=DIAG_REL)


def test_missing_dividends_nones_capital_return_only(
    testco_bundle: CompanyDataBundle,
) -> None:
    bundle = testco_bundle.model_copy(deep=True)
    bundle.financials[-1].dividends_paid = None
    diags = diag_map(bundle)
    assert diags["capital_return_pct_fcf"].value is None
    assert diags["capital_return_pct_fcf"].warnings
    assert diags["buyback_pct_fcf"].value == pytest.approx(0.2778, rel=DIAG_REL)


def test_incremental_margin_requires_prior_year(
    testco_bundle: CompanyDataBundle,
) -> None:
    bundle = testco_bundle.model_copy(deep=True)
    bundle.financials = bundle.financials[-1:]  # FY2025 only
    diag = diag_map(bundle)["incremental_ebitda_margin"]
    assert diag.value is None
    assert diag.warnings


def test_incremental_margin_zero_revenue_delta(
    testco_bundle: CompanyDataBundle,
) -> None:
    bundle = testco_bundle.model_copy(deep=True)
    bundle.financials[-1].revenue = bundle.financials[-2].revenue
    diag = diag_map(bundle)["incremental_ebitda_margin"]
    assert diag.value is None
    assert diag.warnings


def test_diagnostics_never_raise_on_empty_financials(
    testco_bundle: CompanyDataBundle,
) -> None:
    bundle = testco_bundle.model_copy(deep=True)
    bundle.financials = []
    response = compute_kpis(bundle)
    assert len(response.diagnostics) == 7
    for diag in response.diagnostics:
        assert diag.value is None
        assert diag.warnings


def test_capital_return_series_present(testco_bundle: CompanyDataBundle) -> None:
    series = compute_kpis(testco_bundle).series
    for name in ("dividends_paid", "share_buybacks"):
        assert [p.fiscal_year for p in series[name]] == list(range(2021, 2026)), name
    assert series["dividends_paid"][-1].value == pytest.approx(30e6, rel=REL)
    assert series["share_buybacks"][-1].value == pytest.approx(50e6, rel=REL)
