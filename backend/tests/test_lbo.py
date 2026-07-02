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
    # Sources & Uses: 2% of the 2000m EV = 40m of fees, funded by equity.
    assert entry.transaction_fees == pytest.approx(40.0 * M, rel=REL)
    assert entry.total_uses == pytest.approx(2040.0 * M, rel=REL)
    # Sponsor equity is the plug (total uses - debt), so it absorbs the fees.
    assert entry.sponsor_equity == pytest.approx(1040.0 * M, rel=REL)
    assert entry.equity_pct == pytest.approx(1040.0 / 2040.0, rel=REL)
    # Sources balance Uses exactly.
    assert entry.opening_debt + entry.sponsor_equity == pytest.approx(
        entry.total_uses, rel=REL
    )
    assert entry.opening_net_leverage == pytest.approx(4.0, rel=REL)  # 1000m / 250m


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
    entry_ev = a.entry_multiple * entry_ebitda
    opening_debt = a.debt_multiple * entry_ebitda
    # Sponsor equity is the plug: total uses (EV + fees) less new debt.
    sponsor_equity = entry_ev + a.transaction_fee_pct * entry_ev - opening_debt

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


def test_scenarios_bracket_the_base_case(hand_check_result: LboResponse) -> None:
    """Three underwriting cases: strategic > base > downside on IRR, and base
    matches the headline exit exactly."""
    s = {sc.key: sc for sc in hand_check_result.scenarios}
    assert set(s) == {"downside", "base", "strategic"}
    assert s["base"].irr == pytest.approx(hand_check_result.exit.irr, rel=REL)
    assert s["base"].mom == pytest.approx(hand_check_result.exit.mom, rel=REL)
    assert s["strategic"].exit_multiple == pytest.approx(
        hand_check_result.assumptions.exit_multiple + 2.0, rel=REL
    )
    assert s["downside"].exit_multiple == pytest.approx(
        hand_check_result.assumptions.exit_multiple - 2.0, rel=REL
    )
    # A higher exit multiple and faster growth strictly raise the return.
    assert (
        s["strategic"].irr is not None
        and s["base"].irr is not None
        and s["downside"].irr is not None
    )
    assert s["strategic"].irr > s["base"].irr > s["downside"].irr


def test_covenants_no_breach_and_cushion(hand_check_result: LboResponse) -> None:
    """The hand-check deal (3.4x opening leverage) clears every covenant with a
    positive, sub-1.0 EBITDA cushion."""
    cov = hand_check_result.covenants
    assert cov is not None
    assert len(cov.years) == 5
    assert cov.any_breach is False
    y1 = cov.years[0]
    assert y1.net_debt_to_ebitda is not None and y1.net_debt_to_ebitda < 6.0
    assert y1.interest_coverage is not None and y1.interest_coverage > 2.0
    assert y1.fcf_dscr is not None and y1.fcf_dscr > 1.0
    assert cov.min_ebitda_cushion_pct is not None
    assert 0.0 < cov.min_ebitda_cushion_pct < 1.0


def test_covenants_flag_breach_on_high_leverage() -> None:
    """7x opening leverage + 20% interest breaches the leverage covenant in
    year 1 (FCF is negative, so no paydown)."""
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
    assert result.covenants is not None
    assert result.covenants.any_breach is True
    assert result.covenants.years[0].breached is True


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


# ---------------------------------------------------------------------------
# Negative-EBITDA / revenue basis (high-growth companies)
# ---------------------------------------------------------------------------


@pytest.fixture()
def revenue_basis_assumptions() -> LboAssumptions:
    """A negative-EBITDA growth company priced on EV/Revenue, no leverage,
    with a margin ramp from -10% to a positive terminal margin."""
    return LboAssumptions(
        valuation_basis="revenue",
        entry_multiple=3.0,  # EV/Revenue
        debt_multiple=0.0,  # unused on this basis
        entry_leverage_pct=0.0,  # all-equity
        revenue_growth=[0.40, 0.35, 0.30, 0.25, 0.20],
        ebitda_margin=[-0.10, -0.02, 0.06, 0.14, 0.20],
        capex_pct_revenue=0.04,
        nwc_pct_revenue=0.02,
        tax_rate=0.25,
        interest_rate=0.08,
        mandatory_repayment_pct=0.05,
        exit_multiple=12.0,  # EV/EBITDA at exit, once profitable
        holding_period=5,
    )


def test_revenue_basis_entry_prices_on_revenue(
    revenue_basis_assumptions: LboAssumptions,
) -> None:
    """Entry EV is EV/Revenue × revenue and, with no leverage, equals equity —
    even though the entry EBITDA is negative."""
    result = run_lbo(-80.0 * M, 1000.0 * M, revenue_basis_assumptions)
    entry = result.entry
    assert entry.entry_ebitda == pytest.approx(-80.0 * M, rel=REL)  # not floored
    assert entry.entry_ev == pytest.approx(3.0 * 1000.0 * M, rel=REL)
    assert entry.opening_debt == pytest.approx(0.0, abs=1e-3)
    # All-equity: sponsor equity = purchase EV + 2% fees, opening_net_leverage
    # is None because EBITDA is negative (cannot be expressed in EBITDA turns).
    assert entry.sponsor_equity == pytest.approx(1.02 * 3.0 * 1000.0 * M, rel=REL)
    assert entry.equity_pct == pytest.approx(1.0, rel=REL)
    assert entry.opening_net_leverage is None


