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
      className={`rounded-lg border border-transparent bg-negative-soft p-5 ${className}`}
      role="alert"
    >
      <p className="text-sm font-medium text-negative-text">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="btn btn-primary mt-3 px-3 py-1.5 text-sm"
        >
          Retry
        </button>
      )}
    </div>
  );
}
