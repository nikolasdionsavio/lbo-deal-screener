"use client";

// Landing.
//
// Composition alternates density rather than repeating one layout: an
// asymmetric opening, a full-width band carrying the live screen, an editorial
// worked example, a scroll-scrubbed coverage sequence, a sequence that runs
// across, and a scope comparison that runs down.
//
// Motion is choreographed, not staggered. The hero arrives in an order that
// says what matters: the rule and running head establish the column, the
// statement rides up a line at a time inside its own mask, the search field
// follows because it is the thing to do next, and the supporting material
// lands last. Nothing is delayed by a uniform 0.1s; the lead times below are
// the sequence.

import Link from "next/link";
import SearchBar from "@/components/search/SearchBar";
import HomeScreenExample from "@/components/landing/HomeScreenExample";
import HomeWorkedExample from "@/components/landing/HomeWorkedExample";
import HomeCoverage from "@/components/landing/HomeCoverage";
import Container from "@/components/ui/Container";
import Disclaimer from "@/components/ui/Disclaimer";
import { Reveal, SplitLines, useMagnetic } from "@/lib/motion";

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
  // The one magnetic element on the page. A single CTA that answers to the
  // pointer reads as attention; a page of them reads as a demo.
  const screenCta = useMagnetic<HTMLAnchorElement>({ strength: 0.3, max: 8 });

  return (
    <div className="pb-20 pt-12 lg:pb-28 lg:pt-16">
      <Container>
        <div className="grid grid-cols-12 gap-x-6 gap-y-12">
          <div className="col-span-12 lg:col-span-6">
            <Reveal variant="rule">
              <p className="tape">
                <Link
                  href="/about"
                  className="text-ink-muted transition-colors hover:text-ink"
                >
                  Built and maintained by Nikolas Savio
                </Link>
              </p>
            </Reveal>

            <h1 className="ed-statement mt-7 max-w-[13ch] text-ink">
              <SplitLines
                text="Company research you can check"
                lead={90}
                step={95}
              />
            </h1>

            <Reveal variant="rise" lead={520}>
              <p className="ed-intro mt-7">
                Screen every US-listed filer on revenue, margin and leverage,
                then work through one company&rsquo;s filings, operating
                results, valuation, peer set, and a simplified LBO case.
                Calculated figures show the source or assumption behind them.
              </p>
            </Reveal>

            <Reveal variant="rise" lead={640}>
              <p className="mt-7">
                <Link
                  href="/methodology"
                  className="link-slide text-[0.9375rem] text-link"
                >
                  How the figures are sourced
                </Link>
              </p>
            </Reveal>
          </div>

          <div className="col-span-12 lg:col-span-6 xl:col-start-8 xl:col-span-5">
            {/* The search arrives before the supporting prose: it is the thing
                to do next, and entrance order is the argument for importance. */}
            <Reveal variant="lift" lead={400}>
              <SearchBar autoFocus />
            </Reveal>

            <Reveal variant="rise" lead={560}>
              <p className="tape mt-5">Or start with one of these</p>
            </Reveal>

            <ul className="mt-1">
              {STARTERS.map((s, i) => (
                <Reveal
                  as="li"
                  key={s.ticker}
                  variant="settle"
                  index={i}
                  step={70}
                  lead={620}
                >
                  <Link
                    href={`/company/${s.ticker}/dashboard`}
                    className="starter group grid grid-cols-[3.5rem_1fr] items-baseline gap-x-3 border-t border-line py-3.5"
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
                </Reveal>
              ))}
              <li className="border-t border-line" />
            </ul>

            <Reveal variant="rise" lead={820}>
              <p className="mt-5">
                <Link
                  ref={screenCta}
                  href="/screen"
                  className="link-slide text-[0.9375rem] text-link"
                >
                  Or screen every US-listed filer by revenue, margin and
                  leverage
                </Link>
                <span className="mt-1 block text-[0.8125rem] leading-snug text-ink-muted">
                  Figures taken from each company&rsquo;s own SEC filings. Set a
                  revenue band, a margin floor, a net debt / EBITDA range and a
                  sector, then send the shortlist as a link.
                </span>
              </p>
            </Reveal>
          </div>
        </div>
      </Container>

      {/* Screening comes before the single-company example: it is the step that
          finds the company you then research. */}
      <HomeScreenExample />

      {/* The signature scroll-linked sequence. */}
      <HomeCoverage />

      <Container>
        <HomeWorkedExample />

        <section className="mt-28 lg:mt-36">
          <figure className="grid grid-cols-12 gap-x-6">
            <Reveal
              as="figure"
              variant="rule"
              className="col-span-12 md:col-span-3"
            >
              <figcaption className="tape">Nikolas&rsquo;s note</figcaption>
            </Reveal>
            <blockquote className="col-span-12 md:col-span-9">
              <span className="ed-title block !text-[clamp(1.375rem,1.1rem+1.1vw,1.875rem)] !leading-[1.36] text-ink-secondary">
                <SplitLines
                  text="I built this tool because I wanted a quicker way to move from a filing to a first-pass investment view without losing track of where each number came from. The output is meant to be questioned, adjusted, and checked."
                  step={55}
                />
              </span>
            </blockquote>
          </figure>
        </section>

        {/* A real ordered sequence, so the numbers carry information. Runs
            across at desktop, which breaks the vertical rhythm either side. */}
        <section className="mt-28 lg:mt-36">
          <Reveal variant="rule">
            <p className="tape">How the work goes</p>
          </Reveal>
          <Reveal variant="lift" lead={80}>
            <h2 className="ed-section mt-6 max-w-[18ch]">
              From a filing to a first view, in three passes
            </h2>
          </Reveal>
          <ol className="mt-12 grid gap-x-8 gap-y-10 md:grid-cols-3">
            {WORKFLOW.map((step, i) => (
              <Reveal
                as="li"
                key={step.title}
                variant="lift"
                index={i}
                step={110}
              >
                <div className="hairline mb-5" />
                <span className="font-mono text-[0.6875rem] font-semibold tabular-nums text-brand-text">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <h3 className="ed-sub mt-3">{step.title}</h3>
                <p className="mt-2.5 max-w-[42ch] text-[0.9375rem] leading-relaxed text-ink-secondary">
                  {step.body}
                </p>
              </Reveal>
            ))}
          </ol>
        </section>

        {/* Honest scope. */}
        <section className="mt-28 lg:mt-36">
          <Reveal variant="rule">
            <p className="tape">What this is</p>
          </Reveal>
          <div className="mt-10 grid gap-x-12 gap-y-10 md:grid-cols-2">
            <div>
              <p className="font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.08em] text-ink">
                It does
              </p>
              <ul className="mt-4">
                {DOES.map((d, i) => (
                  <Reveal
                    as="li"
                    key={d}
                    variant="settle"
                    index={i}
                    step={60}
                    className="border-t border-line py-3 text-[0.9375rem] leading-snug text-ink-secondary"
                  >
                    {d}
                  </Reveal>
                ))}
              </ul>
            </div>
            <div>
              <p className="font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.08em] text-ink-muted">
                It does not
              </p>
              <ul className="mt-4">
                {DOES_NOT.map((d, i) => (
                  <Reveal
                    as="li"
                    key={d}
                    variant="settle"
                    index={i}
                    step={60}
                    lead={90}
                    className="border-t border-line py-3 text-[0.9375rem] leading-snug text-ink-muted"
                  >
                    {d}
                  </Reveal>
                ))}
              </ul>
            </div>
          </div>
        </section>

        <Reveal variant="rise">
          <p className="mt-16 text-[0.9375rem] text-ink-muted">
            Sources and formulas are documented in the{" "}
            <Link href="/methodology" className="link-slide text-link">
              methodology
            </Link>
            . What has changed, and when, is in the{" "}
            <Link href="/changelog" className="link-slide text-link">
              changelog
            </Link>
            .
          </p>
        </Reveal>

        <Disclaimer />
      </Container>
    </div>
  );
}
