"""Deal score tests (spec §15, against the §9 component table).

KpiResponse objects are built by hand (TESTCO-shaped values) so the scoring
module is tested in isolation from app.kpis.
"""

import pytest

from app.schemas.kpi import KpiResponse, TracedValue
from app.scoring import COMPONENT_SPECS, compute_score, linear_score

REL = 1e-6

# TESTCO FY2025 KPI values (spec §15), as (value, unit).
TESTCO_KPI_VALUES: dict[str, tuple[float, str]] = {
    "revenue_growth_yoy": (1000 / 950 - 1, "percent"),
    "revenue_cagr_3y": ((1000 / 850) ** (1 / 3) - 1, "percent"),
    "gross_margin": (0.40, "percent"),
    "ebitda_margin": (0.25, "percent"),
    "net_income_margin": (0.135, "percent"),
    "fcf_margin": (0.18, "percent"),
    "fcf_conversion": (0.72, "percent"),
    "capex_pct_revenue": (0.05, "percent"),
    "net_debt_to_ebitda": (1.2, "multiple"),
    "debt_to_ebitda": (1.6, "multiple"),
    "interest_coverage": (12.5, "multiple"),
    "roic": (0.1875, "percent"),
    "current_ratio": (2.0, "ratio"),
    "nwc_pct_revenue": (0.15, "percent"),
}

# TESTCO valuation multiples: EV/EBITDA = 1650/250, FCF yield = 180/1350.
TESTCO_EV_EBITDA = 1650 / 250
TESTCO_FCF_YIELD = 180 / 1350


def make_tv(key: str, value: float | None, unit: str, label: str | None = None) -> TracedValue:
    return TracedValue(
        key=key,
        label=label or key,
        value=value,
        unit=unit,  # type: ignore[arg-type]
        period="FY2025",
        formula="test fixture",
        inputs=[],
        warnings=[],
    )


def make_kpi_response(values: dict[str, tuple[float | None, str]]) -> KpiResponse:
    return KpiResponse(
        ticker="TESTCO",
        as_of="2026-06-01",
        data_source="Sample data (illustrative figures)",
        kpis=[make_tv(k, v, u) for k, (v, u) in values.items()],
        series={},
    )


def make_valuation_multiples() -> list[TracedValue]:
    return [
        make_tv("ev_ebitda", TESTCO_EV_EBITDA, "multiple", "EV / EBITDA"),
        make_tv("fcf_yield", TESTCO_FCF_YIELD, "percent", "FCF Yield"),
    ]


def component_map(score_response):
    return {c.key: c for c in score_response.components}


# ---------------------------------------------------------------------------
# Weights and linear_score helper
# ---------------------------------------------------------------------------


def test_weights_sum_to_one() -> None:
    assert sum(spec.weight for spec in COMPONENT_SPECS) == pytest.approx(1.0)


def test_linear_score_midpoint_and_clamping() -> None:
    assert linear_score(0.075, 0.0, 0.15) == pytest.approx(50.0)
    assert linear_score(-0.05, 0.0, 0.15) == 0.0
    assert linear_score(0.30, 0.0, 0.15) == 100.0


def test_linear_score_inverted_range() -> None:
    # worst > best: lower is better (e.g. net_debt_to_ebitda 4.0x -> 0.0x).
    assert linear_score(1.0, 4.0, 0.0) == pytest.approx(75.0)
    assert linear_score(5.0, 4.0, 0.0) == 0.0
    assert linear_score(-1.0, 4.0, 0.0) == 100.0


def test_linear_score_rejects_degenerate_range() -> None:
    with pytest.raises(ValueError):
        linear_score(1.0, 2.0, 2.0)


# ---------------------------------------------------------------------------
# TESTCO-shaped scoring
# ---------------------------------------------------------------------------


