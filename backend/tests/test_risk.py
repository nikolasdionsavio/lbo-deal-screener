"""Risk computation tests (Altman Z'', Piotroski, bands, factor categorisation)."""

from app.risk import compute_financial_risk, compute_market_risk, financial_band
from app.risk.factors import _isolate_item_1a, _looks_like_risk_heading, categorise
from app.schemas.company import CompanyDataBundle, CompanyInfo
from app.schemas.financials import FiscalYearFinancials
from app.schemas.market_stats import KeyStats, MarketStats


def _year(fy: int, **kw) -> FiscalYearFinancials:
    return FiscalYearFinancials(fiscal_year=fy, **kw)


def _bundle(years: list[FiscalYearFinancials]) -> CompanyDataBundle:
    return CompanyDataBundle(
        info=CompanyInfo(ticker="TEST", name="Test Co"),
        market=None,
        financials=years,
        currency="USD",
        data_source="test",
        fetched_at="2026-07-03T00:00:00+00:00",
    )


def test_altman_z2_and_metrics_healthy() -> None:
    """A healthy balance sheet lands in the safe zone with low leverage flags."""
    latest = _year(
        2025,
        revenue=1000.0,
        gross_profit=500.0,
        operating_income=200.0,
        net_income=150.0,
        interest_expense=10.0,
        ebitda=250.0,
        operating_cash_flow=180.0,
        investing_cash_flow=-50.0,
        free_cash_flow=130.0,
        cash_and_equivalents=300.0,
        total_debt=200.0,
        current_assets=600.0,
        current_liabilities=200.0,
        inventory=100.0,
        total_assets=1200.0,
        total_liabilities=400.0,
        total_equity=800.0,
        retained_earnings=500.0,
        shares_outstanding=100.0,
    )
    prior = _year(
        2024,
        revenue=900.0,
        gross_profit=430.0,
        operating_income=160.0,
        net_income=120.0,
        total_assets=1100.0,
        current_assets=520.0,
        current_liabilities=210.0,
        long_term_debt=180.0,
        shares_outstanding=100.0,
    )
    distress, metrics, _ = compute_financial_risk(_bundle([prior, latest]))
    z = next(d for d in distress if d.name.startswith("Altman"))
    assert z.score is not None and z.score > 2.6 and z.zone == "Safe" and z.flag == "low"
    f = next(d for d in distress if d.name.startswith("Piotroski"))
    assert f.score is not None  # scored with two years

    by_key = {m.key: m for m in metrics}
    assert by_key["net_debt_ebitda"].flag == "low"  # (200-300)/250 -> negative, low
    assert by_key["current_ratio"].flag == "low"  # 600/200 = 3.0
    assert by_key["interest_coverage"].value == 20.0  # 200/10

    band, _summary = financial_band(distress, metrics)
    assert band in ("low", "moderate")


def test_altman_z2_distress_zone() -> None:
    """Negative retained earnings + heavy liabilities -> distress zone, high band."""
    latest = _year(
        2025,
        revenue=500.0,
        operating_income=-40.0,
        net_income=-80.0,
        interest_expense=60.0,
        ebitda=-10.0,
        operating_cash_flow=-50.0,
        investing_cash_flow=-10.0,
        free_cash_flow=-70.0,
        cash_and_equivalents=20.0,
        total_debt=600.0,
        current_assets=100.0,
        current_liabilities=300.0,
        total_assets=700.0,
        total_liabilities=680.0,
        total_equity=20.0,
        retained_earnings=-400.0,
        shares_outstanding=100.0,
    )
    distress, metrics, _ = compute_financial_risk(_bundle([latest]))
    z = next(d for d in distress if d.name.startswith("Altman"))
    assert z.zone == "Distress" and z.flag == "high"
    band, _ = financial_band(distress, metrics)
    assert band == "high"  # Z'' distress forces high


def test_compute_financial_risk_no_data() -> None:
    _distress, metrics, warnings = compute_financial_risk(_bundle([]))
    assert metrics == []
    assert any("No financial statements" in w for w in warnings)


def test_market_risk_beta_and_range() -> None:
    stats = MarketStats(
        ticker="TEST",
        as_of="2026-07-03",
        source="Finnhub",
        analysts=__import__("app.schemas.market_stats", fromlist=["AnalystView"]).AnalystView(),
        ownership=__import__("app.schemas.market_stats", fromlist=["OwnershipView"]).OwnershipView(),
        dividends=__import__("app.schemas.market_stats", fromlist=["DividendView"]).DividendView(),
        stats=KeyStats(beta=1.8, fifty_two_week_high=300.0, fifty_two_week_low=100.0),
    )
    metrics = compute_market_risk(stats)
    by = {m.key: m for m in metrics}
    assert by["beta"].flag == "high"  # 1.8 > 1.5
    assert by["range_width"].value == 2.0  # (300-100)/100


def test_factor_categorisation() -> None:
    assert categorise("New regulation could adversely affect our licenses") == "Regulatory & legal"
    assert categorise("We face intense competition from larger rivals") == "Competition"
    assert categorise("A cybersecurity breach could expose customer data") == "Cyber & technology"
    assert categorise("Our indebtedness and covenants limit flexibility") == "Financial & liquidity"
    assert categorise("Weather is nice today") == "Other"


def test_risk_heading_heuristic() -> None:
    assert _looks_like_risk_heading(
        "The Company's business may be adversely affected by supply constraints"
    )
    assert not _looks_like_risk_heading("RISK FACTORS")
    assert not _looks_like_risk_heading("Item 1A. Risk Factors")
    assert not _looks_like_risk_heading("Short")  # too short


def test_isolate_item_1a() -> None:
    text = (
        "table of contents item 1a risk factors ... "
        "Item 1A. Risk Factors The company may be harmed if demand falls. "
        "Competition could reduce our margins. " + "x " * 300
        + " Item 1B. Unresolved Staff Comments none."
    )
    section = _isolate_item_1a(text)
    assert section is not None
    assert "demand falls" in section.lower()
    assert "unresolved staff comments" not in section.lower()
