"""Company + sector risk computation (financial, market, sector), plus the
composite banding. Qualitative 10-K risk factors live in app.risk.factors.

All quantitative metrics are computed from the filed statements in the bundle
(SEC EDGAR), so every figure is traceable. Formulas and thresholds follow
standard credit / equity-research practice (Altman Z''-score, Piotroski
F-score, Sloan accruals, net-debt/EBITDA, interest coverage, current/quick
ratio, cash runway). Anything that cannot be computed returns an "n/a" flag
rather than a fabricated value.
"""

from __future__ import annotations

from app.schemas.company import CompanyDataBundle
from app.schemas.financials import FiscalYearFinancials
from app.schemas.market_stats import MarketStats
from app.schemas.peers import PeerRow
from app.schemas.risk import (
    DistressScore,
    RiskBand,
    RiskFlag,
    RiskMetric,
    SectorComparison,
)

__all__ = [
    "compute_financial_risk",
    "compute_market_risk",
    "compute_sector_risk",
    "financial_band",
]


def _f(x: float | None) -> float | None:
    return x if isinstance(x, (int, float)) else None


def _ratio(num: float | None, den: float | None) -> float | None:
    if num is None or den is None or den == 0:
        return None
    return num / den


def _ebit(y: FiscalYearFinancials) -> float | None:
    """EBIT, reconstructed when operating income is not tagged directly."""
    if y.operating_income is not None:
        return y.operating_income
    if y.pretax_income is not None and y.interest_expense is not None:
        return y.pretax_income + y.interest_expense
    if (
        y.net_income is not None
        and y.tax_expense is not None
        and y.interest_expense is not None
    ):
        return y.net_income + y.tax_expense + y.interest_expense
    return None


def _band_flag(value: float | None, low_below: float, high_above: float) -> RiskFlag:
    """Lower value = lower risk (e.g. leverage). low_below/high_above are cut points."""
    if value is None:
        return "na"
    if value < low_below:
        return "low"
    if value > high_above:
        return "high"
    return "medium"


def _band_flag_inv(value: float | None, high_below: float, low_above: float) -> RiskFlag:
    """Higher value = lower risk (e.g. coverage, current ratio)."""
    if value is None:
        return "na"
    if value > low_above:
        return "low"
    if value < high_below:
        return "high"
    return "medium"


# ---------------------------------------------------------------------------
# Distress scores
# ---------------------------------------------------------------------------


def _altman_z2(latest: FiscalYearFinancials) -> DistressScore:
    """Altman Z''-score for non-manufacturers (book value; no market data):
    Z'' = 6.56·X1 + 3.26·X2 + 6.72·X3 + 1.05·X4, with
    X1=WC/TA, X2=RE/TA, X3=EBIT/TA, X4=Book equity/Total liabilities.
    Zones: > 2.6 safe · 1.1–2.6 grey · < 1.1 distress."""
    ta = _f(latest.total_assets)
    formula = "6.56·(WC/TA) + 3.26·(RE/TA) + 6.72·(EBIT/TA) + 1.05·(Equity/Liabilities)"
    wc = (
        (latest.current_assets - latest.current_liabilities)
        if latest.current_assets is not None and latest.current_liabilities is not None
        else None
    )
    ebit = _ebit(latest)
    x1 = _ratio(wc, ta)
    x2 = _ratio(_f(latest.retained_earnings), ta)
    x3 = _ratio(ebit, ta)
    x4 = _ratio(_f(latest.total_equity), _f(latest.total_liabilities))
    if None in (x1, x2, x3, x4):
        return DistressScore(
            name="Altman Z''-score",
            score=None,
            formatted="—",
            zone="n/a",
            flag="na",
            interpretation=(
                "Not computable: one or more inputs (working capital, retained "
                "earnings, EBIT, equity or liabilities) is not available."
            ),
            formula=formula,
        )
    z = 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4
    if z > 2.6:
        zone, flag, note = "Safe", "low", "In the safe zone; low near-term distress risk."
    elif z >= 1.1:
        zone, flag, note = (
            "Grey",
            "medium",
            "In the grey zone; distress risk is not negligible, monitor leverage and earnings.",
        )
    else:
        zone, flag, note = (
            "Distress",
            "high",
            "In the distress zone; the model implies elevated bankruptcy risk.",
        )
    return DistressScore(
        name="Altman Z''-score",
        score=z,
        formatted=f"{z:.2f}",
        zone=zone,
        flag=flag,
        interpretation=note,
        formula=formula,
    )