def test_revenue_basis_reaches_profitable_exit(
    revenue_basis_assumptions: LboAssumptions,
) -> None:
    """The margin ramp turns EBITDA positive, so the exit prices on EV/EBITDA
    and returns are demonstrable."""
    result = run_lbo(-80.0 * M, 1000.0 * M, revenue_basis_assumptions)
    exit_block = result.exit
    assert exit_block.exit_ebitda > 0  # terminal EBITDA positive
    assert exit_block.exit_ev is not None
    assert exit_block.exit_ev == pytest.approx(12.0 * exit_block.exit_ebitda, rel=REL)
    assert exit_block.exit_equity is not None
    assert exit_block.mom is not None and exit_block.mom > 0
    assert exit_block.irr is not None
    # Early years lose money -> the honest going-concern warnings fire.
    assert any("EV/Revenue" in w for w in result.warnings)
    assert any("cash burn" in w.lower() for w in result.warnings)


def test_revenue_basis_never_profitable_refuses_exit() -> None:
    """A ramp that never turns positive yields no EV/EBITDA exit and null
    returns rather than a nonsense negative exit equity."""
    a = LboAssumptions(
        valuation_basis="revenue",
        entry_multiple=3.0,
        debt_multiple=0.0,
        entry_leverage_pct=0.0,
        revenue_growth=[0.30] * 5,
        ebitda_margin=[-0.20, -0.18, -0.16, -0.14, -0.12],  # never positive
        capex_pct_revenue=0.04,
        nwc_pct_revenue=0.02,
        tax_rate=0.25,
        interest_rate=0.08,
        mandatory_repayment_pct=0.05,
        exit_multiple=12.0,
        holding_period=5,
    )
    result = run_lbo(-200.0 * M, 1000.0 * M, a)
    assert result.exit.exit_ebitda < 0
    assert result.exit.exit_ev is None
    assert result.exit.exit_equity is None
    assert result.exit.mom is None
    assert result.exit.irr is None
    assert any("does not reach positive EBITDA" in w for w in result.warnings)


def test_min_equity_gate_suppresses_both_mom_and_irr() -> None:
    """A sliver of sponsor equity (below 5% of entry EV) suppresses BOTH MoM and
    IRR, closing the old asymmetry where IRR was reported unconditionally."""
    a = LboAssumptions(
        entry_multiple=8.0,
        debt_multiple=7.9,  # equity = 0.1x EBITDA = 1.25% of entry EV
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
    assert result.exit.mom is None
    assert result.exit.irr is None
    assert any("below 5% of entry EV" in w for w in result.warnings)


def test_interest_never_negative_on_zero_debt(
    revenue_basis_assumptions: LboAssumptions,
) -> None:
    """With no opening debt, interest is exactly zero every year (never a
    phantom negative from a mis-signed balance)."""
    result = run_lbo(-80.0 * M, 1000.0 * M, revenue_basis_assumptions)
    assert all(y.interest == pytest.approx(0.0, abs=1e-6) for y in result.years)


def test_revenue_basis_sensitivity_labels_and_ramp(
    revenue_basis_assumptions: LboAssumptions,
) -> None:
    """The entry axis is labelled EV/Revenue, and the margin grid preserves the
    loss-year ramp (no >=1% floor): a downward shift that pushes the terminal
    margin non-positive yields a no-exit (None) cell rather than a floored,
    inflated one."""
    # Terminal margin of 2% so a -4pp shift crosses zero -> no EV/EBITDA exit.
    a = revenue_basis_assumptions.model_copy(
        update={"ebitda_margin": [-0.10, -0.06, -0.03, 0.00, 0.02]}
    )
    result = run_lbo(-80.0 * M, 1000.0 * M, a)
    s = result.sensitivities
    assert "EV/Revenue" in s.irr_entry_vs_exit.row_label
    # Base exit multiple row (index 2), lowest margin shift (-4pp): terminal
    # margin 2% - 4pp = -2% -> terminal EBITDA negative -> None (not floored).
    assert s.mom_exit_vs_margin.values[2][0] is None
    # The unshifted cell (index 2) reaches +2% terminal margin -> a real exit.
    assert s.mom_exit_vs_margin.values[2][2] is not None


def _negative_ebitda_bundle(base: CompanyDataBundle) -> CompanyDataBundle:
    """TESTCO with its latest fiscal year forced to a negative EBITDA."""
    financials = sorted(base.financials, key=lambda y: y.fiscal_year)
    latest = financials[-1]
    financials[-1] = latest.model_copy(update={"ebitda": -0.08 * latest.revenue})
    return base.model_copy(update={"financials": financials})


def test_derive_defaults_negative_ebitda_selects_revenue_basis(
    testco_bundle: CompanyDataBundle,
) -> None:
    """A non-positive latest EBITDA auto-selects the revenue basis with a
    margin ramp that reaches profitability and a positive entry EV."""
    bundle = _negative_ebitda_bundle(testco_bundle)
    assumptions, basis = derive_defaults(bundle)

    assert assumptions.valuation_basis == "revenue"
    assert assumptions.entry_multiple > 0  # EV/Revenue, never negative
    assert assumptions.entry_leverage_pct == pytest.approx(0.0)
    assert assumptions.debt_multiple == pytest.approx(0.0)
    assert assumptions.ebitda_margin[0] < 0  # starts in the red
    assert assumptions.ebitda_margin[-1] > 0  # ramps to profit
    assert assumptions.exit_multiple > 0

    # Every field still carries a basis note (both new fields included).
    for field in LboAssumptions.model_fields:
        assert field in basis and basis[field]

    # The derived defaults feed the engine and produce a real, demonstrable case.
    latest = sorted(bundle.financials, key=lambda y: y.fiscal_year)[-1]
    result = run_lbo(latest.ebitda, latest.revenue, assumptions, ticker="NEGCO")
    assert result.entry.entry_ev > 0
    assert result.exit.exit_ebitda > 0
    assert result.exit.mom is not None


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
