"use client";

// Landing (DESIGN.md: annotated analyst workbook, public density).
// Asymmetric opening: the authored statement on the left, the working search on
// the right. Then one annotated research sheet, a note from Nikolas, the real
// research path, and an honest statement of scope. No SaaS hero, no feature
// cards, no centred column.

import Link from "next/link";
import SearchBar from "@/components/search/SearchBar";
import HomeWorkedExample from "@/components/landing/HomeWorkedExample";
import Disclaimer from "@/components/ui/Disclaimer";

// Three real starting points. Each note is supported by the data this tool
// actually returns for that company (checked against the live API).
const STARTERS = [
  {
    ticker: "AAPL",
    name: "Apple",
    note: "Large and cash-generative. Shows how the screen weighs operating quality against a high entry price.",
  },
  {
    ticker: "HD",
    name: "Home Depot",
    note: "Steady margins and tight working capital to read across the cycle.",
  },
  {
    ticker: "DE",
    name: "Deere",
    note: "A cyclical industrial with a financing arm, so the statements need more care.",
  },
];

const WORKFLOW = [
  {
    title: "Understand the business",
    body: "Read the description, the filings, market data, and the operating history.",
  },
  {
    title: "Test the economics",
    body: "Inspect the KPIs, the filed statements, valuation, and the peer set.",
  },
  {
    title: "Form a first view",
    body: "Adjust the LBO assumptions, read the screening score, and produce a sourced memo.",
  },
];

const DOES = [
  "Organises public filing and market data",
  "Calculates screening metrics that show their formula",
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
    <div className="px-[18px] py-14 sm:px-8 lg:px-12 lg:py-20">
      <div className="mx-auto w-full max-w-[1240px]">
        {/* Asymmetric opening. */}
        <div className="grid grid-cols-12 gap-x-6 gap-y-12">
          <div className="col-span-12 lg:col-span-6 xl:col-span-6">
            <p className="font-mono text-[11px] text-ink-muted">
              Built and maintained by{" "}
              <Link
                href="/about"
                className="text-link underline decoration-line-strong underline-offset-2 transition-colors hover:text-link-hover"
              >
                Nikolas Savio
              </Link>
            </p>
            <h1 className="mt-5 max-w-[11ch] font-display text-[2.625rem] font-normal leading-[1.05] tracking-[-0.01em] text-ink sm:text-[3.375rem] lg:text-[3.75rem]">
              Company research you can check
            </h1>
            <p className="mt-6 max-w-[54ch] text-[1.1875rem] leading-[1.55] text-ink-secondary">
              Search a US-listed company and work through its filings, operating
              results, valuation, peer set, and a simplified LBO case.
              Calculated figures show the source or assumption behind them.
            </p>
            <p className="mt-6">
              <Link
                href="/methodology"
                className="text-[0.95rem] text-link underline decoration-line-strong underline-offset-[3px] transition-colors hover:text-link-hover hover:decoration-link"
              >
                How the figures are sourced
              </Link>
            </p>
          </div>

          <div className="col-span-12 lg:col-span-6 lg:pt-1 xl:col-start-8 xl:col-span-5">
            <SearchBar autoFocus />
            <p className="mt-3 font-mono text-[11px] text-ink-muted">
              Or start with one of these
            </p>
            <ul className="mt-2">
              {STARTERS.map((s) => (
                <li key={s.ticker}>
                  <Link
                    href={`/company/${s.ticker}/dashboard`}
                    className="group grid grid-cols-[3.5rem_1fr] items-baseline gap-x-3 border-t border-line py-3 transition-colors hover:bg-brand-soft"
                  >
                    <span className="font-mono text-[11px] text-ink-muted transition-colors group-hover:text-brand-text">
                      {s.ticker}
                    </span>
                    <span>
                      <span className="text-[0.95rem] font-medium text-ink">
                        {s.name}
                      </span>
                      <span className="mt-0.5 block text-[0.8125rem] leading-snug text-ink-muted">
                        {s.note}
                      </span>
                    </span>
                  </Link>
                </li>
              ))}
              <li className="border-t border-line" />
            </ul>
          </div>
        </div>

        {/* One annotated research sheet, drawn live from the API. */}
        <HomeWorkedExample />

        {/* Nikolas's note: thin rule, Charter, small authorship label. */}
        <section className="mt-20 grid grid-cols-12 gap-x-6">
          <figure className="col-span-12 border-l border-line-strong pl-6 md:col-span-7 lg:col-span-6">
            <figcaption className="font-mono text-[11px] text-ink-muted">
              Nikolas&rsquo;s note
            </figcaption>
            <blockquote className="mt-3 font-display text-[1.1875rem] leading-[1.6] text-ink-secondary">
              I built this tool because I wanted a quicker way to move from a
              filing to a first-pass investment view without losing track of
              where each number came from. The output is meant to be questioned,
              adjusted, and checked.
            </blockquote>
          </figure>
        </section>

        {/* The research path: a real ordered sequence. */}
        <section className="mt-20 border-t border-line pt-8">
          <div className="grid grid-cols-12 gap-x-6 gap-y-6">
            <h2 className="col-span-12 text-[0.8125rem] font-semibold text-ink md:col-span-3">
              How the work goes
            </h2>
            <ol className="col-span-12 md:col-span-9">
              {WORKFLOW.map((step, i) => (
                <li
                  key={step.title}
                  className="grid grid-cols-[2rem_1fr] gap-x-3 border-b border-line py-4 last:border-b-0"
                >
                  <span className="font-mono text-[11px] text-ink-muted">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <div>
                    <h3 className="text-[0.95rem] font-medium text-ink">
                      {step.title}
                    </h3>
                    <p className="mt-1 max-w-[62ch] text-[0.875rem] leading-snug text-ink-muted">
                      {step.body}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* Honest scope. */}
        <section className="mt-16 border-t border-line pt-8">
          <div className="grid grid-cols-12 gap-x-6 gap-y-8">
            <h2 className="col-span-12 text-[0.8125rem] font-semibold text-ink md:col-span-3">
              What this is
            </h2>
            <div className="col-span-12 grid gap-x-6 gap-y-8 md:col-span-9 md:grid-cols-2">
              <div>
                <p className="font-mono text-[11px] text-ink-muted">It does</p>
                <ul className="mt-2">
                  {DOES.map((d) => (
                    <li
                      key={d}
                      className="border-t border-line py-2 text-[0.875rem] text-ink-secondary"
                    >
                      {d}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="font-mono text-[11px] text-ink-muted">
                  It does not
                </p>
                <ul className="mt-2">
                  {DOES_NOT.map((d) => (
                    <li
                      key={d}
                      className="border-t border-line py-2 text-[0.875rem] text-ink-muted"
                    >
                      {d}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </section>

        <p className="mt-10 text-[0.875rem] text-ink-muted">
          Sources and formulas are documented in the{" "}
          <Link
            href="/methodology"
            className="text-link underline decoration-line-strong underline-offset-2 hover:text-link-hover"
          >
            methodology
          </Link>
          . What has changed, and when, is in the{" "}
          <Link
            href="/changelog"
            className="text-link underline decoration-line-strong underline-offset-2 hover:text-link-hover"
          >
            changelog
          </Link>
          .
        </p>

        <Disclaimer />
      </div>
    </div>
  );
}
