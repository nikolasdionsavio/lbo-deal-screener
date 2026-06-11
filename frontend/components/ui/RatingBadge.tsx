import type { Rating } from "@/lib/types";

const STYLES: Record<Rating, string> = {
  Attractive: "border-transparent bg-accent-soft text-positive-text",
  Watchlist: "border-transparent bg-warn-soft text-warn-text",
  Pass: "border-transparent bg-negative-soft text-negative-text",
};

interface RatingBadgeProps {
  rating: Rating;
  className?: string;
}

export default function RatingBadge({
  rating,
  className = "",
}: RatingBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${STYLES[rating]} ${className}`}
    >
      {rating}
    </span>
  );
}
