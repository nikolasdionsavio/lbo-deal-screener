"""Extended statement fields + CRWD-class tag fixes (spec §19.8).

Fixture-driven, no live network: tests/fixtures/edgar_companyfacts_crwd_sample.json
is trimmed verbatim from the real CrowdStrike companyfacts (10-K FY facts for
FY2024-FY2026 only), so every asserted number is ground truth from EDGAR:

- revenue resolves from RevenueFromContractWithCustomerIncludingAssessedTax
  (CRWD files no Excluding variant and no "Revenues"),
- D&A comes from the §19.8 second-anchor component sum (CRWD files NO standard
  depreciation flow tag at all): CapitalizedContractCostAmortization 449.413m +
  AmortizationOfIntangibleAssets 31.233m + CapitalizedComputerSoftwareAmortization1
  79.6m = 560.246m, so FY2026 EBITDA = -293.292m + 560.246m = 266.954m,
- the 16 §19.8 extended fields parse, including the per-share ("USD/shares")
  and share-count ("shares") unit exceptions and the SG&A component sum.
"""

import json
from pathlib import Path
from typing import Iterator

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_provider_dep
from app.main import app
from app.providers.edgar import (
    COMPANYFACTS_URL,
    TICKER_MAP_URL,
    SecEdgarProvider,
)

REL_TOL = 1e-6
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
CRWD_FIXTURE = FIXTURES_DIR / "edgar_companyfacts_crwd_sample.json"
CRWD_CIK = 1535527
TEST_USER_AGENT = "Test Agent test@example.com"

EXTENDED_FIELDS = [
    "research_development",
    "selling_general_admin",
    "pretax_income",
    "eps_basic",
    "eps_diluted",
    "shares_diluted",
    "stock_based_compensation",
    "total_assets",
    "total_liabilities",
    "goodwill",
    "intangible_assets",
    "ppe_net",
    "long_term_debt",
    "retained_earnings",
    "investing_cash_flow",
    "financing_cash_flow",
]


def _crwd_handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if url == TICKER_MAP_URL:
        return httpx.Response(
            200,
            json={
                "0": {
                    "cik_str": CRWD_CIK,
                    "ticker": "CRWD",
                    "title": "CrowdStrike Holdings, Inc.",
                }
            },
        )
    if url == COMPANYFACTS_URL.format(cik=CRWD_CIK):
        return httpx.Response(200, json=json.loads(CRWD_FIXTURE.read_text()))
    return httpx.Response(404, json={"detail": "not found"})


def _crwd_provider(tmp_path: Path) -> SecEdgarProvider:
    client = httpx.Client(transport=httpx.MockTransport(_crwd_handler))
    return SecEdgarProvider(TEST_USER_AGENT, client=client, cache_dir=tmp_path / "cache")


@pytest.fixture()
def crwd_bundle(tmp_path: Path):
    return _crwd_provider(tmp_path).get_company("CRWD")


def test_crwd_revenue_from_including_assessed_tax_tag(crwd_bundle) -> None:
    fy2026 = crwd_bundle.financials[-1]
    assert fy2026.fiscal_year == 2026
    assert fy2026.period_end == "2026-01-31"
    assert fy2026.revenue == pytest.approx(4_812_005_000.0, rel=REL_TOL)
    assert "revenue unavailable from SEC EDGAR" not in crwd_bundle.warnings


def test_crwd_da_second_anchor_yields_fy2026_ebitda(crwd_bundle) -> None:
    """§19.8: CRWD files no standard depreciation tag; the amortization
    components (anchored on CapitalizedContractCostAmortization) sum to D&A,
    and EBITDA derives normally from operating income."""
    fy2026 = crwd_bundle.financials[-1]
    assert fy2026.operating_income == pytest.approx(-293_292_000.0, rel=REL_TOL)
    assert fy2026.depreciation_amortization == pytest.approx(
        560_246_000.0, rel=REL_TOL  # 449.413m + 31.233m + 79.6m
    )
    assert fy2026.ebitda == pytest.approx(266_954_000.0, rel=REL_TOL)
    assert "ebitda" in fy2026.derived_fields
    assert "depreciation_amortization unavailable from SEC EDGAR" not in crwd_bundle.warnings


