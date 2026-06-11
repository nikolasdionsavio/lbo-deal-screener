"""LBO sensitivity grids (spec §8): three 5x5 grids, full model recomputed per
cell via `run_core`.

1. irr_exit_vs_growth: exit multiple (base-2 .. base+2, step 1) x uniform shift
   of every year's revenue growth by {-4, -2, 0, +2, +4} pp.
2. irr_entry_vs_exit: entry multiple base+-2 (re-deriving EV/debt/equity, with
   debt_multiple clamped to entry_multiple - 0.5 for minimum equity) x exit
   multiple base+-2.
3. mom_exit_vs_margin: exit multiple base+-2 x uniform shift of every year's
   EBITDA margin by {-4, -2, 0, +2, +4} pp (margins clamped to >= 1%).
"""

from __future__ import annotations

from app.lbo.engine import run_core
from app.schemas.lbo import LboAssumptions, LboSensitivities, SensitivityGrid

__all__ = ["compute_sensitivities"]

_MULTIPLE_OFFSETS = (-2.0, -1.0, 0.0, 1.0, 2.0)
_PP_SHIFTS = (-0.04, -0.02, 0.0, 0.02, 0.04)
_MIN_MARGIN = 0.01
_DEBT_HEADROOM = 0.5  # debt_multiple clamped to entry_multiple - 0.5


def _exit_irr(
    entry_ebitda: float, entry_revenue: float, assumptions: LboAssumptions
) -> float | None:
    _, _, exit_block, _ = run_core(entry_ebitda, entry_revenue, assumptions)
    return exit_block.irr


def _exit_mom(
    entry_ebitda: float, entry_revenue: float, assumptions: LboAssumptions
) -> float | None:
    _, _, exit_block, _ = run_core(entry_ebitda, entry_revenue, assumptions)
    return exit_block.mom


def compute_sensitivities(
    entry_ebitda: float,
    entry_revenue: float,
    assumptions: LboAssumptions,
) -> LboSensitivities:
    a = assumptions
    exit_rows = [a.exit_multiple + d for d in _MULTIPLE_OFFSETS]
    entry_rows = [a.entry_multiple + d for d in _MULTIPLE_OFFSETS]

    # 1. IRR: exit multiple x uniform revenue-growth shift.
    growth_values: list[list[float | None]] = []
    for exit_m in exit_rows:
        row: list[float | None] = []
        for shift in _PP_SHIFTS:
            # model_copy skips re-validation; lengths and ordering are preserved.
            cell = a.model_copy(
                update={
                    "exit_multiple": exit_m,
                    "revenue_growth": [g + shift for g in a.revenue_growth],
                }
            )
            row.append(_exit_irr(entry_ebitda, entry_revenue, cell))
        growth_values.append(row)
    irr_exit_vs_growth = SensitivityGrid(
        row_label="Exit multiple (EV/EBITDA)",
        col_label="Revenue growth shift",
        rows=exit_rows,
        cols=list(_PP_SHIFTS),
        values=growth_values,
    )

    # 2. IRR: entry multiple x exit multiple, re-deriving the capital structure
    # per row with the debt clamp.
    entry_exit_values: list[list[float | None]] = []
    for entry_m in entry_rows:
        row = []
        for exit_m in exit_rows:
            if entry_m <= 0:
                row.append(None)  # non-positive entry EV is not meaningful
                continue
            debt_m = max(0.0, min(a.debt_multiple, entry_m - _DEBT_HEADROOM))
            cell = a.model_copy(
                update={
                    "entry_multiple": entry_m,
                    "debt_multiple": debt_m,
                    "exit_multiple": exit_m,
                }
            )
            row.append(_exit_irr(entry_ebitda, entry_revenue, cell))
        entry_exit_values.append(row)
    irr_entry_vs_exit = SensitivityGrid(
        row_label="Entry multiple (EV/EBITDA)",
        col_label="Exit multiple (EV/EBITDA)",
        rows=entry_rows,
        cols=exit_rows,
        values=entry_exit_values,
    )

    # 3. MoM: exit multiple x uniform EBITDA-margin shift (clamped >= 1%).
    margin_values: list[list[float | None]] = []
    for exit_m in exit_rows:
        row = []
        for shift in _PP_SHIFTS:
            cell = a.model_copy(
                update={
                    "exit_multiple": exit_m,
                    "ebitda_margin": [
                        max(_MIN_MARGIN, m + shift) for m in a.ebitda_margin
                    ],
                }
            )
            row.append(_exit_mom(entry_ebitda, entry_revenue, cell))
        margin_values.append(row)
    mom_exit_vs_margin = SensitivityGrid(
        row_label="Exit multiple (EV/EBITDA)",
        col_label="EBITDA margin shift",
        rows=exit_rows,
        cols=list(_PP_SHIFTS),
        values=margin_values,
    )

    return LboSensitivities(
        irr_exit_vs_growth=irr_exit_vs_growth,
        irr_entry_vs_exit=irr_entry_vs_exit,
        mom_exit_vs_margin=mom_exit_vs_margin,
    )