def _piotroski(
    latest: FiscalYearFinancials, prior: FiscalYearFinancials | None
) -> DistressScore:
    """Piotroski F-score (0–9): 9 binary tests of profitability, leverage/
    liquidity and operating efficiency. ≥7 strong, ≤3 weak."""
    formula = "Sum of 9 binary tests (profitability, leverage/liquidity, efficiency)"
    if prior is None:
        return DistressScore(
            name="Piotroski F-score",
            score=None,
            formatted="—",
            zone="n/a",
            flag="na",
            interpretation="Needs two consecutive fiscal years; only one is available.",
            formula=formula,
        )
    pts = 0
    total = 0
    roa = _ratio(_f(latest.net_income), _f(latest.total_assets))
    roa_prior = _ratio(_f(prior.net_income), _f(prior.total_assets))
    cfo = _f(latest.operating_cash_flow)
    checks = [
        (roa, lambda: roa > 0),  # 1 ROA > 0
        (cfo, lambda: cfo > 0),  # 2 CFO > 0
        (roa if roa_prior is not None else None, lambda: roa > roa_prior),  # 3 ΔROA>0
        (
            cfo if latest.net_income is not None else None,
            lambda: cfo > latest.net_income,
        ),  # 4 accrual: CFO > NI
        (
            _ratio(_f(latest.long_term_debt), _f(latest.total_assets)),
            lambda: _ratio(_f(latest.long_term_debt), _f(latest.total_assets))
            < _ratio(_f(prior.long_term_debt), _f(prior.total_assets)),
        ),  # 5 Δleverage < 0
        (
            _ratio(_f(latest.current_assets), _f(latest.current_liabilities)),
            lambda: _ratio(_f(latest.current_assets), _f(latest.current_liabilities))
            > _ratio(_f(prior.current_assets), _f(prior.current_liabilities)),
        ),  # 6 Δcurrent ratio > 0
        (
            _f(latest.shares_outstanding),
            lambda: latest.shares_outstanding <= (prior.shares_outstanding or 0) * 1.01,
        ),  # 7 no meaningful share issuance
        (
            _ratio(_f(latest.gross_profit), _f(latest.revenue)),
            lambda: _ratio(_f(latest.gross_profit), _f(latest.revenue))
            > _ratio(_f(prior.gross_profit), _f(prior.revenue)),
        ),  # 8 Δgross margin > 0
        (
            _ratio(_f(latest.revenue), _f(latest.total_assets)),
            lambda: _ratio(_f(latest.revenue), _f(latest.total_assets))
            > _ratio(_f(prior.revenue), _f(prior.total_assets)),
        ),  # 9 Δasset turnover > 0
    ]
    for guard, test in checks:
        # Each test needs its prior-year counterpart too; guard against None.
        try:
            if guard is None:
                continue
            total += 1
            if test():
                pts += 1
        except (TypeError, ZeroDivisionError):
            continue
    if total < 5:
        return DistressScore(
            name="Piotroski F-score",
            score=None,
            formatted="—",
            zone="n/a",
            flag="na",
            interpretation="Insufficient two-year data to score reliably.",
            formula=formula,
        )
    if pts >= 7:
        zone, flag, note = "Strong", "low", "Financially strong across profitability, leverage and efficiency."
    elif pts >= 4:
        zone, flag, note = "Moderate", "medium", "Mixed financial-strength signals."
    else:
        zone, flag, note = "Weak", "high", "Weak on most fundamental-strength tests."
    return DistressScore(
        name="Piotroski F-score",
        score=float(pts),
        formatted=f"{pts} / 9",
        zone=zone,
        flag=flag,
        interpretation=note,
        formula=formula,
    )


# ---------------------------------------------------------------------------
# Financial risk metrics
# ---------------------------------------------------------------------------


