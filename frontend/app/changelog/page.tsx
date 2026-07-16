// Changelog (route /changelog): a modest, dated log of what actually changed.
// Reads the same real RELEASES history the app already tracks. Newest first.

import type { Metadata } from "next";
import Disclaimer from "@/components/ui/Disclaimer";
import { RELEASES } from "@/lib/version";

export const metadata: Metadata = {
  title: "Changelog · Investment Intelligence",
  description: "What has changed in Investment Intelligence, most recent first.",
};

export default function ChangelogPage() {
  return (
    <div className="px-4 py-10 sm:px-8">
      <div className="mx-auto w-full max-w-3xl">
        <h1 className="text-[2rem] font-semibold leading-tight text-ink">
          Changelog
        </h1>
        <p className="mt-2 max-w-prose text-[0.95rem] text-ink-secondary">
          What has changed, most recent first. Data-mapping and methodology
          changes are noted here so a figure that moves has a reason on record.
        </p>

        <div className="mt-8">
          {RELEASES.map((release) => (
            <section
              key={release.version}
              className="border-t border-line py-6 sm:grid sm:grid-cols-[9rem_1fr] sm:gap-6"
            >
              <div className="mb-2 sm:mb-0">
                <div className="font-mono text-sm text-ink">{release.date}</div>
                <div className="mt-0.5 font-mono text-xs text-ink-muted">
                  v{release.version}
                </div>
              </div>
              <div>
                <h2 className="text-[0.95rem] font-semibold text-ink">
                  {release.title}
                </h2>
                <ul className="mt-2 space-y-1.5">
                  {release.changes.map((change, i) => (
                    <li
                      key={i}
                      className="text-sm leading-snug text-ink-secondary"
                    >
                      {change}
                    </li>
                  ))}
                </ul>
              </div>
            </section>
          ))}
        </div>

        <Disclaimer />
      </div>
    </div>
  );
}
