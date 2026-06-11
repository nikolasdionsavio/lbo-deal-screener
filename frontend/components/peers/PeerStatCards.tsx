// Peer-group quartile stat cards (BUILD_SPEC section 19.5): one card per
// metric showing the peer median, with the Q1–Q3 interquartile range in the
// sub line. Stats are computed by the backend over valued peers only
// (target excluded); metrics without stats are hidden.

import StatCard from "@/components/ui/StatCard";
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
  const cards = METRICS.flatMap((metric) => {
    const s = stats[metric.key];
    return s !== undefined ? [{ ...metric, stats: s }] : [];
  });

  if (cards.length === 0) return null;

  return (
    <div className={`grid gap-4 sm:grid-cols-2 lg:grid-cols-4 ${className}`}>
      {cards.map((card) => (
        <StatCard
          key={card.key}
          label={card.label}
          value={fmt(card.stats.median, card.format)}
          sub={`Q1 ${fmt(card.stats.q1, card.format)} – Q3 ${fmt(
            card.stats.q3,
            card.format,
          )}`}
        />
      ))}
    </div>
  );
}
