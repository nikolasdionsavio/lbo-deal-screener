"""Deal score engine (spec §9).

Consumes schema objects only (KpiResponse, valuation TracedValues) — never
imports from app.kpis / app.lbo / app.valuation.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.kpi import KpiResponse, TracedValue
from app.schemas.score import SCORE_DISCLAIMER, ScoreComponent, ScoreResponse

# ---------------------------------------------------------------------------
# Formatting helpers (internal to scoring/memo; spec formats $X.Xbn / X.X% / X.Xx)
# ---------------------------------------------------------------------------


def fmt_percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def fmt_multiple(value: float) -> str:
    return f"{value:.1f}x"


def fmt_ratio(value: float) -> str:
    return f"{value:.1f}"


# Spec §4: USD -> $, GBP -> £, EUR -> €; any other ISO code is prefixed
# verbatim ("SEK 1.2bn"). None ≡ USD for legacy callers.
_CURRENCY_SYMBOLS = {"USD": "$", "GBP": "£", "EUR": "€"}


def _currency_prefix(currency: str | None) -> str:
    code = (currency or "USD").upper()
    symbol = _CURRENCY_SYMBOLS.get(code)
    return symbol if symbol is not None else f"{code} "


def fmt_currency(value: float, currency: str | None = None) -> str:
    prefix = _currency_prefix(currency)
    sign = "-" if value < 0 else ""
    v = abs(value)
    if v >= 1e12:
        return f"{sign}{prefix}{v / 1e12:.1f}tn"
    if v >= 1e9:
        return f"{sign}{prefix}{v / 1e9:.1f}bn"
    if v >= 1e6:
        return f"{sign}{prefix}{v / 1e6:.1f}m"
    return f"{sign}{prefix}{v:,.0f}"


def fmt_value(value: float, unit: str, currency: str | None = None) -> str:
    if unit == "percent":
        return fmt_percent(value)
    if unit == "multiple":
        return fmt_multiple(value)
    if unit == "currency":
        return fmt_currency(value, currency)
    if unit == "per_share":
        return f"{_currency_prefix(currency)}{value:.2f}"
    return fmt_ratio(value)


def _compact(x: float) -> str:
    """Compact bound formatting: 0.0 -> "0", 15.0 -> "15", 0.8 -> "0.8"."""
    return f"{x:g}"


# ---------------------------------------------------------------------------
# Component table (spec §9) — weights MUST sum to 1.0
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InputSpec:
    key: str
    label: str  # fallback label when the TracedValue is absent
    unit: str  # "percent" | "multiple" | "ratio"
    worst: float
    best: float  # worst > best means lower-is-better (inverted range)
    source: str  # "kpi" | "valuation"


@dataclass(frozen=True)
class ComponentSpec:
    key: str
    label: str
    weight: float
    inputs: tuple[InputSpec, ...]


COMPONENT_SPECS: tuple[ComponentSpec, ...] = (
    ComponentSpec(
        "growth",
        "Growth",
        0.20,
        (InputSpec("revenue_cagr_3y", "3-year revenue CAGR", "percent", 0.0, 0.15, "kpi"),),
    ),
    ComponentSpec(
        "margins",
        "Margins",
        0.20,
        (
            InputSpec("ebitda_margin", "EBITDA margin", "percent", 0.05, 0.30, "kpi"),
            InputSpec("gross_margin", "Gross margin", "percent", 0.20, 0.60, "kpi"),
        ),
    ),
    ComponentSpec(
        "cash_conversion",
        "Cash Conversion",
        0.20,
        (
            InputSpec("fcf_conversion", "FCF conversion", "percent", 0.20, 0.80, "kpi"),
            InputSpec("fcf_margin", "FCF margin", "percent", 0.00, 0.15, "kpi"),
        ),
    ),
    ComponentSpec(
        "leverage_capacity",
        "Leverage Capacity",
        0.15,
        (
            InputSpec("net_debt_to_ebitda", "Net debt / EBITDA", "multiple", 4.0, 0.0, "kpi"),
            InputSpec("interest_coverage", "Interest coverage", "multiple", 1.0, 8.0, "kpi"),
        ),
    ),
    ComponentSpec(
        "valuation",
        "Valuation",
        0.15,
        (
            InputSpec("ev_ebitda", "EV / EBITDA", "multiple", 16.0, 6.0, "valuation"),
            InputSpec("fcf_yield", "FCF yield", "percent", 0.02, 0.08, "valuation"),
        ),
    ),
    ComponentSpec(
        "balance_sheet_risk",
        "Balance Sheet Risk",
        0.10,
        (
            InputSpec("current_ratio", "Current ratio", "ratio", 0.8, 2.0, "kpi"),
            InputSpec("debt_to_ebitda", "Total debt / EBITDA", "multiple", 5.0, 1.0, "kpi"),
        ),
    ),
)


def linear_score(value: float, worst: float, best: float) -> float:
    """Linear 0–100 score, clamped. worst > best inverts the scale."""
    if worst == best:
        raise ValueError("linear_score requires worst != best")
    raw = (value - worst) / (best - worst) * 100.0
    return min(100.0, max(0.0, raw))


def rating_for(total: float) -> str:
    if total >= 70:
        return "Attractive"
    if total >= 50:
        return "Watchlist"
    return "Pass"


def _scale_text(inp: InputSpec) -> str:
    if inp.unit == "percent":
        return f"{_compact(inp.worst * 100)}–{_compact(inp.best * 100)}%"
    if inp.unit == "multiple":
        return f"{_compact(inp.worst)}x–{_compact(inp.best)}x"
    return f"{_compact(inp.worst)}–{_compact(inp.best)}"


def compute_score(
    kpis: KpiResponse,
    valuation_multiples: list[TracedValue] | None = None,
) -> ScoreResponse:
    """Compute the transparent 0–100 deal score per the spec §9 component table.

    Per component: average of the available input scores. If ALL inputs of a
    component are missing, its score is None and its weight is redistributed
    proportionally across the available components (with a warning).
    """
    kpi_map = {tv.key: tv for tv in kpis.kpis}
    val_map = {tv.key: tv for tv in (valuation_multiples or [])}

    drafts: list[tuple[ComponentSpec, float | None, list[TracedValue], list[str], str]] = []
    for spec in COMPONENT_SPECS:
        inputs: list[TracedValue] = []
        warnings: list[str] = []
        clauses: list[str] = []
        scores: list[float] = []
        for inp in spec.inputs:
            lookup = kpi_map if inp.source == "kpi" else val_map
            tv = lookup.get(inp.key)
            if tv is None:
                tv = TracedValue(
                    key=inp.key,
                    label=inp.label,
                    value=None,
                    unit=inp.unit,  # type: ignore[arg-type]
                    period="n/a",
                    formula="n/a",
                    warnings=[f"{inp.label} was not provided to the scoring engine"],
                )
            inputs.append(tv)
            if tv.value is None:
                warnings.append(
                    f"{inp.label} unavailable; excluded from the {spec.label} score"
                )
                continue
            s = linear_score(tv.value, inp.worst, inp.best)
            scores.append(s)
            label = tv.label or inp.label
            clauses.append(
                f"{label} of {fmt_value(tv.value, inp.unit)} scores "
                f"{round(s)}/100 on a {_scale_text(inp)} scale"
            )
        if scores:
            comp_score: float | None = sum(scores) / len(scores)
            reason = ". ".join(clauses) + "."
        else:
            comp_score = None
            reason = (
                f"No {spec.label} inputs available; its {fmt_percent(spec.weight)} "
                "weight was redistributed proportionally across the remaining components."
            )
            warnings.append(
                f"All {spec.label} inputs missing; weight redistributed "
                "proportionally across available components"
            )
        drafts.append((spec, comp_score, inputs, warnings, reason))

    available_weight = sum(spec.weight for spec, score, *_ in drafts if score is not None)

    components: list[ScoreComponent] = []
    total_points = 0.0
    for spec, comp_score, inputs, warnings, reason in drafts:
        if comp_score is None or available_weight <= 0:
            effective_weight = 0.0
            weighted_points: float | None = None
        else:
            effective_weight = spec.weight / available_weight
            weighted_points = effective_weight * comp_score
            total_points += weighted_points
        components.append(
            ScoreComponent(
                key=spec.key,
                label=spec.label,
                weight=spec.weight,
                effective_weight=effective_weight,
                score=comp_score,
                weighted_points=weighted_points,
                reason=reason,
                inputs=inputs,
                warnings=warnings,
            )
        )

    total = round(total_points, 1)
    return ScoreResponse(
        ticker=kpis.ticker,
        as_of=kpis.as_of,
        total=total,
        rating=rating_for(total),
        components=components,
        disclaimer=SCORE_DISCLAIMER,
    )