def expected_testco_total() -> float:
    """Independent recomputation of the §9 table on TESTCO values."""
    comp_scores = {
        "growth": linear_score(TESTCO_KPI_VALUES["revenue_cagr_3y"][0], 0.0, 0.15),
        "margins": (linear_score(0.25, 0.05, 0.30) + linear_score(0.40, 0.20, 0.60)) / 2,
        "cash_conversion": (linear_score(0.72, 0.20, 0.80) + linear_score(0.18, 0.0, 0.15)) / 2,
        "leverage_capacity": (linear_score(1.2, 4.0, 0.0) + linear_score(12.5, 1.0, 8.0)) / 2,
        "valuation": (
            linear_score(TESTCO_EV_EBITDA, 16.0, 6.0)
            + linear_score(TESTCO_FCF_YIELD, 0.02, 0.08)
        ) / 2,
        "balance_sheet_risk": (linear_score(2.0, 0.8, 2.0) + linear_score(1.6, 5.0, 1.0)) / 2,
    }
    weights = {spec.key: spec.weight for spec in COMPONENT_SPECS}
    return round(sum(weights[k] * s for k, s in comp_scores.items()), 1)


def test_testco_total_in_range_and_matches_table() -> None:
    score = compute_score(make_kpi_response(TESTCO_KPI_VALUES), make_valuation_multiples())
    assert 0.0 <= score.total <= 100.0
    assert score.total == pytest.approx(expected_testco_total(), abs=0.051)
    assert score.ticker == "TESTCO"
    assert score.as_of == "2026-06-01"
    assert len(score.components) == 6
    # No redistribution: effective weights equal nominal weights and sum to 1.
    for comp in score.components:
        assert comp.score is not None
        assert comp.effective_weight == pytest.approx(comp.weight, rel=REL)
    assert sum(c.effective_weight for c in score.components) == pytest.approx(1.0)


def test_reasons_cite_formatted_values() -> None:
    score = compute_score(make_kpi_response(TESTCO_KPI_VALUES), make_valuation_multiples())
    comps = component_map(score)
    # 3y CAGR (1000/850)^(1/3)-1 = 5.6% -> 37/100 on the 0-15% scale.
    assert "5.6%" in comps["growth"].reason
    assert "37/100" in comps["growth"].reason
    assert "0–15% scale" in comps["growth"].reason
    assert "25.0%" in comps["margins"].reason
    assert "40.0%" in comps["margins"].reason
    assert "1.2x" in comps["leverage_capacity"].reason
    assert "12.5x" in comps["leverage_capacity"].reason
    assert "6.6x" in comps["valuation"].reason
    assert "1.6x" in comps["balance_sheet_risk"].reason


def test_missing_valuation_component_redistributes_weight() -> None:
    score = compute_score(make_kpi_response(TESTCO_KPI_VALUES), None)
    comps = component_map(score)
    valuation = comps["valuation"]
    assert valuation.score is None
    assert valuation.effective_weight == 0.0
    assert valuation.weighted_points is None
    assert valuation.warnings  # redistribution warning recorded
    # Remaining weight (0.85) is scaled back up to 1.0 proportionally.
    for key, comp in comps.items():
        if key == "valuation":
            continue
        assert comp.effective_weight == pytest.approx(comp.weight / 0.85, rel=REL)
    assert sum(c.effective_weight for c in score.components) == pytest.approx(1.0)
    assert 0.0 <= score.total <= 100.0


def test_component_none_when_all_inputs_value_none() -> None:
    values = dict(TESTCO_KPI_VALUES)
    values["fcf_conversion"] = (None, "percent")
    values["fcf_margin"] = (None, "percent")
    score = compute_score(make_kpi_response(values), make_valuation_multiples())
    comps = component_map(score)
    assert comps["cash_conversion"].score is None
    assert comps["cash_conversion"].effective_weight == 0.0
    assert comps["cash_conversion"].warnings
    assert sum(c.effective_weight for c in score.components) == pytest.approx(1.0)
    assert 0.0 <= score.total <= 100.0


