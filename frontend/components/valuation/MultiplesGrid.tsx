import StatCard from "@/components/ui/StatCard";
import { fmtCurrency, fmtMultiple, fmtNumber, fmtPercent } from "@/lib/format";
import type { TracedValue } from "@/lib/types";

function fmtTraced(tv: TracedValue): string {
  switch (tv.unit) {
    case "percent":
      return fmtPercent(tv.value);
    case "multiple":
      return fmtMultiple(tv.value);
    case "currency":
    case "per_share":
      return fmtCurrency(tv.value);
    case "ratio":
      return fmtNumber(tv.value, { digits: 2 });
  }
}

interface MultiplesGridProps {
  multiples: TracedValue[];
  className?: string;
}

/** Current valuation multiples as StatCards with the formula in the sub line. */
export default function MultiplesGrid({
  multiples,
  className = "",
}: MultiplesGridProps) {
  return (
    <div
      className={`grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 ${className}`}
    >
      {multiples.map((tv) => (
        <StatCard
          key={tv.key}
          label={tv.label}
          value={fmtTraced(tv)}
          sub={`${tv.formula} · ${tv.period}`}
        />
      ))}
    </div>
  );
}
