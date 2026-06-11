// Headline list for the company news page (BUILD_SPEC section 19.6).
// Each item: title as an external link, source, absolute date plus a
// relative "3h ago" when published within the last 48 hours, and the
// summary clamped to two lines when present.

import type { NewsItem } from "@/lib/types";

const RELATIVE_WINDOW_MS = 48 * 60 * 60 * 1000;

interface PublishedDates {
  absolute: string;
  relative: string | null;
}

/** "Jun 11, 2026" plus "3h ago" when published within the last 48 hours. */
export function formatPublished(iso: string): PublishedDates {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return { absolute: iso, relative: null };
  }
  const absolute = date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  const ageMs = Date.now() - date.getTime();
  if (ageMs < 0 || ageMs >= RELATIVE_WINDOW_MS) {
    return { absolute, relative: null };
  }
  const minutes = Math.floor(ageMs / 60_000);
  if (minutes < 1) return { absolute, relative: "just now" };
  if (minutes < 60) return { absolute, relative: `${minutes}m ago` };
  return { absolute, relative: `${Math.floor(minutes / 60)}h ago` };
}

function NewsRow({ item }: { item: NewsItem }) {
  const { absolute, relative } = formatPublished(item.published_at);
  return (
    <li className="py-3 first:pt-0 last:pb-0">
      <a
        href={item.url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-sm font-medium text-brand underline decoration-slate-300 underline-offset-2 hover:decoration-brand"
      >
        {item.title}
      </a>
      <div className="mt-1 flex flex-wrap items-center gap-x-2 text-xs text-slate-500">
        <span>{item.source}</span>
        <span className="text-slate-300">·</span>
        <span className="tabular-nums">{absolute}</span>
        {relative !== null && (
          <>
            <span className="text-slate-300">·</span>
            <span>{relative}</span>
          </>
        )}
      </div>
      {item.summary !== null && item.summary !== "" && (
        <p className="mt-1 line-clamp-2 text-sm leading-relaxed text-slate-600">
          {item.summary}
        </p>
      )}
    </li>
  );
}

export default function NewsList({ items }: { items: NewsItem[] }) {
  return (
    <ul className="divide-y divide-slate-100">
      {items.map((item, i) => (
        <NewsRow key={`${item.url}-${i}`} item={item} />
      ))}
    </ul>
  );
}