def compute_financial_risk(
    bundle: CompanyDataBundle,
) -> tuple[list[DistressScore], list[RiskMetric], list[str]]:
    warnings: list[str] = []
    years = sorted(bundle.financials, key=lambda y: y.fiscal_year)
    if not years:
        return [], [], ["No financial statements available to assess financial risk."]
    latest = years[-1]
    prior = years[-2] if len(years) >= 2 else None

    distress = [_altman_z2(latest), _piotroski(latest, prior)]

    metrics: list[RiskMetric] = []

    # Net debt / EBITDA
    net_debt = (
        (latest.total_debt - (latest.cash_and_equivalents or 0.0))
        if latest.total_debt is not None
        else None
    )
    nd_ebitda = _ratio(net_debt, _f(latest.ebitda))
    metrics.append(
        RiskMetric(
            key="net_debt_ebitda",
            label="Net debt / EBITDA",
            value=nd_ebitda,
            formatted=f"{nd_ebitda:.1f}x" if nd_ebitda is not None else "—",
            flag=_band_flag(nd_ebitda, 2.0, 4.0),
            interpretation=(
                "Leverage is conservative." if (nd_ebitda or 0) < 2.0
                else "Leverage is high; limited debt headroom." if (nd_ebitda or 0) > 4.0
                else "Leverage is moderate."
            ) if nd_ebitda is not None else "Not available.",
            formula="(Total debt − cash) / EBITDA",
        )
    )

    # Interest coverage
    cov = _ratio(_ebit(latest), _f(latest.interest_expense))
    metrics.append(
        RiskMetric(
            key="interest_coverage",
            label="Interest coverage",
            value=cov,
            formatted=f"{cov:.1f}x" if cov is not None else "—",
            flag=_band_flag_inv(cov, 1.5, 4.0),
            interpretation=(
                "EBIT comfortably covers interest." if (cov or 0) > 4.0
                else "Thin interest coverage; earnings barely service the debt." if (cov or 0) < 1.5
                else "Adequate but leveraged interest coverage."
            ) if cov is not None else "Not available (no interest expense reported, or EBIT missing).",
            formula="EBIT / interest expense",
        )
    )

    # Current ratio
    cur = _ratio(_f(latest.current_assets), _f(latest.current_liabilities))
    metrics.append(
        RiskMetric(
            key="current_ratio",
            label="Current ratio",
            value=cur,
            formatted=f"{cur:.2f}" if cur is not None else "—",
            flag=_band_flag_inv(cur, 1.0, 2.0),
            interpretation=(
                "Comfortable short-term liquidity." if (cur or 0) > 2.0
                else "Current liabilities exceed current assets." if (cur or 0) < 1.0
                else "Adequate short-term liquidity."
            ) if cur is not None else "Not available.",
            formula="Current assets / current liabilities",
        )
    )

    # Quick ratio
    quick = (
        _ratio(
            (latest.current_assets - (latest.inventory or 0.0)),
            latest.current_liabilities,
        )
        if latest.current_assets is not None and latest.current_liabilities is not None
        else None
    )
    metrics.append(
        RiskMetric(
            key="quick_ratio",
            label="Quick ratio",
            value=quick,
            formatted=f"{quick:.2f}" if quick is not None else "—",
            flag=_band_flag_inv(quick, 0.5, 1.0),
            interpretation=(
                "Liquid even excluding inventory." if (quick or 0) > 1.0
                else "Weak liquidity once inventory is excluded." if (quick or 0) < 0.5
                else "Moderate liquidity excluding inventory."
            ) if quick is not None else "Not available.",
            formula="(Current assets − inventory) / current liabilities",
        )
    )

    # Cash runway (only meaningful when FCF is negative)
    fcf = _f(latest.free_cash_flow)
    if fcf is not None and fcf < 0:
        runway_years = _ratio(_f(latest.cash_and_equivalents), -fcf)
        runway_months = runway_years * 12 if runway_years is not None else None
        metrics.append(
            RiskMetric(
                key="cash_runway",
                label="Cash runway",
                value=runway_months,
                formatted=f"{runway_months:.0f} months" if runway_months is not None else "—",
                flag=_band_flag_inv(runway_months, 12.0, 24.0),
                interpretation=(
                    "The company is burning cash; this is how long the balance-sheet "
                    "cash lasts at the current burn rate before external financing is needed."
                ),
                formula="Cash & equivalents / annual free-cash-flow burn",
            )
        )

    # Sloan accruals ratio (earnings quality)
    sloan = (
        _ratio(
            (
                latest.net_income
                - (latest.operating_cash_flow or 0.0)
                - (latest.investing_cash_flow or 0.0)
            ),
            latest.total_assets,
        )
        if latest.net_income is not None
        and latest.operating_cash_flow is not None
        and latest.total_assets is not None
        else None
    )
    if sloan is not None:
        a = abs(sloan)
        flag: RiskFlag = "low" if a < 0.05 else "high" if a > 0.10 else "medium"
        metrics.append(
            RiskMetric(
                key="sloan_accruals",
                label="Accruals ratio (earnings quality)",
                value=sloan,
                formatted=f"{sloan * 100:+.1f}%",
                flag=flag,
                interpretation=(
                    "Earnings are largely cash-backed." if a < 0.05
                    else "Earnings are heavily accrual-driven, which tends to mean-revert; check receivables and inventory." if a > 0.10
                    else "Moderate accruals; earnings are reasonably cash-backed."
                ),
                formula="(Net income − operating cash flow − investing cash flow) / total assets",
            )
        )
    else:
        warnings.append("Accruals ratio unavailable (cash-flow statement lines missing).")

    return distress, metrics, warnings


# ---------------------------------------------------------------------------
# Market risk
# ---------------------------------------------------------------------------


