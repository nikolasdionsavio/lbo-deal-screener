interface LoadingStateProps {
  /** Number of skeleton lines to render. */
  lines?: number;
  className?: string;
}

export default function LoadingState({
  lines = 4,
  className = "",
}: LoadingStateProps) {
  return (
    <div
      className={`space-y-3 ${className}`}
      role="status"
      aria-label="Loading"
    >
      {Array.from({ length: lines }, (_, i) => (
        <div
          key={i}
          className="skeleton h-4"
          style={{ width: `${100 - (i % 4) * 12}%` }}
        />
      ))}
    </div>
  );
}
