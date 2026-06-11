"""LBO model schemas (spec §8, §12). All rates are decimals (0.05 = 5%)."""

from pydantic import BaseModel, Field, model_validator


class LboAssumptions(BaseModel):
    entry_multiple: float  # EV / entry EBITDA
    debt_multiple: float  # opening debt / entry EBITDA (validated < entry_multiple)
    revenue_growth: list[float]  # length == holding_period
    ebitda_margin: list[float]  # length == holding_period
    capex_pct_revenue: float
    nwc_pct_revenue: float  # ΔNWC = this × Δrevenue (spec §2.9)
    tax_rate: float
    interest_rate: float  # cash interest on beginning-of-year debt
    mandatory_repayment_pct: float  # % of ORIGINAL opening debt repaid per year
    exit_multiple: float
    holding_period: int = Field(default=5, ge=1, le=7)

    @model_validator(mode="after")
    def _validate(self) -> "LboAssumptions":
        if len(self.revenue_growth) != self.holding_period:
            raise ValueError(
                f"revenue_growth must have exactly {self.holding_period} entries "
                f"(one per holding-period year), got {len(self.revenue_growth)}"
            )
        if len(self.ebitda_margin) != self.holding_period:
            raise ValueError(
                f"ebitda_margin must have exactly {self.holding_period} entries "
                f"(one per holding-period year), got {len(self.ebitda_margin)}"
            )
        if not self.debt_multiple < self.entry_multiple:
            raise ValueError(
                "debt_multiple must be strictly less than entry_multiple "
                f"({self.debt_multiple} >= {self.entry_multiple})"
            )
        return self


class LboEntry(BaseModel):
    entry_ebitda: float
    entry_revenue: float
    entry_ev: float
    opening_debt: float
    sponsor_equity: float
    equity_pct: float


class LboYear(BaseModel):
    year: int
    revenue: float
    ebitda: float
    capex: float
    delta_nwc: float
    interest: float
    taxes: float
    fcf: float
    debt_repaid: float
    ending_debt: float
    ending_cash: float


class LboExit(BaseModel):
    exit_ebitda: float
    exit_ev: float
    ending_debt: float
    ending_cash: float
    exit_equity: float
    mom: float | None = None
    irr: float | None = None


class SensitivityGrid(BaseModel):
    row_label: str
    col_label: str
    rows: list[float]
    cols: list[float]
    values: list[list[float | None]]  # values[i][j] for rows[i] × cols[j]


class LboSensitivities(BaseModel):
    irr_exit_vs_growth: SensitivityGrid
    irr_entry_vs_exit: SensitivityGrid
    mom_exit_vs_margin: SensitivityGrid


class LboResponse(BaseModel):
    ticker: str
    entry: LboEntry
    years: list[LboYear]
    exit: LboExit
    sensitivities: LboSensitivities
    assumptions: LboAssumptions  # echo of inputs
    warnings: list[str] = Field(default_factory=list)


class LboDefaultsResponse(BaseModel):
    """Response for GET /api/companies/{ticker}/lbo/defaults (spec §12)."""

    assumptions: LboAssumptions
    basis: dict[str, str] = Field(default_factory=dict)
