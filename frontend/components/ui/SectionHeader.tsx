import type { ReactNode } from "react";

interface SectionHeaderProps {
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
  className?: string;
}

export default function SectionHeader({
  title,
  subtitle,
  actions,
  className = "",
}: SectionHeaderProps) {
  return (
    <div className={`mb-4 flex items-end justify-between gap-4 ${className}`}>
      <div>
        <h2 className="text-lg font-semibold text-ink">{title}</h2>
        {subtitle !== undefined && subtitle !== null && (
          <p className="mt-0.5 text-sm text-slate-500">{subtitle}</p>
        )}
      </div>
      {actions !== undefined && actions !== null && (
        <div className="shrink-0">{actions}</div>
      )}
    </div>
  );
}
