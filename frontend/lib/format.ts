// Number formatting helpers (docs/BUILD_SPEC.md section 14).
// Currency auto-scales ($1.23tn / $456.7bn / $89.1m); null renders as an em dash.

const NOT_AVAILABLE = "—"; // —

function isMissing(value: number | null | undefined): value is null | undefined {
  return value === null || value === undefined || !Number.isFinite(value);
}

export function fmtCurrency(value: number | null | undefined): string {
  if (isMissing(value)) return NOT_AVAILABLE;
  const sign = value < 0 ? "-" : "";
  const abs = Math.abs(value);
  if (abs >= 1e12) return `${sign}$${(abs / 1e12).toFixed(2)}tn`;
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(1)}bn`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(1)}m`;
  return `${sign}$${abs.toLocaleString("en-US", {
    minimumFractionDigits: abs < 1000 ? 2 : 0,
    maximumFractionDigits: 2,
  })}`;
}

export function fmtPercent(
  value: number | null | undefined,
  options: { digits?: number; signed?: boolean } = {},
): string {
  if (isMissing(value)) return NOT_AVAILABLE;
  const { digits = 1, signed = false } = options;
  const pct = value * 100;
  const sign = signed && pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(digits)}%`;
}

export function fmtMultiple(value: number | null | undefined): string {
  if (isMissing(value)) return NOT_AVAILABLE;
  return `${value.toFixed(1)}x`;
}

export function fmtNumber(
  value: number | null | undefined,
  options: { digits?: number } = {},
): string {
  if (isMissing(value)) return NOT_AVAILABLE;
  const { digits = 0 } = options;
  return value.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}
