// Changelog (route /changelog): a modest, dated log of what actually changed.
// Reads the same real RELEASES history the app already tracks. Newest first.

import type { Metadata } from "next";
import Container from "@/components/ui/Container";
import Disclaimer from "@/components/ui/Disclaimer";
import { RELEASES } from "@/lib/version";

export const metadata: Metadata = {
  title: "Changelog",
  description:
    "What has changed in Investment Intelligence, most recent first.",
};

export default function ChangelogPage() {
  return (
    <div className="py-14 lg:py-20">
      <Container>
        <h1 className="ed-title text-ink">Changelog</h1>
        <p className="ed-intro mt-5">
          What has changed, most recent first. Data-mapping and methodology
          changes are noted here so a figure that moves has a reason on record.
        </p>

        <div className="mt-12">
          {RELEASES.map((release) => (
            <section
              key={release.version}
              className="border-t border-line py-7 sm:grid sm:grid-cols-[11rem_1fr] sm:gap-10"
            >
              <div className="mb-2 sm:mb-0">
                <div className="font-mono text-sm text-ink">{release.date}</div>
                <div className="mt-0.5 font-mono text-xs text-ink-muted">
                  v{release.version}
                </div>
              </div>
              <div>
                <h2 className="ed-sub">{release.title}</h2>
                <ul className="mt-2 space-y-1.5">
                  {release.changes.map((change, i) => (
                    <li
                      key={i}
                      className="max-w-[68ch] text-[0.9375rem] leading-relaxed text-ink-secondary"
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
      </Container>
    </div>
  );
}
