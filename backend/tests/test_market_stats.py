"""Market-stats extraction and endpoint tests (analyst / ownership / dividends)."""

import pytest
from fastapi.testclient import TestClient

import app.market_stats as market_stats

# A large-cap-shaped Yahoo .info dict (subset of the real fields).
FULL_INFO = {
    "currency": "USD",
    "currentPrice": 200.0,
    "targetMeanPrice": 240.0,
    "targetHighPrice": 300.0,
    "targetLowPrice": 180.0,
    "recommendationKey": "buy",
    "recommendationMean": 2.1,
    "numberOfAnalystOpinions": 42,
    "forwardPE": 22.5,
    "forwardEps": 8.9,
    "trailingEps": 7.5,
    "earningsGrowth": 0.12,
    "revenueGrowth": 0.08,
    "earningsTimestamp": 1_770_000_000,
    "heldPercentInstitutions": 0.62,
    "heldPercentInsiders": 0.001,
    "floatShares": 9_000_000_000,
    "sharesOutstanding": 9_500_000_000,
    "sharesShort": 100_000_000,
    "shortPercentOfFloat": 0.011,
    "sharesPercentSharesOut": 0.0105,
    "shortRatio": 2.3,
    "dividendRate": 2.2,
    "dividendYield": 1.1,  # reported as a percent here
    "payoutRatio": 0.28,
    "fiveYearAvgDividendYield": 1.5,  # percent
    "exDividendDate": 1_760_000_000,
    "lastDividendValue": 0.55,
    "beta": 1.15,
    "trailingPE": 26.6,
    "priceToBook": 40.0,
    "enterpriseToEbitda": 20.1,
    "enterpriseToRevenue": 7.2,
    "profitMargins": 0.25,
    "returnOnEquity": 1.4,
    "fiftyTwoWeekHigh": 260.0,
    "fiftyTwoWeekLow": 160.0,
    "52WeekChange": 0.18,
    "SandP52WeekChange": 0.12,
    "fiftyDayAverage": 210.0,
    "twoHundredDayAverage": 195.0,
}


@pytest.fixture(autouse=True)
def _clear_cache():
    market_stats.reset_cache()
    yield
    market_stats.reset_cache()


def test_build_extracts_all_blocks() -> None:
    s = market_stats._build("AAPL", FULL_INFO)
    assert s is not None
    a = s.analysts
    assert a.rating == "buy"
    assert a.analyst_count == 42
    assert a.target_mean == pytest.approx(240.0)
    assert a.current_price == pytest.approx(200.0)
    assert a.implied_upside == pytest.approx(0.20)  # 240/200 - 1
    assert a.forward_pe == pytest.approx(22.5)
    assert a.next_earnings_date is not None  # epoch converted

    o = s.ownership
    assert o.held_pct_institutions == pytest.approx(0.62)
    assert o.short_ratio == pytest.approx(2.3)
    assert o.shares_outstanding == pytest.approx(9_500_000_000)

    d = s.dividends
    assert d.dividend_rate == pytest.approx(2.2)
    assert d.dividend_yield == pytest.approx(0.011)  # 1.1% -> decimal
    assert d.five_year_avg_yield == pytest.approx(0.015)  # 1.5 -> 0.015
    assert d.ex_dividend_date is not None

    assert s.stats.beta == pytest.approx(1.15)
    assert s.stats.fifty_two_week_change == pytest.approx(0.18)
    assert s.currency == "USD"
    assert s.warnings == []  # full coverage -> no unavailable warning


def test_pence_normalization_for_lse() -> None:
    """GBp (pence) quotes divide price-per-share fields by 100; ratios untouched."""
    info = {
        "currency": "GBp",
        "currentPrice": 500.0,  # 500p = £5.00
        "targetMeanPrice": 600.0,
        "dividendRate": 20.0,  # 20p
        "dividendYield": 0.04,  # already a decimal here
        "payoutRatio": 0.5,
        "fiftyTwoWeekHigh": 650.0,
    }
    s = market_stats._build("TSCO.L", info)
    assert s is not None
    assert s.currency == "GBP"
    assert s.analysts.current_price == pytest.approx(5.0)
    assert s.analysts.target_mean == pytest.approx(6.0)
    assert s.dividends.dividend_rate == pytest.approx(0.20)
    assert s.dividends.payout_ratio == pytest.approx(0.5)  # ratio not divided
    assert s.stats.fifty_two_week_high == pytest.approx(6.5)


def test_sparse_info_degrades_and_warns() -> None:
    s = market_stats._build("TINY", {"currency": "USD"})
    assert s is not None
    assert s.analysts.target_mean is None
    assert s.ownership.held_pct_institutions is None
    assert s.dividends.dividend_rate is None
    assert any("Analyst coverage is unavailable" in w for w in s.warnings)


def test_endpoint_404_when_no_data(client: TestClient) -> None:
    # Autouse conftest stub makes _fetch_info return None.
    r = client.get("/api/companies/NODATA/market-stats")
    assert r.status_code == 404


def test_endpoint_returns_stats(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(market_stats, "_fetch_info", lambda ticker: FULL_INFO)
    market_stats.reset_cache()
    r = client.get("/api/companies/AAPL/market-stats")
    assert r.status_code == 200
    body = r.json()
    assert body["ticker"] == "AAPL"
    assert body["analysts"]["rating"] == "buy"
    assert body["analysts"]["implied_upside"] == pytest.approx(0.20)
    assert body["ownership"]["held_pct_institutions"] == pytest.approx(0.62)
    assert body["dividends"]["dividend_yield"] == pytest.approx(0.011)


def test_cache_avoids_refetch(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def counting(ticker: str):
        calls["n"] += 1
        return FULL_INFO

    monkeypatch.setattr(market_stats, "_fetch_info", counting)
    market_stats.reset_cache()
    market_stats.get_market_stats("AAPL")
    market_stats.get_market_stats("AAPL")
    assert calls["n"] == 1  # second call served from cache
