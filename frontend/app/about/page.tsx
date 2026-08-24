// About (route /about): presentational only. Content is read from lib/about.ts.
// Short and spoken: a greeting, a few plain paragraphs, factual credentials,
// and text links. No gradient frame, no colored tiles, no status dot.

import type { Metadata } from "next";
import { SITE_URL } from "@/lib/seo";
import Image from "next/image";
import Link from "next/link";
import Disclaimer from "@/components/ui/Disclaimer";
import { about } from "@/lib/about";

export const metadata: Metadata = {
  title: "About Nikolas Dion Savio",
  description:
    "Nikolas Dion Savio is a Risk Management and Financial Engineering postgraduate at Imperial College Business School and the author of Investment Intelligence, a company research tool that shows the source or assumption behind every calculated figure.",
  alternates: { canonical: "/about" },
};

export default function AboutPage() {
  const { greeting, standfirst, photo, name, bio, credentials, links } = about;

  const profileSchema = {
    "@context": "https://schema.org",
    "@type": "ProfilePage",
    url: `${SITE_URL}/about`,
    name: `About ${about.fullName}`,
    mainEntity: { "@id": `${SITE_URL}/#nikolas-dion-savio` },
  };

  return (
    <div className="px-4 py-10 sm:px-8">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(profileSchema) }}
      />
      <div className="mx-auto w-full max-w-2xl">
        <div className="flex items-center gap-4">
          <Image
            src={photo}
            alt={name}
            width={760}
            height={950}
            priority
            className="h-16 w-16 rounded-md object-cover object-top"
          />
          <div>
            <h1 className="font-sans text-[1.9rem] font-semibold leading-tight text-ink">
              {greeting}
            </h1>
            {/* The formal name in visible copy. The greeting is the voice of
                the page and stays; this is the line that answers a search for
                the full name. */}
            <p className="mt-1 text-[0.8125rem] leading-snug text-ink-muted">
              {standfirst}
            </p>
          </div>
        </div>

        <div className="mt-6 space-y-4">
          {bio.map((paragraph, index) => (
            <p
              key={index}
              className="max-w-prose text-[1.0625rem] leading-relaxed text-ink-secondary"
            >
              {paragraph}
            </p>
          ))}
        </div>

        <dl className="mt-10 border-t border-line">
          {credentials.map((c) => (
            <div
              key={c.org}
              className="flex flex-col gap-0.5 border-b border-line py-3 sm:flex-row sm:items-baseline sm:justify-between sm:gap-6"
            >
              <dt className="text-[0.95rem] font-medium text-ink">{c.org}</dt>
              <dd className="text-sm text-ink-muted sm:text-right">{c.detail}</dd>
            </div>
          ))}
        </dl>

        <p className="mt-8 text-[0.95rem] text-ink-secondary">
          Find me on{" "}
          {links.map((link, i) => (
            <span key={link.label}>
              <a
                href={link.href}
                target={link.href.startsWith("mailto:") ? undefined : "_blank"}
                rel="noopener noreferrer"
                className="text-brand-text underline decoration-line-strong underline-offset-2 transition-colors hover:decoration-brand"
              >
                {link.label}
              </a>
              {i < links.length - 2 ? ", " : i === links.length - 2 ? ", or " : ""}
            </span>
          ))}
          .
        </p>

        <p className="mt-4 text-[0.95rem] text-ink-secondary">
          If a calculation, data mapping, or workflow could be clearer,{" "}
          <Link
            href="/contact"
            className="text-brand-text underline decoration-line-strong underline-offset-2 transition-colors hover:decoration-brand"
          >
            send feedback
          </Link>
          .
        </p>

        <Disclaimer />
      </div>
    </div>
  );
}
