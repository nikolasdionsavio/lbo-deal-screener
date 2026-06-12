// Number formatting helpers (docs/BUILD_SPEC.md sections 4 and 14).
// Currency auto-scales ($1.23tn / $456.7bn / $89.1m); null renders as an em dash.
// Per the currency contract: USD → $, GBP → £, EUR → €; any other ISO code is
// used as a prefix ("SEK 1.2bn"). No code (null/undefined) means USD.

const NOT_AVAILABLE = "—"; // —

function isMissing(value: number | null | undefined): value is null | undefined {
  return value === null || value === undefined || !Number.isFinite(value);
}

function currencyPrefix(currency: string | null | undefined): string {
  switch (currency ?? "USD") {
    case "USD":
      return "$";
    case "GBP":
      return "£";
    case "EUR":
      return "€";
    default:
      return `${currency} `;
  }
}

export function fmtCurrency(
  value: number | null | undefined,
  currency?: string | null,
): string {
  if (isMissing(value)) return NOT_AVAILABLE;
  const prefix = currencyPrefix(currency);
  const sign = value < 0 ? "-" : "";
  const abs = Math.abs(value);
  if (abs >= 1e12) return `${sign}${prefix}${(abs / 1e12).toFixed(2)}tn`;
  if (abs >= 1e9) return `${sign}${prefix}${(abs / 1e9).toFixed(1)}bn`;
  if (abs >= 1e6) return `${sign}${prefix}${(abs / 1e6).toFixed(1)}m`;
  return `${sign}${prefix}${abs.toLocaleString("en-US", {
    minimumFractionDigits: abs < 1000 ? 2 : 0,
    maximumFractionDigits: 2,
  })}`;
}

/**
 * Per-share figures (EPS): exact two decimals in the reporting currency,
 * never magnitude-scaled ("$6.13", "-$0.42", "SEK 12.40").
 */
export function fmtPerShare(
  value: number | null | undefined,
  currency?: string | null,
): string {
  if (isMissing(value)) return NOT_AVAILABLE;
  const sign = value < 0 ? "-" : "";
  return `${sign}${currencyPrefix(currency)}${Math.abs(value).toFixed(2)}`;
}

/**
 * Share counts in millions with an "m" suffix ("15,408m"), never
 * currency-scaled (BUILD_SPEC section 19.8 statements rendering).
 */
export function fmtShareCount(value: number | null | undefined): string {
  if (isMissing(value)) return NOT_AVAILABLE;
  const millions = value / 1e6;
  const digits = Math.abs(millions) < 10 ? 1 : 0;
  return `${millions.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}m`;
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

/** Day-count metrics (DSO, DSI, DPO, CCC): "43.8 days"; null renders as —. */
export function fmtDays(value: number | null | undefined): string {
  if (isMissing(value)) return NOT_AVAILABLE;
  return `${value.toFixed(1)} days`;
}

/**
 * Date-only rendering for API date strings (BUILD_SPEC section 19.7
 * presentation pass): ISO timestamps ("2026-06-12T09:14:03Z") truncate to
 * YYYY-MM-DD; plain dates pass through; anything unrecognised is returned
 * as-is rather than mangled. Null renders as —.
 */
export function fmtDate(value: string | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return NOT_AVAILABLE;
  }
  const match = /^(\d{4}-\d{2}-\d{2})/.exec(value);
  return match !== null ? match[1] : value;
}
