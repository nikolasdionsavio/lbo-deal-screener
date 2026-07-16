// About (route /about): presentational only. Content is read from lib/about.ts.
// Short and spoken: a greeting, a few plain paragraphs, factual credentials,
// and text links. No gradient frame, no colored tiles, no status dot.

import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import Disclaimer from "@/components/ui/Disclaimer";
import { about } from "@/lib/about";

export const metadata: Metadata = {
  title: "About · Investment Intelligence",
  description:
    "Nikolas Savio built Investment Intelligence to move from company filings to a first-pass investment view without losing the audit trail.",
};

export default function AboutPage() {
  const { greeting, photo, name, bio, credentials, links } = about;

  return (
    <div className="px-4 py-10 sm:px-8">
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
          <h1 className="font-sans text-[1.9rem] font-semibold leading-tight text-ink">
            {greeting}
          </h1>
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
