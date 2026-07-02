// Methodology (route /methodology): how the platform turns filings into
// figures. Static, server-rendered. Reinforces the core promise — every number
// is traceable and the models are transparent, not a black box.

import type { Metadata } from "next";
import Card from "@/components/ui/Card";
import Disclaimer from "@/components/ui/Disclaimer";
import SectionHeader from "@/components/ui/SectionHeader";

export const metadata: Metadata = {
  title: "Methodology · Investment Intelligence",
  description:
    "How Investment Intelligence sources data and computes KPIs, valuation, the LBO model and the deal score — transparently and traceably.",
};

const SECTIONS: { title: string; body: string[] }[] = [
  {
    title: "Data & sources",
    body: [
      "Fundamentals are drawn from primary filings — SEC EDGAR company facts for US issuers (10-K / 20-F / 40-F, GAAP and IFRS) — with market data from public quote feeds. No paid data vendors are used.",
      "Figures are shown in the company's reporting currency. Where a quote and reporting currency differ, mixed-currency multiples are suppressed rather than silently converted, and the gap is flagged.",
      "Every value carries an as-of date and its source. When a figure is derived rather than reported verbatim, it is marked as such.",
    ],
  },
  {
    title: "KPIs",
    body: [
      "Operating and credit metrics are computed directly from the filed statements. Each figure exposes its formula and the exact inputs behind it, so any number can be traced back to a line item in a filing.",
      "Where an input is missing, the metric is left blank and the gap is named — nothing is inferred to fill a hole.",
    ],
  },
  {
    title: "Valuation",
    body: [
      "Trading multiples (EV/EBITDA, EV/Revenue, P/E) are applied to the latest figures to imply a value range. The range is editable — adjusting a multiple updates the implied figures immediately.",
      "Multiples are placed in context against a peer set, with the target's relative position shown rather than asserted.",
    ],
  },
  {
    title: "LBO model",
    body: [
      "A simplified five-year LBO: entry enterprise value from a multiple, debt sized against it, a Sources & Uses that balances with the sponsor-equity plug, a projected build of revenue, EBITDA, cash flow and debt paydown, and an exit that returns IRR and multiple of money.",
      "Companies that are not yet EBITDA-profitable are modeled on a revenue basis: entry prices on EV/Revenue, a margin ramp carries EBITDA to profitability, and the exit prices on EV/EBITDA once profitable. The return is framed as predicated on those operating assumptions, not on an unearned re-rating.",
      "Returns are bracketed by base, strategic-buyer and downside cases, and the debt path is stress-tested against a standard covenant package — so the output reads as a range and a credit view, not a single number.",
      "Every assumption is visible and editable; the whole model, including the sensitivity grids, recomputes on any change.",
    ],
  },
  {
    title: "Deal score",
    body: [
      "A transparent 0–100 screening score blends growth, profitability, leverage and valuation components. Each component, its weight and its inputs are shown on the Deal Score page, so the score summarises the figures above rather than hiding them.",
      "When a component cannot be computed, it is excluded and the remaining weights are redistributed — the score never invents an input.",
    ],
  },
  {
    title: "Investment memo",
    body: [
      "The memo is assembled deterministically from the computed figures using fixed templates. It is not written by a language model, and it introduces no facts that are not already on the analysis pages.",
    ],
  },
  {
    title: "What this is not",
    body: [
      "This is an educational screening tool built on public filings, not investment advice, an offer, or a recommendation. First-pass figures are a starting point for judgement, not a substitute for full diligence.",
    ],
  },
];

export default function MethodologyPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-8">
      <SectionHeader
        variant="page"
        as="h1"
        title="Methodology"
        subtitle="How filings become figures — sources, formulas and the models behind every page."
      />

      <div className="mt-6 space-y-4">
        {SECTIONS.map((section) => (
          <Card key={section.title}>
            <h2 className="font-display text-base font-semibold text-ink">
              {section.title}
            </h2>
            <div className="mt-2 space-y-2">
              {section.body.map((p, i) => (
                <p key={i} className="text-sm leading-relaxed text-ink-secondary">
                  {p}
                </p>
              ))}
            </div>
          </Card>
        ))}
      </div>

      <Disclaimer />
    </div>
  );
}
