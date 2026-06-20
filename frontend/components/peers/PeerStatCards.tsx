// Peer-group quartile figures (BUILD_SPEC section 19.5): a key-figures ledger
// of the peer median per metric, with the Q1-Q3 interquartile range below each.
// Stats are computed by the backend over valued peers only (target excluded);
// metrics without stats are hidden.

import Card from "@/components/ui/Card";
import { FigureRow } from "@/components/ui/figure";
import { fmtMultiple, fmtPercent } from "@/lib/format";
import type { PeerStats } from "@/lib/types";

type MetricFormat = "multiple" | "percent";

const METRICS: { key: string; label: string; format: MetricFormat }[] = [
  { key: "ev_ebitda", label: "EV / EBITDA (median)", format: "multiple" },
  { key: "ev_revenue", label: "EV / Revenue (median)", format: "multiple" },
  { key: "pe", label: "P / E (median)", format: "multiple" },
  {
    key: "ebitda_margin",
    label: "EBITDA margin (median)",
    format: "percent",
  },
];

function fmt(value: number | null, format: MetricFormat): string {
  return format === "multiple" ? fmtMultiple(value) : fmtPercent(value);
}

interface PeerStatCardsProps {
  stats: Record<string, PeerStats>;
  className?: string;
}

export default function PeerStatCards({
  stats,
  className = "",
}: PeerStatCardsProps) {
  const rows = METRICS.flatMap((metric) => {
    const s = stats[metric.key];
    return s !== undefined ? [{ ...metric, stats: s }] : [];
  });

  if (rows.length === 0) return null;
  const mid = Math.ceil(rows.length / 2);
  const columns = [rows.slice(0, mid), rows.slice(mid)];

  return (
    <Card className={className}>
      <div className="grid gap-x-10 sm:grid-cols-2">
        {columns.map((column, i) => (
          <div key={i}>
            {column.map((row) => (
              <FigureRow
                key={row.key}
                label={row.label}
                value={fmt(row.stats.median, row.format)}
                sub={`Q1 ${fmt(row.stats.q1, row.format)} – Q3 ${fmt(
                  row.stats.q3,
                  row.format,
                )}`}
              />
            ))}
          </div>
        ))}
      </div>
    </Card>
  );
}
