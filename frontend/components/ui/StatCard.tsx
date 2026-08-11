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
      <div className="text-[13px] font-medium text-ink-secondary">{label}</div>
      <div className="figure-gilt mt-1.5 text-xl font-semibold tracking-tight">
        {value}
      </div>
      {sub !== undefined && sub !== null && (
        <div className="mt-1 text-xs leading-snug text-ink-muted">{sub}</div>
      )}
    </Card>
  );
}
