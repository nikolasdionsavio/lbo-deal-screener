// About (route /about): presentational only. ALL content is read from
// lib/about.ts — edit that file to change this page. Renders a monogram
// avatar (no photo), name, role, bio prose, and a "Find me" list of pill
// links. Links with href "#" are placeholders and render de-emphasized.

import type { Metadata } from "next";
import Card from "@/components/ui/Card";
import Disclaimer from "@/components/ui/Disclaimer";
import { about, type AboutLinkKind } from "@/lib/about";

export const metadata: Metadata = {
  title: "About · Investment Intelligence",
  description: "About the author and the project.",
};

// Initials for the monogram avatar, derived from the name (first letter of
// up to three words). Falls back to "II" if the name is empty.
function initials(name: string): string {
  const letters = name
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 3)
    .map((word) => word[0]?.toUpperCase() ?? "")
    .join("");
  return letters || "II";
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

function LinkedInIcon() {
  return (
    <svg {...linkIconAttrs()}>
      <rect x="1.75" y="1.75" width="12.5" height="12.5" rx="2" />
      <path d="M4.5 6.5v5M4.5 4.25v.01" />
      <path d="M7.5 11.5v-3a1.75 1.75 0 0 1 3.5 0v3" />
      <path d="M7.5 6.5v5" />
    </svg>
  );
}

function WebIcon() {
  return (
    <svg {...linkIconAttrs()}>
      <circle cx="8" cy="8" r="6.25" />
      <path d="M1.75 8h12.5" />
      <path d="M8 1.75c1.75 1.7 2.75 3.9 2.75 6.25S9.75 12.55 8 14.25C6.25 12.55 5.25 10.35 5.25 8S6.25 3.45 8 1.75Z" />
    </svg>
  );
}

function EmailIcon() {
  return (
    <svg {...linkIconAttrs()}>
      <rect x="1.75" y="3.5" width="12.5" height="9" rx="1.5" />
      <path d="m2.5 4.5 5.5 4 5.5-4" />
    </svg>
  );
}

function GenericLinkIcon() {
  return (
    <svg {...linkIconAttrs()}>
      <path d="M6.5 9.5a2.5 2.5 0 0 0 3.7.2l2-2a2.5 2.5 0 0 0-3.5-3.5l-1 1" />
      <path d="M9.5 6.5a2.5 2.5 0 0 0-3.7-.2l-2 2a2.5 2.5 0 0 0 3.5 3.5l1-1" />
    </svg>
  );
}

function LinkIcon({ kind }: { kind: AboutLinkKind }) {
  if (kind === "linkedin") return <LinkedInIcon />;
  if (kind === "web") return <WebIcon />;
  if (kind === "email") return <EmailIcon />;
  return <GenericLinkIcon />;
}

export default function AboutPage() {
  const { name, role, bio, links } = about;

  return (
    <div className="flex min-h-[calc(100vh-3rem)] flex-col px-4 py-8 sm:px-8">
      <div className="mx-auto w-full max-w-2xl">
        <Card>
          {/* Header: monogram avatar + name + role */}
          <div className="flex items-center gap-4">
            <span
              className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-brand-soft text-base font-semibold tracking-wide text-brand-text"
              aria-hidden="true"
            >
              {initials(name)}
            </span>
            <div className="min-w-0">
              <h1 className="font-display text-[1.375rem] font-semibold leading-snug text-ink">
                {name}
              </h1>
              <p className="mt-0.5 text-sm text-ink-muted">{role}</p>
            </div>
          </div>

          {/* Bio prose */}
          <div className="mt-6 max-w-prose space-y-3">
            {bio.map((paragraph, index) => (
              <p
                key={index}
                className="text-sm leading-relaxed text-ink-secondary"
              >
                {paragraph}
              </p>
            ))}
          </div>

          {/* Find me */}
          <div className="divider-dashed my-6" />
          <h2 className="text-[11px] font-medium uppercase tracking-wide text-ink-muted">
            Find me
          </h2>
          <ul className="mt-3 flex flex-wrap gap-2">
            {links.map((link) => {
              const isPlaceholder = link.href === "#";
              return (
                <li key={link.label}>
                  <a
                    href={link.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-disabled={isPlaceholder ? true : undefined}
                    title={
                      isPlaceholder ? `${link.label} — link not set` : undefined
                    }
                    className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm transition-colors duration-150 ${
                      isPlaceholder
                        ? "pointer-events-none border-line text-ink-muted opacity-50"
                        : "border-line-strong text-ink-secondary hover:bg-surface-sunken hover:text-ink"
                    }`}
                  >
                    <LinkIcon kind={link.kind} />
                    {link.label}
                  </a>
                </li>
              );
            })}
          </ul>
        </Card>
      </div>
      <div className="mx-auto w-full max-w-2xl">
        <Disclaimer />
      </div>
    </div>
  );
}
