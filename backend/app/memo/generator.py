"""Deterministic investment memo generator (spec §10).

Templates are filled ONLY from computed data (profile, KPIs, valuation, LBO,
score). No facts are invented; missing data is stated as missing. Consumes
schema objects only — never imports from app.kpis / app.lbo / app.valuation.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.company import CompanyProfile
from app.schemas.kpi import KpiResponse, TracedValue
from app.schemas.lbo import LboResponse
from app.schemas.memo import (
    MEMO_DISCLAIMER,
    MEMO_SECTION_KEYS,
    MemoResponse,
    MemoSection,
)
from app.schemas.score import ScoreResponse
from app.schemas.valuation import ValuationResponse
from app.scoring.model import fmt_currency, fmt_multiple, fmt_percent, fmt_value

SECTION_TITLES: dict[str, str] = {
    "company_overview": "Company Overview",
    "investment_thesis": "Investment Thesis",
    "financial_highlights": "Financial Highlights",
    "kpi_summary": "KPI Summary",
    "lbo_case_summary": "LBO Case Summary",
    "valuation_view": "Valuation View",
    "key_risks": "Key Risks",
    "data_gaps": "Data Gaps",
    "screening_view": "Screening View",
}

NO_GAPS_LINE = "No material data gaps identified in the fields used."
THESIS_FALLBACK = "Limited affirmative thesis support from available data."
PUBLIC_MARKET_RISK = (
    "Public-market valuation may already reflect the qualities identified above."
)

# KPI display order for the summary section.
_KPI_SUMMARY_ORDER = [
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
]


def _kpi_value(kpi_map: dict[str, TracedValue], key: str) -> float | None:
    tv = kpi_map.get(key)
    return tv.value if tv is not None else None


def _collect_data_gaps(
    profile: CompanyProfile,
    kpis: KpiResponse,
    valuation: ValuationResponse | None,
    lbo: LboResponse | None,
) -> list[str]:
    """Aggregate every warning from the bundle, KPIs, valuation and LBO (deduped)."""
    gaps: list[str] = []

    def add(warnings: list[str]) -> None:
        for w in warnings:
            if w and w not in gaps:
                gaps.append(w)

    add(profile.warnings)
    for tv in kpis.kpis:
        add(tv.warnings)
    if valuation is not None:
        add(valuation.warnings)
        for tv in valuation.multiples:
            add(tv.warnings)
    if lbo is not None:
        add(lbo.warnings)
    return gaps


# ---------------------------------------------------------------------------
# Section builders — must never emit the literal strings "None" or "nan"
# ---------------------------------------------------------------------------


def _company_overview(profile: CompanyProfile) -> str:
    lines: list[str] = [f"**{profile.name} ({profile.ticker})**", ""]
    if profile.description:
        lines += [profile.description, ""]
    facts: list[str] = []
    classification = " / ".join(b for b in (profile.sector, profile.industry) if b)
    if classification:
        facts.append(f"- Sector and industry: {classification}")
    if profile.exchange:
        facts.append(f"- Exchange: {profile.exchange}")
    if profile.share_price is not None:
        facts.append(f"- Share price: ${profile.share_price:.2f}")
    if profile.market_cap is not None:
        facts.append(f"- Market capitalization: {fmt_currency(profile.market_cap)}")
    if profile.enterprise_value is not None:
        facts.append(f"- Enterprise value: {fmt_currency(profile.enterprise_value)}")
    if facts:
        lines += facts + [""]
    source = f"Data source: {profile.data_source}"
    if profile.data_as_of:
        source += f" (data as of {profile.data_as_of})"
    source += "."
    lines.append(source)
    return "\n".join(lines)


def _investment_thesis(kpi_map: dict[str, TracedValue]) -> str:
    bullets: list[str] = []
    v = _kpi_value(kpi_map, "fcf_conversion")
    if v is not None and v > 0.6:
        bullets.append(
            f"- Strong cash conversion supports deleveraging "
            f"(FCF conversion of {fmt_percent(v)})."
        )
    v = _kpi_value(kpi_map, "revenue_cagr_3y")
    if v is not None and v > 0.07:
        bullets.append(
            f"- Consistent top-line growth ({fmt_percent(v)} 3-year revenue CAGR) "
            "supports the equity build."
        )
    v = _kpi_value(kpi_map, "ebitda_margin")
    if v is not None and v > 0.2:
        bullets.append(
            f"- EBITDA margin of {fmt_percent(v)} indicates a profitable operating model."
        )
    v = _kpi_value(kpi_map, "net_debt_to_ebitda")
    if v is not None and v < 2.0:
        bullets.append(
            f"- Modest existing leverage (net debt / EBITDA of {fmt_multiple(v)}) "
            "leaves headroom for an LBO capital structure."
        )
    if len(bullets) < 2:
        lines = [THESIS_FALLBACK]
        if bullets:
            lines += [""] + bullets
        return "\n".join(lines)
    return "\n".join(bullets)


def _financial_highlights(profile: CompanyProfile) -> str:
    fy = (
        f"FY{profile.latest_fiscal_year}"
        if profile.latest_fiscal_year is not None
        else "the latest fiscal year"
    )
    items: list[tuple[str, float | None]] = [
        ("Revenue", profile.revenue),
        ("EBITDA", profile.ebitda),
        ("Net income", profile.net_income),
        ("Free cash flow", profile.free_cash_flow),
        ("Cash and equivalents", profile.cash),
        ("Total debt", profile.total_debt),
        ("Net debt", profile.net_debt),
    ]
    bullets = [f"- {label}: {fmt_currency(v)}" for label, v in items if v is not None]
    missing = [label for label, v in items if v is None]
    if bullets:
        lines = [f"Key figures for {fy}:", ""] + bullets
    else:
        lines = ["Financial highlights are not available from the data source used."]
    if missing and bullets:
        lines += ["", f"Not available: {', '.join(missing)}."]
    return "\n".join(lines)


def _kpi_summary(kpis: KpiResponse, kpi_map: dict[str, TracedValue]) -> str:
    bullets: list[str] = []
    seen: set[str] = set()
    for key in _KPI_SUMMARY_ORDER + [k.key for k in kpis.kpis]:
        if key in seen:
            continue
        seen.add(key)
        tv = kpi_map.get(key)
        if tv is None:
            continue
        if tv.value is not None:
            bullets.append(f"- {tv.label} ({tv.period}): {fmt_value(tv.value, tv.unit)}")
        else:
            bullets.append(f"- {tv.label}: not available")
    if not bullets:
        return "KPI data is not available for this company."
    return "\n".join(bullets)


def _lbo_case_summary(lbo: LboResponse | None) -> str:
    if lbo is None:
        return (
            "An LBO case is not available; the model could not be run on the "
            "data provided."
        )
    a = lbo.assumptions
    e = lbo.entry
    x = lbo.exit
    lines = [
        (
            f"Entry at {fmt_multiple(a.entry_multiple)} EV/EBITDA implies an "
            f"enterprise value of {fmt_currency(e.entry_ev)}, funded with "
            f"{fmt_currency(e.opening_debt)} of debt "
            f"({fmt_multiple(a.debt_multiple)} EBITDA) and "
            f"{fmt_currency(e.sponsor_equity)} of sponsor equity "
            f"({fmt_percent(e.equity_pct)} of the structure)."
        ),
        (
            f"Exit in year {a.holding_period} at {fmt_multiple(a.exit_multiple)} "
            f"EV/EBITDA on exit EBITDA of {fmt_currency(x.exit_ebitda)} implies "
            f"exit equity of {fmt_currency(x.exit_equity)}."
        ),
    ]
    returns: list[str] = []
    if x.mom is not None:
        returns.append(f"{fmt_multiple(x.mom)} money-on-money")
    if x.irr is not None:
        returns.append(f"{fmt_percent(x.irr)} IRR")
    if returns:
        lines.append(
            f"Modelled returns: {' and '.join(returns)} over the "
            f"{a.holding_period}-year hold."
        )
    else:
        lines.append("Modelled returns could not be computed for these assumptions.")
    return "\n\n".join(lines)


def _valuation_view(valuation: ValuationResponse | None) -> str:
    if valuation is None:
        return "A multiples-based valuation range is not available."
    lines: list[str] = []
    mult_map = {tv.key: tv for tv in valuation.multiples}
    ev_ebitda = mult_map.get("ev_ebitda")
    if ev_ebitda is not None and ev_ebitda.value is not None:
        lines.append(
            f"The company currently trades at {fmt_multiple(ev_ebitda.value)} EV/EBITDA."
        )
    a = valuation.assumptions
    lines.append(
        f"Applying EV/EBITDA multiples of {fmt_multiple(a.low)} / "
        f"{fmt_multiple(a.base)} / {fmt_multiple(a.high)} (low / base / high):"
    )
    for case in valuation.range:
        parts: list[str] = []
        if case.implied_ev is not None:
            parts.append(f"implied EV {fmt_currency(case.implied_ev)}")
        if case.implied_equity is not None:
            parts.append(f"implied equity {fmt_currency(case.implied_equity)}")
        if case.implied_share_price is not None:
            parts.append(f"implied share price ${case.implied_share_price:.2f}")
        if case.premium_vs_current is not None:
            parts.append(f"{fmt_percent(case.premium_vs_current)} vs the current price")
        detail = ", ".join(parts) if parts else "implied values not available"
        lines.append(f"- {case.case.capitalize()} ({fmt_multiple(case.multiple)}): {detail}")
    lines.append(
        "These multiples-based figures are screening aids, not a definitive valuation."
    )
    return "\n".join(lines)


def _key_risks(kpi_map: dict[str, TracedValue], data_gaps: list[str]) -> str:
    bullets: list[str] = []
    v = _kpi_value(kpi_map, "net_debt_to_ebitda")
    if v is not None and v > 3:
        bullets.append(f"- Elevated existing leverage: net debt / EBITDA of {fmt_multiple(v)}.")
    v = _kpi_value(kpi_map, "revenue_growth_yoy")
    if v is not None and v < 0:
        bullets.append(f"- Declining revenue: {fmt_percent(v)} year over year.")
    v = _kpi_value(kpi_map, "fcf_margin")
    if v is not None and v < 0.05:
        bullets.append(f"- Weak free cash flow generation: FCF margin of {fmt_percent(v)}.")
    v = _kpi_value(kpi_map, "interest_coverage")
    if v is not None and v < 3:
        bullets.append(f"- Thin interest coverage: EBITDA covers interest {fmt_multiple(v)}.")
    if data_gaps:
        bullets.append(
            "- Data quality: one or more inputs were missing or derived; "
            "see the Data Gaps section."
        )
    bullets.append(f"- {PUBLIC_MARKET_RISK}")
    return "\n".join(bullets)


def _data_gaps_section(data_gaps: list[str]) -> str:
    if not data_gaps:
        return NO_GAPS_LINE
    return "\n".join(f"- {gap}" for gap in data_gaps)


def _screening_view(score: ScoreResponse) -> str:
    justifications = {
        "Attractive": (
            "The mechanical screen supports further diligence on this company "
            "as an LBO candidate."
        ),
        "Watchlist": (
            "The mechanical screen shows a mixed profile; monitor for improved "
            "fundamentals or a better entry point."
        ),
        "Pass": (
            "The mechanical screen does not support prioritising this company "
            "on current metrics."
        ),
    }
    justification = justifications.get(
        score.rating, "See the component breakdown for details."
    )
    return (
        f"**{score.rating}** — deal score of {score.total:.1f}/100. {justification}"
        f"\n\n{score.disclaimer}"
    )


def generate_memo(
    profile: CompanyProfile,
    kpis: KpiResponse,
    valuation: ValuationResponse | None,
    lbo: LboResponse | None,
    score: ScoreResponse,
) -> MemoResponse:
    """Generate the nine-section investment memo (spec §10) from computed data."""
    kpi_map = {tv.key: tv for tv in kpis.kpis}
    data_gaps = _collect_data_gaps(profile, kpis, valuation, lbo)

    contents: dict[str, str] = {
        "company_overview": _company_overview(profile),
        "investment_thesis": _investment_thesis(kpi_map),
        "financial_highlights": _financial_highlights(profile),
        "kpi_summary": _kpi_summary(kpis, kpi_map),
        "lbo_case_summary": _lbo_case_summary(lbo),
        "valuation_view": _valuation_view(valuation),
        "key_risks": _key_risks(kpi_map, data_gaps),
        "data_gaps": _data_gaps_section(data_gaps),
        "screening_view": _screening_view(score),
    }
    sections = [
        MemoSection(key=key, title=SECTION_TITLES[key], content=contents[key])
        for key in MEMO_SECTION_KEYS
    ]
    return MemoResponse(
        ticker=profile.ticker,
        generated_at=datetime.now(timezone.utc).isoformat(),
        rating=score.rating,
        sections=sections,
        data_gaps=data_gaps,
        disclaimer=MEMO_DISCLAIMER,
    )