def compute_market_risk(stats: MarketStats | None) -> list[RiskMetric]:
    if stats is None:
        return []
    metrics: list[RiskMetric] = []
    beta = _f(stats.stats.beta)
    if beta is not None:
        metrics.append(
            RiskMetric(
                key="beta",
                label="Beta",
                value=beta,
                formatted=f"{beta:.2f}",
                flag=_band_flag(beta, 1.0, 1.5),
                interpretation=(
                    "Less volatile than the market." if beta < 1.0
                    else "Materially more volatile than the market." if beta > 1.5
                    else "Roughly in line with market volatility."
                ),
                formula="Sensitivity of the share price to the market (systematic risk)",
            )
        )
    hi = _f(stats.stats.fifty_two_week_high)
    lo = _f(stats.stats.fifty_two_week_low)
    if hi is not None and lo is not None and lo > 0:
        width = (hi - lo) / lo
        metrics.append(
            RiskMetric(
                key="range_width",
                label="52-week range width",
                value=width,
                formatted=f"{width * 100:.0f}%",
                flag=_band_flag(width, 0.5, 1.0),
                interpretation=(
                    "A wide 52-week band indicates high realised price volatility."
                    if width > 1.0
                    else "A narrow trading band indicates lower realised volatility."
                    if width < 0.5
                    else "Moderate realised price volatility over the last year."
                ),
                formula="(52-week high − 52-week low) / 52-week low",
            )
        )
    return metrics


# ---------------------------------------------------------------------------
# Composite banding
# ---------------------------------------------------------------------------


def financial_band(
    distress: list[DistressScore], metrics: list[RiskMetric]
) -> tuple[RiskBand, str]:
    flags = [d.flag for d in distress] + [m.flag for m in metrics]
    highs = flags.count("high")
    z = next((d for d in distress if d.name.startswith("Altman")), None)
    z_distress = z is not None and z.flag == "high"
    if not any(f != "na" for f in flags):
        return "na", "Not enough financial data to assess financial risk."
    if z_distress or highs >= 3:
        return "high", "High financial risk: distress signals and/or multiple stretched credit metrics."
    if highs == 2:
        return "elevated", "Elevated financial risk: several credit metrics are outside comfortable ranges."
    if highs == 1:
        return "moderate", "Moderate financial risk: one credit metric warrants attention."
    return "low", "Low financial risk: leverage, coverage and liquidity are within healthy ranges."


# ---------------------------------------------------------------------------
# Sector (peer-relative) risk
# ---------------------------------------------------------------------------


def _median(values: list[float]) -> float | None:
    vals = sorted(values)
    n = len(vals)
    if n == 0:
        return None
    mid = n // 2
    return vals[mid] if n % 2 else (vals[mid - 1] + vals[mid]) / 2.0


def compute_sector_risk(
    target: PeerRow | None, peers: list[PeerRow]
) -> tuple[list[SectorComparison], str]:
    valued = [p for p in peers if p is not None]
    if target is None or len(valued) < 3:
        return [], (
            "Sector comparison needs a peer set of at least three valued companies; "
            "too few are available for this company."
        )
    out: list[SectorComparison] = []

    def cmp(
        metric: str,
        get,
        fmt,
        higher_is_riskier: bool,
        more_note: str,
        less_note: str,
    ) -> None:
        cv = get(target)
        pvals = [get(p) for p in valued if get(p) is not None]
        med = _median([v for v in pvals if v is not None])
        if cv is None or med is None:
            return
        worse = (cv > med) if higher_is_riskier else (cv < med)
        # "worse than median" -> medium flag; markedly worse -> high.
        ratio = (cv / med) if med not in (0, None) else 1.0
        if worse and (ratio > 1.5 or ratio < 0.66):
            flag: RiskFlag = "high"
        elif worse:
            flag = "medium"
        else:
            flag = "low"
        out.append(
            SectorComparison(
                metric=metric,
                company_value=cv,
                company_formatted=fmt(cv),
                peer_median=med,
                peer_median_formatted=fmt(med),
                peer_count=len(pvals),
                flag=flag,
                note=(more_note if worse else less_note),
            )
        )

    cmp(
        "EBITDA margin",
        lambda p: p.ebitda_margin,
        lambda v: f"{v * 100:.1f}%",
        higher_is_riskier=False,
        more_note="Lower margin than the peer median — thinner cushion against shocks.",
        less_note="Margin at or above the peer median.",
    )
    cmp(
        "Revenue growth",
        lambda p: p.revenue_growth_yoy,
        lambda v: f"{v * 100:.1f}%",
        higher_is_riskier=False,
        more_note="Growing slower than the peer median.",
        less_note="Growing at or above the peer median.",
    )
    cmp(
        "EV / EBITDA",
        lambda p: p.ev_ebitda,
        lambda v: f"{v:.1f}x",
        higher_is_riskier=True,
        more_note="Richer valuation than peers — more downside if the multiple de-rates.",
        less_note="Valued at or below the peer median.",
    )
    note = (
        f"Compared against {len(valued)} sector peers. A metric worse than the "
        "peer median is flagged as a relative risk."
    )
    return out, note
