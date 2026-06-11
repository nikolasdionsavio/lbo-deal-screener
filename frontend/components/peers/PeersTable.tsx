// Peer comparables table (BUILD_SPEC section 19.5): one row per company with
// the target pinned to the top and highlighted. Monetary columns use each
// row's own reporting currency; null values render as an em dash.

import DataTable, { type Column } from "@/components/ui/DataTable";
import {
  fmtCurrency,
  fmtMultiple,
  fmtPercent,
} from "@/lib/format";
import type { PeerRow } from "@/lib/types";

interface TableRow {
  peer: PeerRow;
  isTarget: boolean;
}

const NOT_AVAILABLE = (
  <span title="Not available" className="text-slate-400">
    —
  </span>
);

function multiple(value: number | null) {
  return value === null ? NOT_AVAILABLE : fmtMultiple(value);
}

function percent(value: number | null, signed = false) {
  return value === null ? NOT_AVAILABLE : fmtPercent(value, { signed });
}

function money(value: number | null, currency: string | null) {
  return value === null ? NOT_AVAILABLE : fmtCurrency(value, currency);
}

const COLUMNS: Column<TableRow>[] = [
  {
    key: "company",
    header: "Company",
    render: ({ peer, isTarget }) => (
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium text-ink">{peer.name}</span>
          <span className="text-xs tabular-nums text-slate-500">
            {peer.ticker}
          </span>
          {isTarget && (
            <span className="inline-flex items-center rounded-full border border-accent/30 bg-accent/10 px-2 py-0.5 text-[11px] font-medium text-accent">
              Target
            </span>
          )}
        </div>
        {peer.warnings.length > 0 && (
          <div className="mt-1 flex flex-wrap gap-1">
            {peer.warnings.map((warning, i) => (
              <span
                key={i}
                className="inline-flex items-center rounded-full border border-warn/30 bg-warn/10 px-2 py-0.5 text-[11px] text-warn"
              >
                {warning}
              </span>
            ))}
          </div>
        )}
      </div>
    ),
  },
  {
    key: "market_cap",
    header: "Market cap",
    numeric: true,
    render: ({ peer }) => money(peer.market_cap, peer.currency),
  },
  {
    key: "enterprise_value",
    header: "EV",
    numeric: true,
    render: ({ peer }) => money(peer.enterprise_value, peer.currency),
  },
  {
    key: "ev_ebitda",
    header: "EV / EBITDA",
    numeric: true,
    render: ({ peer }) => multiple(peer.ev_ebitda),
  },
  {
    key: "ev_revenue",
    header: "EV / Revenue",
    numeric: true,
    render: ({ peer }) => multiple(peer.ev_revenue),
  },
  {
    key: "pe",
    header: "P / E",
    numeric: true,
    render: ({ peer }) => multiple(peer.pe),
  },
  {
    key: "ebitda_margin",
    header: "EBITDA margin",
    numeric: true,
    render: ({ peer }) => percent(peer.ebitda_margin),
  },
  {
    key: "revenue_growth_yoy",
    header: "Rev. growth YoY",
    numeric: true,
    render: ({ peer }) => percent(peer.revenue_growth_yoy, true),
  },
];

interface PeersTableProps {
  target: PeerRow;
  peers: PeerRow[];
  className?: string;
}

export default function PeersTable({
  target,
  peers,
  className = "",
}: PeersTableProps) {
  const rows: TableRow[] = [
    { peer: target, isTarget: true },
    ...peers.map((peer) => ({ peer, isTarget: false })),
  ];

  return (
    <DataTable
      columns={COLUMNS}
      rows={rows}
      rowKey={({ peer, isTarget }) => `${isTarget ? "target-" : ""}${peer.ticker}`}
      rowClassName={({ isTarget }) => (isTarget ? "bg-accent/5" : "")}
      className={className}
    />
  );
}
