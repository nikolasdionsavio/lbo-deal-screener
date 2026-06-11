"""Normalization derivations and derived_fields bookkeeping (spec §4, §15)."""

import pytest

from app.normalization import apply_derivations, normalize_financials
from app.schemas.company import CompanyDataBundle
from app.schemas.financials import FiscalYearFinancials

REL_TOL = 1e-6


def test_derives_gross_profit_ebitda_fcf_and_records_derived_fields() -> None:
    year = FiscalYearFinancials(
        fiscal_year=2024,
        revenue=500e6,
        cost_of_revenue=300e6,
        operating_income=100e6,
        depreciation_amortization=25e6,
        operating_cash_flow=110e6,
        capex=30e6,
    )
    out = apply_derivations(year)
    assert out.gross_profit == pytest.approx(200e6, rel=REL_TOL)
    assert out.ebitda == pytest.approx(125e6, rel=REL_TOL)
    assert out.free_cash_flow == pytest.approx(80e6, rel=REL_TOL)
    assert out.derived_fields == ["gross_profit", "ebitda", "free_cash_flow"]


def test_fcf_derivation_path_is_ocf_minus_positive_capex() -> None:
    # TESTCO FY2025 inputs: OCF 230m, capex 50m (stored positive) -> FCF 180m.
    year = FiscalYearFinancials(
        fiscal_year=2025, operating_cash_flow=230e6, capex=50e6
    )
    out = apply_derivations(year)
    assert out.free_cash_flow == pytest.approx(180e6, rel=REL_TOL)
    assert out.derived_fields == ["free_cash_flow"]


def test_stated_fields_are_left_untouched(testco_bundle: CompanyDataBundle) -> None:
    latest = testco_bundle.financials[-1].model_copy(deep=True)
    out = apply_derivations(latest)
    assert out.gross_profit == pytest.approx(400e6, rel=REL_TOL)
    assert out.ebitda == pytest.approx(250e6, rel=REL_TOL)
    assert out.free_cash_flow == pytest.approx(180e6, rel=REL_TOL)
    assert out.derived_fields == []  # everything was stated, nothing derived


def test_partial_inputs_leave_fields_none_without_bookkeeping() -> None:
    year = FiscalYearFinancials(
        fiscal_year=2024,
        revenue=500e6,  # cost_of_revenue missing -> no gross profit
        operating_income=100e6,  # D&A missing -> no EBITDA
        operating_cash_flow=110e6,  # capex missing -> no FCF
    )
    out = apply_derivations(year)
    assert out.gross_profit is None
    assert out.ebitda is None
    assert out.free_cash_flow is None
    assert out.derived_fields == []


def test_apply_derivations_is_idempotent() -> None:
    year = FiscalYearFinancials(
        fiscal_year=2024, operating_income=100e6, depreciation_amortization=25e6
    )
    apply_derivations(year)
    apply_derivations(year)
    assert year.derived_fields == ["ebitda"]


def test_normalize_financials_applies_to_every_year() -> None:
    years = [
        FiscalYearFinancials(fiscal_year=2023, revenue=450e6, cost_of_revenue=280e6),
        FiscalYearFinancials(fiscal_year=2024, revenue=500e6, cost_of_revenue=300e6),
    ]
    out = normalize_financials(years)
    assert len(out) == 2
    assert out[0].gross_profit == pytest.approx(170e6, rel=REL_TOL)
    assert out[1].gross_profit == pytest.approx(200e6, rel=REL_TOL)
    assert all(y.derived_fields == ["gross_profit"] for y in out)
