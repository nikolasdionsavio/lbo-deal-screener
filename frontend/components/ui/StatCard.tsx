import type { ReactNode } from "react";
import Card from "./Card";

interface StatCardProps {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  className?: string;
}

export default function StatCard({
  label,
  value,
  sub,
  className = "",
}: StatCardProps) {
  return (
    <Card className={className}>
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className="mt-1 text-2xl font-semibold tabular-nums text-ink">
        {value}
      </div>
      {sub !== undefined && sub !== null && (
        <div className="mt-1 text-xs text-slate-500">{sub}</div>
      )}
    </Card>
  );
}
