"""Underwriting scenarios: base / strategic / downside exit cases.

A sponsor brackets the return rather than underwriting a single point. Each case
is a transparent, deterministic transformation of the base assumptions — no new
data and no hidden knobs — so the three IRRs read as a defensible range:

* base       — management-case operations at the base exit multiple.
* strategic  — a strategic buyer pays a control/synergy premium (+2.0x) at exit.
* downside   — a downturn: revenue growth −5pp a year and 2.0x of multiple
               compression at exit.
"""

from __future__ import annotations

from app.lbo.engine import run_core
from app.schemas.lbo import LboAssumptions, LboScenario

__all__ = ["compute_scenarios"]

_STRATEGIC_PREMIUM = 2.0  # +x turns of EV/EBITDA a strategic buyer pays at exit
_DOWNSIDE_MULTIPLE_HAIRCUT = 2.0  # −x turns of exit multiple in a downturn
_DOWNSIDE_GROWTH_SHIFT = 0.05  # −pp on every year's revenue growth in a downturn
_MIN_EXIT_MULTIPLE = 0.5


def compute_scenarios(
    entry_ebitda: float,
    entry_revenue: float,
    base: LboAssumptions,
) -> list[LboScenario]:
    """Run the three underwriting cases and return their headline returns."""
    strategic_exit = base.exit_multiple + _STRATEGIC_PREMIUM
    downside_exit = max(_MIN_EXIT_MULTIPLE, base.exit_multiple - _DOWNSIDE_MULTIPLE_HAIRCUT)
    downside_growth = [
        max(-0.99, g - _DOWNSIDE_GROWTH_SHIFT) for g in base.revenue_growth
    ]

    specs: list[tuple[str, str, str, dict]] = [
        (
            "downside",
            "Downturn",
            f"Revenue growth −{_DOWNSIDE_GROWTH_SHIFT:.0%} a year and "
            f"{_DOWNSIDE_MULTIPLE_HAIRCUT:.1f}x of exit-multiple compression.",
            {"exit_multiple": downside_exit, "revenue_growth": downside_growth},
        ),
        (
            "base",
            "Base case",
            "Management-case operations at the base exit multiple.",
            {},
        ),
        (
            "strategic",
            "Strategic sale",
            f"A strategic buyer pays a +{_STRATEGIC_PREMIUM:.1f}x control and "
            "synergy premium at exit.",
            {"exit_multiple": strategic_exit},
        ),
    ]

    out: list[LboScenario] = []
    for key, label, note, update in specs:
        # model_copy(update=...) skips re-validation; exit_multiple stays > 0 and
        # growth entries stay > -100% by construction above.
        assumptions = base.model_copy(update=update) if update else base
        _, _, exit_block, _ = run_core(entry_ebitda, entry_revenue, assumptions)
        out.append(
            LboScenario(
                key=key,  # type: ignore[arg-type]
                label=label,
                note=note,
                exit_multiple=assumptions.exit_multiple,
                irr=exit_block.irr,
                mom=exit_block.mom,
                exit_equity=exit_block.exit_equity,
            )
        )
    return out
