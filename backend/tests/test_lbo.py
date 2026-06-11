"""LBO engine, defaults and sensitivity tests (spec §8, §15)."""

import pytest

from app.lbo.defaults import derive_defaults
from app.lbo.engine import run_lbo
from app.schemas.company import CompanyDataBundle
from app.schemas.lbo import LboAssumptions, LboResponse

M = 1e6
REL = 1e-6


@pytest.fixture()
def hand_check_assumptions() -> LboAssumptions:
    """The §15 hand-check assumption set."""
    return LboAssumptions(
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


@pytest.fixture()
def hand_check_result(hand_check_assumptions: LboAssumptions) -> LboResponse:
    return run_lbo(250.0 * M, 1000.0 * M, hand_check_assumptions)


def test_entry_capital_structure(hand_check_result: LboResponse) -> None:
    entry = hand_check_result.entry
    assert entry.entry_ebitda == pytest.approx(250.0 * M, rel=REL)
    assert entry.entry_revenue == pytest.approx(1000.0 * M, rel=REL)
    assert entry.entry_ev == pytest.approx(2000.0 * M, rel=REL)
    assert entry.opening_debt == pytest.approx(1000.0 * M, rel=REL)
    assert entry.sponsor_equity == pytest.approx(1000.0 * M, rel=REL)
    assert entry.equity_pct == pytest.approx(0.5, rel=REL)


def test_year_one_hand_check(hand_check_result: LboResponse) -> None:
    """The §15 year-1 values, exactly."""
    y1 = hand_check_result.years[0]
    assert y1.year == 1
    assert y1.revenue == pytest.approx(1050.0 * M, rel=REL)
    assert y1.ebitda == pytest.approx(262.5 * M, rel=REL)
    assert y1.capex == pytest.approx(52.5 * M, rel=REL)
    assert y1.delta_nwc == pytest.approx(1.0 * M, rel=REL)
    assert y1.interest == pytest.approx(80.0 * M, rel=REL)
    assert y1.taxes == pytest.approx(32.5 * M, rel=REL)
    assert y1.fcf == pytest.approx(96.5 * M, rel=REL)
    assert y1.ending_debt == pytest.approx(903.5 * M, rel=REL)
    assert y1.debt_repaid == pytest.approx(96.5 * M, rel=REL)
    assert y1.ending_cash == pytest.approx(0.0, abs=1e-3)


def test_full_run_against_independent_loop(
    hand_check_result: LboResponse, hand_check_assumptions: LboAssumptions
) -> None:
    """Cross-check every year of the engine against an independent loop."""
    a = hand_check_assumptions
    entry_ebitda = 250.0 * M
    opening_debt = a.debt_multiple * entry_ebitda
    sponsor_equity = a.entry_multiple * entry_ebitda - opening_debt

    revenue = 1000.0 * M
    debt = opening_debt
    cash = 0.0
    assert len(hand_check_result.years) == a.holding_period
    ebitda = 0.0
    for t, year in enumerate(hand_check_result.years, start=1):
        revenue_prev = revenue
        revenue = revenue_prev * (1.0 + a.revenue_growth[t - 1])
        ebitda = a.ebitda_margin[t - 1] * revenue
        capex = a.capex_pct_revenue * revenue
        delta_nwc = a.nwc_pct_revenue * (revenue - revenue_prev)
        interest = a.interest_rate * debt
        taxes = max(0.0, ebitda - capex - interest) * a.tax_rate
        fcf = ebitda - capex - delta_nwc - interest - taxes
        # Spec §8 literal piecewise repayment, kept deliberately distinct from
        # the engine's algebraic reduction so this loop is a truly independent
        # check: mandatory + sweep, but only max(0, fcf) when FCF falls short
        # of the mandatory amount (no new borrowing).
        mandatory = a.mandatory_repayment_pct * opening_debt
        if fcf < mandatory:
            repaid = min(debt, max(0.0, fcf))
        else:
            repaid = min(debt, mandatory + max(0.0, fcf - mandatory))
        cash += max(0.0, fcf - repaid)
        debt -= repaid

        assert year.year == t
        assert year.revenue == pytest.approx(revenue, rel=REL)
        assert year.ebitda == pytest.approx(ebitda, rel=REL)
        assert year.capex == pytest.approx(capex, rel=REL)
        assert year.delta_nwc == pytest.approx(delta_nwc, rel=REL)
        assert year.interest == pytest.approx(interest, rel=REL)
        assert year.taxes == pytest.approx(taxes, rel=REL)
        assert year.fcf == pytest.approx(fcf, rel=REL)
        assert year.debt_repaid == pytest.approx(repaid, rel=REL)
        assert year.ending_debt == pytest.approx(debt, rel=REL)
        assert year.ending_cash == pytest.approx(cash, rel=REL, abs=1e-3)

    exit_block = hand_check_result.exit
    exit_ev = a.exit_multiple * ebitda
    exit_equity = exit_ev - debt + cash
    assert exit_block.exit_ebitda == pytest.approx(ebitda, rel=REL)
    assert exit_block.exit_ev == pytest.approx(exit_ev, rel=REL)
    assert exit_block.ending_debt == pytest.approx(debt, rel=REL)
    assert exit_block.ending_cash == pytest.approx(cash, rel=REL, abs=1e-3)
    assert exit_block.exit_equity == pytest.approx(exit_equity, rel=REL)
    assert exit_block.mom == pytest.approx(exit_equity / sponsor_equity, rel=REL)


def test_irr_mom_consistency(hand_check_result: LboResponse) -> None:
    """With entry/exit-only equity flows, irr == mom^(1/5) - 1 within 1e-9."""
    exit_block = hand_check_result.exit
    assert exit_block.mom is not None and exit_block.irr is not None
    assert exit_block.irr == pytest.approx(
        exit_block.mom ** (1.0 / 5.0) - 1.0, abs=1e-9
    )


def test_sensitivity_grids_shape_and_center(hand_check_result: LboResponse) -> None:
    """All three grids are 5x5 and their center cell equals the base case."""
    s = hand_check_result.sensitivities
    exit_block = hand_check_result.exit
    for grid, base_value in (
        (s.irr_exit_vs_growth, exit_block.irr),
        (s.irr_entry_vs_exit, exit_block.irr),
        (s.mom_exit_vs_margin, exit_block.mom),
    ):
        assert len(grid.rows) == 5
        assert len(grid.cols) == 5
        assert len(grid.values) == 5
        assert all(len(row) == 5 for row in grid.values)
        assert base_value is not None
        assert grid.values[2][2] == pytest.approx(base_value, abs=1e-9)


def test_sensitivity_axes(hand_check_result: LboResponse) -> None:
    s = hand_check_result.sensitivities
    assert s.irr_exit_vs_growth.rows == [6.0, 7.0, 8.0, 9.0, 10.0]
    assert s.irr_exit_vs_growth.cols == [-0.04, -0.02, 0.0, 0.02, 0.04]
    assert s.irr_entry_vs_exit.rows == [6.0, 7.0, 8.0, 9.0, 10.0]
    assert s.irr_entry_vs_exit.cols == [6.0, 7.0, 8.0, 9.0, 10.0]
    assert s.mom_exit_vs_margin.rows == [6.0, 7.0, 8.0, 9.0, 10.0]
    assert s.mom_exit_vs_margin.cols == [-0.04, -0.02, 0.0, 0.02, 0.04]


def test_irr_monotone_in_exit_multiple_along_columns(
    hand_check_result: LboResponse,
) -> None:
    """IRR strictly increases with the exit multiple, in every column."""
    grid = hand_check_result.sensitivities.irr_exit_vs_growth
    for j in range(5):
        column = [grid.values[i][j] for i in range(5)]
        assert all(v is not None for v in column)
        assert all(column[i] < column[i + 1] for i in range(4))  # type: ignore[operator]


def test_negative_fcf_year_warning() -> None:
    """High leverage + high interest makes year-1 FCF negative -> warning."""
    a = LboAssumptions(
        entry_multiple=8.0,
        debt_multiple=7.0,
        revenue_growth=[0.05] * 5,
        ebitda_margin=[0.25] * 5,
        capex_pct_revenue=0.05,
        nwc_pct_revenue=0.02,
        tax_rate=0.25,
        interest_rate=0.20,
        mandatory_repayment_pct=0.05,
        exit_multiple=8.0,
        holding_period=5,
    )
    result = run_lbo(250.0 * M, 1000.0 * M, a)
    assert result.years[0].fcf < 0
    assert result.years[0].debt_repaid == pytest.approx(0.0, abs=1e-3)
    assert result.years[0].ending_debt == pytest.approx(7.0 * 250.0 * M, rel=REL)
    assert any("Negative FCF in year 1" in w for w in result.warnings)


def test_debt_floor_and_excess_cash_accrual() -> None:
    """Once debt hits zero, the sweep stops and excess FCF builds cash."""
    a = LboAssumptions(
        entry_multiple=8.0,
        debt_multiple=0.5,
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
    result = run_lbo(250.0 * M, 1000.0 * M, a)
    for year in result.years:
        assert year.ending_debt >= 0.0
    assert result.years[-1].ending_debt == pytest.approx(0.0, abs=1e-3)
    assert result.years[-1].ending_cash > 0.0


def test_derive_defaults_testco(testco_bundle: CompanyDataBundle) -> None:
    """TESTCO defaults per §8: EV/EBITDA 6.6x -> entry 6.5x, etc."""
    assumptions, basis = derive_defaults(testco_bundle)

    assert assumptions.entry_multiple == pytest.approx(6.5)
    assert assumptions.exit_multiple == pytest.approx(6.5)
    assert assumptions.debt_multiple == pytest.approx(3.5)
    assert assumptions.holding_period == 5

    cagr = (1000.0 / 850.0) ** (1.0 / 3.0) - 1.0  # within [0, 0.15]: unclamped
    assert assumptions.revenue_growth == pytest.approx([cagr] * 5, rel=REL)
    assert assumptions.ebitda_margin == pytest.approx([0.25] * 5, rel=REL)
    capex_avg = (45.0 / 900.0 + 48.0 / 950.0 + 50.0 / 1000.0) / 3.0
    assert assumptions.capex_pct_revenue == pytest.approx(capex_avg, rel=REL)
    assert assumptions.nwc_pct_revenue == pytest.approx(0.02)
    assert assumptions.tax_rate == pytest.approx(0.25)
    assert assumptions.interest_rate == pytest.approx(0.08)
    assert assumptions.mandatory_repayment_pct == pytest.approx(0.05)

    # Every assumption field carries a basis note.
    for field in LboAssumptions.model_fields:
        assert field in basis
        assert basis[field]


def test_derive_defaults_fallback_without_market(
    testco_bundle: CompanyDataBundle,
) -> None:
    """No market data -> EV/EBITDA unavailable -> entry falls back to 8.0x."""
    bundle = testco_bundle.model_copy(update={"market": None})
    assumptions, basis = derive_defaults(bundle)
    assert assumptions.entry_multiple == pytest.approx(8.0)
    assert assumptions.exit_multiple == pytest.approx(8.0)
    assert assumptions.debt_multiple == pytest.approx(4.0)
    assert "unavailable" in basis["entry_multiple"].lower()


def test_run_lbo_with_testco_defaults(testco_bundle: CompanyDataBundle) -> None:
    """End-to-end: derived defaults feed the engine without errors."""
    assumptions, _ = derive_defaults(testco_bundle)
    latest = testco_bundle.financials[-1]
    assert latest.ebitda is not None and latest.revenue is not None
    result = run_lbo(latest.ebitda, latest.revenue, assumptions, ticker="TESTCO")
    assert result.ticker == "TESTCO"
    assert result.entry.entry_ev == pytest.approx(6.5 * 250.0 * M, rel=REL)
    assert result.exit.mom is not None and result.exit.mom > 0
    assert result.exit.irr is not None
    assert result.assumptions == assumptions  # echo of inputs
