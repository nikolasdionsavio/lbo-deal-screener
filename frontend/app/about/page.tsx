// About (route /about): presentational only. ALL content is read from
// lib/about.ts — edit that file to change this page. A warm, first-person
// profile: photo, greeting, bio prose, color-coded highlights, and a
// "Find me" list of links.

import type { Metadata } from "next";
import Image from "next/image";
import Disclaimer from "@/components/ui/Disclaimer";
import {
  about,
  type AboutLinkKind,
  type HighlightColor,
  type HighlightIcon,
} from "@/lib/about";

export const metadata: Metadata = {
  title: "About · Investment Intelligence",
  description: "About Nikolas Dion Savio and the project.",
};

// Per-highlight color, used for the icon tile. Soft tints in both themes so
// the page picks up several deliberate accents (the one place we go colorful).
const HIGHLIGHT_TINT: Record<HighlightColor, string> = {
  blue: "bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300",
  indigo:
    "bg-indigo-100 text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300",
  teal: "bg-teal-100 text-teal-700 dark:bg-teal-500/15 dark:text-teal-300",
  amber: "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300",
  emerald:
    "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300",
};

function iconAttrs(size = 18) {
  return {
    width: size,
    height: size,
    viewBox: "0 0 20 20",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.6,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true as const,
  };
}

function HighlightGlyph({ icon }: { icon: HighlightIcon }) {
  if (icon === "school")
    return (
      <svg {...iconAttrs()}>
        <path d="M10 3 2.5 6.5 10 10l7.5-3.5L10 3Z" />
        <path d="M5.5 8v4.2c0 1 2 1.8 4.5 1.8s4.5-.8 4.5-1.8V8" />
        <path d="M17.5 6.5v4" />
      </svg>
    );
  if (icon === "markets")
    return (
      <svg {...iconAttrs()}>
        <path d="M3 17h14" />
        <path d="M5 17V8m4 9V5m4 12v-6m4 6V9" />
      </svg>
    );
  if (icon === "research")
    return (
      <svg {...iconAttrs()}>
        <path d="M8 2.5h4M8.5 2.5v4.2L4.7 14a1.5 1.5 0 0 0 1.3 2.3h8a1.5 1.5 0 0 0 1.3-2.3l-3.8-7.3V2.5" />
        <path d="M6.6 11.5h6.8" />
      </svg>
    );
  if (icon === "racing")
    return (
      <svg {...iconAttrs()}>
        <path d="M4.5 17V3" />
        <path d="M4.5 4.2c3-1.4 5.5 1.4 8.5 0V11c-3 1.4-5.5-1.4-8.5 0" />
      </svg>
    );
  // trading
  return (
    <svg {...iconAttrs()}>
      <path d="M3 13.5 8 9l3 2.5 6-6.5" />
      <path d="M13 5h4v4" />
    </svg>
  );
}

function linkIconAttrs() {
  return {
    width: 14,
    height: 14,
    viewBox: "0 0 16 16",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.5,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true as const,
  };
}

function LinkIcon({ kind }: { kind: AboutLinkKind }) {
  if (kind === "linkedin")
    return (
      <svg {...linkIconAttrs()}>
        <rect x="1.75" y="1.75" width="12.5" height="12.5" rx="2" />
        <path d="M4.5 6.5v5M4.5 4.25v.01" />
        <path d="M7.5 11.5v-3a1.75 1.75 0 0 1 3.5 0v3" />
        <path d="M7.5 6.5v5" />
      </svg>
    );
  if (kind === "web")
    return (
      <svg {...linkIconAttrs()}>
        <circle cx="8" cy="8" r="6.25" />
        <path d="M1.75 8h12.5" />
        <path d="M8 1.75c1.75 1.7 2.75 3.9 2.75 6.25S9.75 12.55 8 14.25C6.25 12.55 5.25 10.35 5.25 8S6.25 3.45 8 1.75Z" />
      </svg>
    );
  if (kind === "email")
    return (
      <svg {...linkIconAttrs()}>
        <rect x="1.75" y="3.5" width="12.5" height="9" rx="1.5" />
        <path d="m2.5 4.5 5.5 4 5.5-4" />
      </svg>
    );
  return (
    <svg {...linkIconAttrs()}>
      <path d="M6.5 9.5a2.5 2.5 0 0 0 3.7.2l2-2a2.5 2.5 0 0 0-3.5-3.5l-1 1" />
      <path d="M9.5 6.5a2.5 2.5 0 0 0-3.7-.2l-2 2a2.5 2.5 0 0 0 3.5 3.5l1-1" />
    </svg>
  );
}