def test_crwd_extended_fields_parse_with_unit_exceptions(crwd_bundle) -> None:
    fy2026 = crwd_bundle.financials[-1]
    # Per-share unit exception ("USD/shares") — eps fields only.
    assert fy2026.eps_basic == pytest.approx(-0.65, rel=REL_TOL)
    assert fy2026.eps_diluted == pytest.approx(-0.65, rel=REL_TOL)
    # Share-count unit exception ("shares") — shares_diluted only.
    assert fy2026.shares_diluted == pytest.approx(250_576_000.0, rel=REL_TOL)
    # SG&A component-sum fallback: G&A 670.344m + S&M 1,831.254m.
    assert fy2026.selling_general_admin == pytest.approx(2_501_598_000.0, rel=REL_TOL)
    assert fy2026.research_development == pytest.approx(1_384_770_000.0, rel=REL_TOL)
    assert fy2026.pretax_income == pytest.approx(-126_989_000.0, rel=REL_TOL)
    assert fy2026.stock_based_compensation == pytest.approx(1_096_679_000.0, rel=REL_TOL)
    assert fy2026.total_assets == pytest.approx(11_086_684_000.0, rel=REL_TOL)
    assert fy2026.total_liabilities == pytest.approx(6_614_079_000.0, rel=REL_TOL)
    assert fy2026.goodwill == pytest.approx(1_363_294_000.0, rel=REL_TOL)
    assert fy2026.intangible_assets == pytest.approx(136_702_000.0, rel=REL_TOL)
    assert fy2026.ppe_net == pytest.approx(976_331_000.0, rel=REL_TOL)
    assert fy2026.long_term_debt == pytest.approx(745_471_000.0, rel=REL_TOL)
    assert fy2026.retained_earnings == pytest.approx(-1_283_042_000.0, rel=REL_TOL)
    assert fy2026.investing_cash_flow == pytest.approx(-764_479_000.0, rel=REL_TOL)
    assert fy2026.financing_cash_flow == pytest.approx(132_452_000.0, rel=REL_TOL)


def test_crwd_kpi_inputs_unchanged_core_fields(crwd_bundle) -> None:
    """Core fields (KPIs/score/LBO read these) still resolve as before."""
    fy2026 = crwd_bundle.financials[-1]
    assert fy2026.net_income == pytest.approx(-162_502_000.0, rel=REL_TOL)
    assert fy2026.total_debt == pytest.approx(745_471_000.0, rel=REL_TOL)
    assert fy2026.free_cash_flow == pytest.approx(1_310_241_000.0, rel=REL_TOL)
    assert crwd_bundle.currency == "USD"


def test_extended_fields_missing_stay_none_without_warnings(tmp_path: Path) -> None:
    """§19.8 fields are optional: filers without the tags get None and no
    '<field> unavailable from SEC EDGAR' warning spam (core fields only)."""
    import tests.test_providers as tp

    provider = tp._make_edgar(tmp_path / "cache", tp._edgar_handler())
    bundle = provider.get_company("FIXT")
    fy = bundle.financials[-1]
    for field in EXTENDED_FIELDS:
        if field == "long_term_debt":
            # The FIXT fixture files LongTermDebtNoncurrent (for total_debt),
            # which legitimately populates this extended field too.
            assert fy.long_term_debt == pytest.approx(150e6)
            continue
        assert getattr(fy, field) is None, field
    for field in EXTENDED_FIELDS:
        assert f"{field} unavailable from SEC EDGAR" not in bundle.warnings


# ---------------------------------------------------------------------------
# MRVL regression: a combined D&A tag with stale partial history must not
# block the per-period component fill (tests/fixtures/
# edgar_companyfacts_mrvl_sample.json is trimmed verbatim from the real
# Marvell companyfacts — FY2025/FY2026 filings plus DepreciationAndAmortization's
# real stale history, which stops at FY2023).
# ---------------------------------------------------------------------------

MRVL_FIXTURE = FIXTURES_DIR / "edgar_companyfacts_mrvl_sample.json"
MRVL_CIK = 1835632


def _mrvl_handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if url == TICKER_MAP_URL:
        return httpx.Response(
            200,
            json={
                "0": {
                    "cik_str": MRVL_CIK,
                    "ticker": "MRVL",
                    "title": "Marvell Technology, Inc.",
                }
            },
        )
    if url == COMPANYFACTS_URL.format(cik=MRVL_CIK):
        return httpx.Response(200, json=json.loads(MRVL_FIXTURE.read_text()))
    return httpx.Response(404, json={"detail": "not found"})


@pytest.fixture()
def mrvl_bundle(tmp_path: Path):
    client = httpx.Client(transport=httpx.MockTransport(_mrvl_handler))
    provider = SecEdgarProvider(
        TEST_USER_AGENT, client=client, cache_dir=tmp_path / "cache"
    )
    return provider.get_company("MRVL")


