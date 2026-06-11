"use client";

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
  className?: string;
}

export default function ErrorState({
  message,
  onRetry,
  className = "",
}: ErrorStateProps) {
  return (
    <div
      className={`rounded-lg border border-negative/30 bg-negative/5 p-5 ${className}`}
      role="alert"
    >
      <p className="text-sm font-medium text-negative">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 rounded bg-brand px-3 py-1.5 text-sm font-medium text-white hover:bg-brand/90"
        >
          Retry
        </button>
      )}
    </div>
  );
}
