import Card from "@/components/ui/Card";
import { FigureRow } from "@/components/ui/figure";
import {
  fmtCurrency,
  fmtDays,
  fmtMultiple,
  fmtNumber,
  fmtPercent,
} from "@/lib/format";
import type { TracedValue } from "@/lib/types";

function fmtTraced(tv: TracedValue, currency: string | null): string {
  switch (tv.unit) {
    case "percent":
      return fmtPercent(tv.value);
    case "multiple":
      return fmtMultiple(tv.value);
    case "currency":
    case "per_share":
      return fmtCurrency(tv.value, currency);
    case "ratio":
      return fmtNumber(tv.value, { digits: 2 });
    case "days":
      return fmtDays(tv.value);
  }
}

interface MultiplesGridProps {
  multiples: TracedValue[];
  /** Reporting currency code for currency/per-share values; null means USD. */
  currency?: string | null;
  className?: string;
}

/** Current valuation multiples as a key-figures ledger: each row is the
 *  metric, its value, and the formula and period it was computed from. */
export default function MultiplesGrid({
  multiples,
  currency = null,
  className = "",
}: MultiplesGridProps) {
  if (multiples.length === 0) return null;
  const mid = Math.ceil(multiples.length / 2);
  const columns = [multiples.slice(0, mid), multiples.slice(mid)];

  return (
    <Card className={className}>
      <div className="grid gap-x-10 sm:grid-cols-2">
        {columns.map((column, i) => (
          <div key={i}>
            {column.map((tv) => (
              <FigureRow
                key={tv.key}
                label={tv.label}
                value={fmtTraced(tv, currency)}
                sub={`${tv.formula} · ${tv.period}`}
              />
            ))}
          </div>
        ))}
      </div>
    </Card>
  );
}
