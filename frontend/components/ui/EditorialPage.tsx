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

import type { ReactNode } from "react";
import Container from "@/components/ui/Container";

export default function EditorialPage({
  title,
  intro,
  aside,
  children,
}: {
  title: string;
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
            <div className="lg:sticky lg:top-8">
              <h1 className="ed-title text-ink">{title}</h1>
              {intro !== undefined && intro !== null && (
                <p className="ed-intro mt-5 max-w-[38ch]">{intro}</p>
              )}
              {aside !== undefined && aside !== null && (
                <div className="mt-6">{aside}</div>
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