export default function AboutPage() {
  const { name, role, tagline, photo, greeting, bio, highlights, links } =
    about;

  return (
    <div className="px-4 py-8 sm:px-8">
      <div className="mx-auto w-full max-w-3xl">
        {/* Header: photo + greeting, on a soft multi-tone wash */}
        <section className="overflow-hidden rounded-2xl border border-line bg-surface shadow-card">
          <div className="relative bg-gradient-to-br from-brand-soft via-surface to-teal-500/10 px-6 py-8 sm:px-8 sm:py-10">
            <div className="flex flex-col items-center gap-6 text-center sm:flex-row sm:items-center sm:text-left">
              <div className="shrink-0">
                <div className="rounded-2xl bg-gradient-to-br from-brand to-accent p-[3px] shadow-card-hover">
                  <Image
                    src={photo}
                    alt={name}
                    width={760}
                    height={950}
                    priority
                    className="h-32 w-32 rounded-[14px] object-cover object-top sm:h-40 sm:w-40"
                  />
                </div>
              </div>
              <div className="min-w-0">
                <span className="inline-flex items-center gap-1.5 rounded-full border border-line-strong bg-surface px-3 py-1 text-xs font-medium text-ink-secondary">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  {greeting}
                </span>
                <h1 className="mt-3 font-display text-2xl font-semibold leading-tight text-ink sm:text-[1.75rem]">
                  {name}
                </h1>
                <p className="mt-1 text-sm font-medium text-brand-text">
                  {role}
                </p>
                <p className="mt-0.5 text-sm text-ink-muted">{tagline}</p>
              </div>
            </div>
          </div>

          {/* Bio prose */}
          <div className="space-y-4 px-6 py-7 sm:px-8">
            {bio.map((paragraph, index) => (
              <p
                key={index}
                className="max-w-prose text-[15px] leading-relaxed text-ink-secondary"
              >
                {paragraph}
              </p>
            ))}
          </div>
        </section>

        {/* Color-coded highlights */}
        <h2 className="mt-8 px-1 text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
          A few highlights
        </h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {highlights.map((item) => (
            <div
              key={item.title}
              className="flex items-start gap-3.5 rounded-xl border border-line bg-surface p-4 shadow-card transition-shadow duration-150 hover:shadow-card-hover"
            >
              <span
                className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${HIGHLIGHT_TINT[item.color]}`}
              >
                <HighlightGlyph icon={item.icon} />
              </span>
              <div className="min-w-0">
                <p className="text-sm font-semibold leading-snug text-ink">
                  {item.title}
                </p>
                <p className="mt-1 text-[13px] leading-snug text-ink-muted">
                  {item.detail}
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* Find me */}
        <h2 className="mt-8 px-1 text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
          Find me
        </h2>
        <ul className="mt-3 flex flex-wrap gap-2">
          {links.map((link) => (
            <li key={link.label}>
              <a
                href={link.href}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 rounded-full border border-line-strong bg-surface px-3.5 py-1.5 text-sm text-ink-secondary shadow-card transition-all duration-150 hover:-translate-y-px hover:text-ink hover:shadow-card-hover"
              >
                <LinkIcon kind={link.kind} />
                {link.label}
              </a>
            </li>
          ))}
        </ul>

        <Disclaimer />
      </div>
    </div>
  );
}
