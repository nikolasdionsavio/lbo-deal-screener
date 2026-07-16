"use client";

// Landing page (redesign 2026): author-led, not feature-led. A person built a
// research tool; the page opens with who, why, and a working search, then a
// real research path, one live worked example, and an honest statement of what
// the tool does and does not do. No marketing hero, no feature cards.

import Link from "next/link";
import SearchBar from "@/components/search/SearchBar";
import HomeWorkedExample from "@/components/landing/HomeWorkedExample";
import Disclaimer from "@/components/ui/Disclaimer";

// Three real starting points. Each reason is supported by the data the tool
// actually returns for that company (checked against the live API).
const STARTERS = [
  {
    ticker: "AAPL",
    name: "Apple",
    reason:
      "A large, cash-generative business. A good test of how the screen weighs operating quality against a high entry price.",
  },
  {
    ticker: "HD",
    name: "Home Depot",
    reason:
      "A retailer with steady margins and tight working capital to read across the cycle.",
  },
  {
    ticker: "DE",
    name: "Deere",
    reason:
      "A cyclical industrial with a financing arm, so the statements need more care.",
  },
];

const WORKFLOW = [
  {
    title: "Understand the business",
    body: "Review the description, filings, market data, and operating history.",
  },
  {
    title: "Test the economics",
    body: "Inspect KPIs, financial statements, valuation, and comparable companies.",
  },
  {
    title: "Form a first view",
    body: "Adjust the LBO assumptions, review the screening score, and produce a sourced memo.",
  },
];

const DOES = [
  "Organises public filing and market data",
  "Calculates transparent screening metrics",
  "Lets you edit the key assumptions",
  "Produces a structured first-pass memo",
];

const DOES_NOT = [
  "Replace full investment due diligence",
  "Verify management guidance",
  "Model every transaction detail",
  "Provide investment advice",
];

export default function LandingPage() {
  return (
    <div className="px-4 py-12 sm:px-8 sm:py-16">
      <div className="mx-auto w-full max-w-[1180px]">
        {/* Author + heading + search: left-aligned, no centred hero. */}
        <div className="max-w-2xl">
          <Link
            href="/about"
            className="inline-flex items-center gap-2 font-mono text-xs uppercase tracking-wide text-ink-muted transition-colors hover:text-ink"
          >
            Built by Nikolas Savio
          </Link>
          <h1 className="mt-4 text-[2.5rem] font-semibold leading-[1.08] tracking-tight text-ink sm:text-[3.25rem]">
            Company research you can check
          </h1>
          <p className="mt-4 max-w-xl text-[1.0625rem] leading-relaxed text-ink-secondary">
            Search a US-listed company and work through its filings, operating
            KPIs, valuation, peer set, and a five-year LBO model. Every
            calculated figure shows the source or assumption behind it.
          </p>

          <SearchBar
            className="mt-7"
            autoFocus
            placeholder="Search by company name or ticker"
          />

          <div className="mt-5 space-y-px">
            {STARTERS.map((s) => (
              <Link
                key={s.ticker}
                href={`/company/${s.ticker}/dashboard`}
                className="group flex items-baseline gap-3 border-t border-line py-2.5 transition-colors hover:bg-brand-soft"
              >
                <span className="font-mono text-xs text-filed">{s.ticker}</span>
                <span className="w-[4.5rem] shrink-0 text-sm font-medium text-ink">
                  {s.name}
                </span>
                <span className="text-sm leading-snug text-ink-muted">
                  {s.reason}
                </span>
              </Link>
            ))}
          </div>
        </div>

        {/* Founder note: the one piece of editorial serif on the page. */}
        <figure className="mt-14 max-w-2xl">
          <figcaption className="font-mono text-xs uppercase tracking-wide text-ink-muted">
            Why I built it
          </figcaption>
          <blockquote className="mt-3 font-display text-[1.2rem] leading-relaxed text-ink-secondary">
            I wanted one place where I could move from public filings to a
            first-pass investment view without copying figures across several
            tools or losing track of where they came from. Investment
            Intelligence is the result. It shows the work behind each output,
            including the parts that remain incomplete.
          </blockquote>
        </figure>

        {/* The research path: a real ordered sequence, not three feature cards. */}
        <section className="mt-16">
          <h2 className="text-sm font-semibold text-ink">How the work goes</h2>
          <ol className="mt-5 grid gap-x-8 gap-y-6 sm:grid-cols-3">
            {WORKFLOW.map((step, i) => (
              <li key={step.title} className="relative">
                <div className="flex items-center gap-3">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-line-strong font-mono text-xs text-ink-secondary">
                    {i + 1}
                  </span>
                  {i < WORKFLOW.length - 1 && (
                    <span
                      aria-hidden
                      className="hidden h-px flex-1 bg-line sm:block"
                    />
                  )}
                </div>
                <h3 className="mt-3 text-[0.95rem] font-semibold text-ink">
                  {step.title}
                </h3>
                <p className="mt-1 text-sm leading-snug text-ink-muted">
                  {step.body}
                </p>
              </li>
            ))}
          </ol>
        </section>

        {/* One live worked example, drawn from the real API. */}
        <HomeWorkedExample />

        {/* Honest scope. */}
        <section className="mt-16 grid max-w-3xl gap-8 sm:grid-cols-2">
          <div>
            <h2 className="text-sm font-semibold text-ink">
              What the tool does
            </h2>
            <ul className="mt-3">
              {DOES.map((d) => (
                <li
                  key={d}
                  className="border-t border-line py-2 text-sm text-ink-secondary"
                >
                  {d}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h2 className="text-sm font-semibold text-ink">
              What it does not do
            </h2>
            <ul className="mt-3">
              {DOES_NOT.map((d) => (
                <li
                  key={d}
                  className="border-t border-line py-2 text-sm text-ink-muted"
                >
                  {d}
                </li>
              ))}
            </ul>
          </div>
        </section>

        <p className="mt-8 max-w-3xl text-sm text-ink-muted">
          More on sources and formulas in the{" "}
          <Link
            href="/methodology"
            className="text-brand-text underline decoration-line-strong underline-offset-2 hover:decoration-brand"
          >
            methodology
          </Link>
          , and what has changed in the{" "}
          <Link
            href="/changelog"
            className="text-brand-text underline decoration-line-strong underline-offset-2 hover:decoration-brand"
          >
            changelog
          </Link>
          .
        </p>

        <div className="max-w-3xl">
          <Disclaimer />
        </div>
      </div>
    </div>
  );
}
