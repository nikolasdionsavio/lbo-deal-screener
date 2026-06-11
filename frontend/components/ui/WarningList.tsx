interface WarningListProps {
  warnings: string[];
  className?: string;
}

export default function WarningList({
  warnings,
  className = "",
}: WarningListProps) {
  if (warnings.length === 0) return null;
  return (
    <ul
      className={`space-y-1 rounded-lg border border-warn/30 bg-warn/10 px-4 py-3 text-sm text-warn ${className}`}
    >
      {warnings.map((warning, i) => (
        <li key={i}>{warning}</li>
      ))}
    </ul>
  );
}