def test_partial_inputs_still_score_component() -> None:
    values = dict(TESTCO_KPI_VALUES)
    values["gross_margin"] = (None, "percent")
    score = compute_score(make_kpi_response(values), make_valuation_multiples())
    comps = component_map(score)
    margins = comps["margins"]
    # Only ebitda_margin available: component = that single input's score.
    assert margins.score == pytest.approx(linear_score(0.25, 0.05, 0.30), rel=REL)
    assert margins.effective_weight == pytest.approx(margins.weight, rel=REL)
    assert margins.warnings  # missing gross margin flagged


def test_all_components_missing_is_graceful() -> None:
    values = {k: (None, u) for k, (_, u) in TESTCO_KPI_VALUES.items()}
    score = compute_score(make_kpi_response(values), None)
    assert score.total == 0.0
    assert score.rating == "Pass"
    assert all(c.score is None for c in score.components)


# ---------------------------------------------------------------------------
# Rating boundaries (synthetic component scores)
# ---------------------------------------------------------------------------


def uniform_score_inputs(target: float) -> tuple[KpiResponse, list[TracedValue]]:
    """Build inputs where every §9 input scores exactly `target`/100."""
    kpi_values: dict[str, tuple[float | None, str]] = {}
    valuation: list[TracedValue] = []
    for spec in COMPONENT_SPECS:
        for inp in spec.inputs:
            value = inp.worst + (inp.best - inp.worst) * target / 100.0
            if inp.source == "kpi":
                kpi_values[inp.key] = (value, inp.unit)
            else:
                valuation.append(make_tv(inp.key, value, inp.unit))
    return make_kpi_response(kpi_values), valuation


@pytest.mark.parametrize(
    ("target", "expected_rating"),
    [
        (100.0, "Attractive"),
        (70.0, "Attractive"),  # boundary: >= 70
        (69.0, "Watchlist"),
        (50.0, "Watchlist"),  # boundary: >= 50
        (49.0, "Pass"),
        (0.0, "Pass"),
    ],
)
def test_rating_boundaries(target: float, expected_rating: str) -> None:
    kpis, valuation = uniform_score_inputs(target)
    score = compute_score(kpis, valuation)
    assert score.total == pytest.approx(target, abs=0.051)
    assert score.rating == expected_rating


def test_disclaimer_verbatim() -> None:
    score = compute_score(make_kpi_response(TESTCO_KPI_VALUES), make_valuation_multiples())
    assert score.disclaimer == (
        "Screening score based on mechanical rules. Not an investment recommendation."
    )


# ---------------------------------------------------------------------------
# Currency-aware formatters (spec §4: USD $, GBP £, EUR €, else "CODE " prefix)
# ---------------------------------------------------------------------------


def test_fmt_currency_default_and_known_symbols() -> None:
    from app.scoring.model import fmt_currency

    assert fmt_currency(1.5e9) == "$1.5bn"
    assert fmt_currency(1.5e9, "USD") == "$1.5bn"
    assert fmt_currency(1.5e9, "GBP") == "£1.5bn"
    assert fmt_currency(2.3e12, "EUR") == "€2.3tn"
    assert fmt_currency(-2.5e6, "GBP") == "-£2.5m"
    assert fmt_currency(950.0, "gbp") == "£950"  # case-insensitive code


def test_fmt_currency_unknown_code_prefixes_iso_code() -> None:
    from app.scoring.model import fmt_currency

    assert fmt_currency(1.2e9, "SEK") == "SEK 1.2bn"
    assert fmt_currency(-3.4e6, "CHF") == "-CHF 3.4m"


def test_fmt_value_per_share_uses_currency_prefix() -> None:
    from app.scoring.model import fmt_value

    assert fmt_value(13.5, "per_share") == "$13.50"
    assert fmt_value(2.5, "per_share", "GBP") == "£2.50"
    assert fmt_value(13.5, "per_share", "SEK") == "SEK 13.50"
