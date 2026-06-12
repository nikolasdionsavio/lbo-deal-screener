// Story cards for the company news page (BUILD_SPEC section 19.8): each
// item is a distinct surface card with a hairline border that raises on
// hover. Headline as a 600-weight ink link, a prominent source + relative
// time meta row, and the summary clamped to two lines when present.

import type { NewsItem } from "@/lib/types";

interface PublishedDates {
  /** "3h ago" graded out to days/weeks/months; absolute date as fallback. */
  relative: string;
  /** Full local date-time for the title attribute. */
  absolute: string;
}

/** Relative age for the meta row, with the exact timestamp for hover. */
export function formatPublished(iso: string): PublishedDates {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return { relative: iso, absolute: iso };
  }
  const absolute = date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
  const ageMs = Date.now() - date.getTime();
  if (ageMs < 0) {
    // Clock skew or a provider future-dating an item: show the date.
    return { relative: absolute, absolute };
  }
  const minutes = Math.floor(ageMs / 60_000);
  if (minutes < 1) return { relative: "just now", absolute };
  if (minutes < 60) return { relative: `${minutes}m ago`, absolute };
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return { relative: `${hours}h ago`, absolute };
  const days = Math.floor(hours / 24);
  if (days < 14) return { relative: `${days}d ago`, absolute };
  if (days < 61) return { relative: `${Math.floor(days / 7)}w ago`, absolute };
  return { relative: `${Math.floor(days / 30)}mo ago`, absolute };
}

function StoryCard({ item }: { item: NewsItem }) {
  const { relative, absolute } = formatPublished(item.published_at);
  return (
    <li>
      <article className="rounded-lg border border-line bg-surface p-4 shadow-card transition duration-150 hover:-translate-y-px hover:border-line-strong hover:shadow-card-hover sm:p-5">
        <a
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm font-semibold leading-snug text-ink underline-offset-2 hover:underline"
        >
          {item.title}
        </a>
        <div className="mt-1.5 flex flex-wrap items-center gap-x-2 text-xs">
          <span className="font-medium text-ink-secondary">{item.source}</span>
          <span aria-hidden="true" className="text-ink-muted">
            ·
          </span>
          <time
            dateTime={item.published_at}
            title={absolute}
            className="tabular-nums text-ink-muted"
          >
            {relative}
          </time>
        </div>
        {item.summary !== null && item.summary !== "" && (
          <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-ink-secondary">
            {item.summary}
          </p>
        )}
      </article>
    </li>
  );
}

export default function NewsList({ items }: { items: NewsItem[] }) {
  return (
    <ul className="space-y-4">
      {items.map((item, i) => (
        <StoryCard key={`${item.url}-${i}`} item={item} />
      ))}
    </ul>
  );
}