def test_mrvl_fy2026_da_and_ebitda_filled_from_components(mrvl_bundle) -> None:
    """MRVL files DepreciationAndAmortization only through FY2023, so FY2026
    D&A must come from the per-period component sum: Depreciation 221.7m +
    AmortizationOfIntangibleAssets 942.0m + OtherDepreciationAndAmortization
    348.6m + OperatingLeaseRightOfUseAssetAmortizationExpense 44.4m = 1,556.7m,
    and EBITDA = OperatingIncomeLoss 1,322.9m + 1,556.7m = 2,879.6m."""
    fy2026 = mrvl_bundle.financials[-1]
    assert fy2026.fiscal_year == 2026
    assert fy2026.period_end == "2026-01-31"
    assert fy2026.revenue == pytest.approx(8_194_600_000.0, rel=REL_TOL)
    assert fy2026.depreciation_amortization == pytest.approx(1557e6, abs=1e6)
    assert fy2026.ebitda == pytest.approx(2880e6, abs=1e6)
    assert "ebitda" in fy2026.derived_fields
    assert any(
        w.startswith("depreciation_amortization assembled from multiple SEC tags")
        for w in mrvl_bundle.warnings
    )
    assert (
        "depreciation_amortization unavailable from SEC EDGAR"
        not in mrvl_bundle.warnings
    )


def test_mrvl_combined_tag_keeps_its_own_periods(mrvl_bundle) -> None:
    """Per-period precedence: the combined tag still owns FY2023 (304.9m as
    filed); only the years it misses are component-filled."""
    by_year = {y.fiscal_year: y for y in mrvl_bundle.financials}
    assert by_year[2023].depreciation_amortization == pytest.approx(
        304_900_000.0, rel=REL_TOL
    )
    # FY2025 (missed by the combined tag) is component-filled: 177.0m +
    # 1,052.6m + 304.3m + 34.3m.
    assert by_year[2025].depreciation_amortization == pytest.approx(
        1_568_200_000.0, rel=REL_TOL
    )


# ---------------------------------------------------------------------------
# /statements endpoint exposes the extended fields (CRWD-fixture-backed)
# ---------------------------------------------------------------------------


@pytest.fixture()
def crwd_api(client: TestClient, tmp_path: Path) -> Iterator[TestClient]:
    provider = _crwd_provider(tmp_path)
    app.dependency_overrides[get_provider_dep] = lambda: provider
    yield client
    app.dependency_overrides.pop(get_provider_dep, None)


def test_statements_endpoint_includes_extended_fields(crwd_api: TestClient) -> None:
    resp = crwd_api.get("/api/companies/CRWD/statements")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert [y["fiscal_year"] for y in body["years"]][:1] == [2026]
    fy2026 = body["years"][0]
    income = fy2026["income_statement"]
    assert income["revenue"] == pytest.approx(4_812_005_000.0, rel=REL_TOL)
    assert income["ebitda"] == pytest.approx(266_954_000.0, rel=REL_TOL)
    assert income["research_development"] == pytest.approx(1_384_770_000.0, rel=REL_TOL)
    assert income["selling_general_admin"] == pytest.approx(2_501_598_000.0, rel=REL_TOL)
    assert income["pretax_income"] == pytest.approx(-126_989_000.0, rel=REL_TOL)
    assert income["eps_basic"] == pytest.approx(-0.65, rel=REL_TOL)
    assert income["eps_diluted"] == pytest.approx(-0.65, rel=REL_TOL)
    assert income["shares_diluted"] == pytest.approx(250_576_000.0, rel=REL_TOL)
    balance = fy2026["balance_sheet"]
    assert balance["total_assets"] == pytest.approx(11_086_684_000.0, rel=REL_TOL)
    assert balance["total_liabilities"] == pytest.approx(6_614_079_000.0, rel=REL_TOL)
    assert balance["goodwill"] == pytest.approx(1_363_294_000.0, rel=REL_TOL)
    assert balance["intangible_assets"] == pytest.approx(136_702_000.0, rel=REL_TOL)
    assert balance["ppe_net"] == pytest.approx(976_331_000.0, rel=REL_TOL)
    assert balance["long_term_debt"] == pytest.approx(745_471_000.0, rel=REL_TOL)
    assert balance["retained_earnings"] == pytest.approx(-1_283_042_000.0, rel=REL_TOL)
    cash_flow = fy2026["cash_flow"]
    assert cash_flow["stock_based_compensation"] == pytest.approx(
        1_096_679_000.0, rel=REL_TOL
    )
    assert cash_flow["investing_cash_flow"] == pytest.approx(-764_479_000.0, rel=REL_TOL)
    assert cash_flow["financing_cash_flow"] == pytest.approx(132_452_000.0, rel=REL_TOL)


def test_financials_endpoint_carries_extended_fields_through(
    crwd_api: TestClient,
) -> None:
    """/financials serves the canonical rows, so the §19.8 fields ride along."""
    resp = crwd_api.get("/api/companies/CRWD/financials")
    assert resp.status_code == 200, resp.text
    latest = resp.json()["years"][-1]
    assert latest["fiscal_year"] == 2026
    assert latest["eps_diluted"] == pytest.approx(-0.65, rel=REL_TOL)
    assert latest["total_assets"] == pytest.approx(11_086_684_000.0, rel=REL_TOL)
