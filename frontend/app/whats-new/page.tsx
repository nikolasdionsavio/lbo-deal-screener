// What's New (route /whats-new): the platform changelog, newest release first.
// Static content, server-rendered from lib/version.ts so the sidebar version
// marker and this page never drift apart.

import type { Metadata } from "next";
import Card from "@/components/ui/Card";
import Disclaimer from "@/components/ui/Disclaimer";
import SectionHeader from "@/components/ui/SectionHeader";
import { APP_VERSION, RELEASES } from "@/lib/version";

export const metadata: Metadata = {
  title: "What's New",
  description:
    "Release notes for Investment Intelligence: the latest features and improvements to the deal-screening platform.",
};

export default function WhatsNewPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-8">
      <SectionHeader
        variant="page"
        as="h1"
        title="What's New"
        subtitle={`Release notes for the platform. Currently on v${APP_VERSION}.`}
      />

      <div className="mt-6 space-y-4">
        {RELEASES.map((release, i) => (
          <Card key={release.version}>
            <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
              <div className="flex items-baseline gap-2.5">
                <h2 className="font-display text-lg font-semibold text-ink">
                  {release.title}
                </h2>
                <span className="rounded-full border border-line-strong px-2 py-0.5 text-xs font-medium tabular-nums text-ink-secondary">
                  v{release.version}
                </span>
                {i === 0 && (
                  <span className="rounded-full bg-accent-soft px-2 py-0.5 text-xs font-medium text-positive-text">
                    Latest
                  </span>
                )}
              </div>
              <span className="text-xs text-ink-muted">{release.date}</span>
            </div>
            <ul className="mt-3 space-y-2">
              {release.changes.map((change, j) => (
                <li key={j} className="flex gap-2.5 text-sm text-ink-secondary">
                  <span
                    aria-hidden
                    className="mt-[0.45rem] h-1.5 w-1.5 shrink-0 rounded-circle bg-brand"
                  />
                  <span>{change}</span>
                </li>
              ))}
            </ul>
          </Card>
        ))}
      </div>

      <Disclaimer />
    </div>
  );
}
