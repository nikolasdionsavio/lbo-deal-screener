import type { Rating } from "@/lib/types";

const STYLES: Record<Rating, string> = {
  Attractive: "border-accent/30 bg-accent/10 text-accent",
  Watchlist: "border-warn/30 bg-warn/10 text-warn",
  Pass: "border-negative/30 bg-negative/10 text-negative",
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
