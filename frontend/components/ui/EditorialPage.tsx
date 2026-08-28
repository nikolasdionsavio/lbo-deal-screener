// Shared layout for the public reading pages: methodology, how to use,
// changelog, what's new.
//
// They were each a centred max-w-3xl column, which DESIGN.md rules out in as
// many words ("Do not centre everything. No narrow column floating in a wide
// screen"). At 1440px that left roughly 340px of dead margin on either side of
// a page whose whole argument is that it is dense and considered.
//
// The replacement keeps the reading measure, which was the only good reason
// for the narrow column, and spends the reclaimed width on a title column that
// stays with you down a long document. Prose still wraps at ~68ch; the page is
// no longer symmetrical about its own centre.

"use client";

import type { ReactNode } from "react";
import Container from "@/components/ui/Container";
import { Reveal, SplitLines } from "@/lib/motion";

export default function EditorialPage({
  title,
  kicker,
  intro,
  aside,
  children,
}: {
  title: string;
  /** Running head. Names the section of the site, not the page. */
  kicker?: string;
  intro?: ReactNode;
  /** Optional extra under the title: source note, contents, last-updated. */
  aside?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="py-14 lg:py-20">
      <Container>
        <div className="grid grid-cols-12 gap-x-6 gap-y-8">
          <header className="col-span-12 lg:col-span-4">
            {/* Sticky only where there is room for it, and only on the pages
                that are long enough to lose your place in. */}
            <div className="lg:sticky lg:top-24">
              {kicker !== undefined && (
                <Reveal variant="rule" className="mb-6">
                  <p className="tape">{kicker}</p>
                </Reveal>
              )}
              <h1 className="ed-title text-ink">
                <SplitLines text={title} lead={60} step={80} />
              </h1>
              {intro !== undefined && intro !== null && (
                <Reveal variant="rise" lead={260}>
                  <p className="ed-intro mt-6 max-w-[38ch]">{intro}</p>
                </Reveal>
              )}
              {aside !== undefined && aside !== null && (
                <Reveal variant="rise" lead={340}>
                  <div className="mt-6">{aside}</div>
                </Reveal>
              )}
            </div>
          </header>

          <div className="col-span-12 lg:col-span-7 lg:col-start-6">
            {children}
          </div>
        </div>
      </Container>
    </div>
  );
}
