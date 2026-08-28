"use client";

// Landing (DESIGN.md: annotated analyst workbook, public density).
//
// Composition. The page alternates between two densities rather than repeating
// one. Editorial sections sit in the reading column; the screen band runs the
// full width of the viewport on its own surface, because the product's own
// density is the argument for it and a band is how you show density without
// describing it. Section rhythm varies deliberately: the opening is asymmetric,
// the band is full width, the sequence runs across, the scope runs down.
//
// No SaaS hero, no feature cards, no centred column.

import Link from "next/link";
import SearchBar from "@/components/search/SearchBar";
import HomeScreenExample from "@/components/landing/HomeScreenExample";
import HomeWorkedExample from "@/components/landing/HomeWorkedExample";
import Container from "@/components/ui/Container";
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
    <div className="pb-14 pt-14 lg:pb-20 lg:pt-20">
      {/* Asymmetric opening: authored statement left, working search right. */}
      <Container>
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
            <h1 className="ed-statement mt-5 max-w-[11ch] text-ink">
              Company research you can check
            </h1>
            <p className="ed-intro mt-6 max-w-[54ch]">
              Screen every US-listed filer on revenue, margin and leverage, then
              work through one company&rsquo;s filings, operating results,
              valuation, peer set, and a simplified LBO case. Calculated figures
              show the source or assumption behind them.
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
            {/* The second way in. Starting from a ticker assumes you already
                have a company in mind; this is the path for when you do not. */}
            <p className="mt-4">
              <Link
                href="/screen"
                className="text-[0.95rem] text-link underline decoration-line-strong underline-offset-[3px] transition-colors hover:text-link-hover hover:decoration-link"
              >
                Or screen every US-listed filer by revenue, margin and leverage
              </Link>
              <span className="mt-1 block text-[0.8125rem] leading-snug text-ink-muted">
                Figures taken from each company&rsquo;s own SEC filings. Set a
                revenue band, a margin floor, a net debt / EBITDA range and a
                sector, then send the shortlist as a link.
              </span>
            </p>
          </div>
        </div>
      </Container>

      {/* Screening comes before the single-company example: it is the step that
          finds the company you then research. It gets the band because it is
          the densest thing on the site, and density is the claim. */}
      <HomeScreenExample />

      <Container>
        <HomeWorkedExample />

        {/* Nikolas's note. Set wide and quiet rather than boxed: the authorship
            line does the framing that a container would otherwise do. */}
        <section className="mt-24">
          <figure className="grid grid-cols-12 gap-x-6">
            <figcaption className="col-span-12 font-mono text-[11px] text-ink-muted md:col-span-3">
              Nikolas&rsquo;s note
            </figcaption>
            <blockquote className="col-span-12 font-display text-[1.3125rem] leading-[1.55] text-ink-secondary md:col-span-9 lg:text-[1.4375rem]">
              I built this tool because I wanted a quicker way to move from a
              filing to a first-pass investment view without losing track of
              where each number came from. The output is meant to be questioned,
              adjusted, and checked.
            </blockquote>
          </figure>
        </section>

        {/* The research path: a real ordered sequence, so the numbers carry
            information. Runs across at desktop, which breaks the vertical
            list rhythm the sections above and below both use. */}
        <section className="mt-24 border-t border-line pt-10">
          <h2 className="ed-section">How the work goes</h2>
          <ol className="mt-8 grid gap-x-6 gap-y-8 md:grid-cols-3">
            {WORKFLOW.map((step, i) => (
              <li key={step.title} className="border-t border-line-strong pt-4">
                <span className="font-mono text-[11px] font-semibold text-brand-text">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <h3 className="ed-sub mt-2">{step.title}</h3>
                <p className="mt-2 max-w-[42ch] text-[0.9375rem] leading-relaxed text-ink-secondary">
                  {step.body}
                </p>
              </li>
            ))}
          </ol>
        </section>

        {/* Honest scope. Two columns that read as one comparison, not as two
            unrelated lists. */}
        <section className="mt-24 border-t border-line pt-10">
          <h2 className="ed-section">What this is</h2>
          <div className="mt-8 grid gap-x-10 gap-y-8 md:grid-cols-2">
            <div>
              <p className="label-mono">It does</p>
              <ul className="mt-3">
                {DOES.map((d) => (
                  <li
                    key={d}
                    className="border-t border-line py-2.5 text-[0.9375rem] leading-snug text-ink-secondary"
                  >
                    {d}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="label-mono">It does not</p>
              <ul className="mt-3">
                {DOES_NOT.map((d) => (
                  <li
                    key={d}
                    className="border-t border-line py-2.5 text-[0.9375rem] leading-snug text-ink-muted"
                  >
                    {d}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        <p className="mt-12 text-[0.9375rem] text-ink-muted">
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
      </Container>
    </div>
  );
}
