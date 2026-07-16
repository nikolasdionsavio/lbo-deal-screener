// How to use (route /how-to-use): a concise guide to the screening workflow,
// step by step. Static content, server-rendered. Numbered steps use the
// icon-tile treatment (DESIGN.md Aesthetic v2) inside a Card, with dashed
// dividers between groups.

import type { Metadata } from "next";
import Card from "@/components/ui/Card";
import Disclaimer from "@/components/ui/Disclaimer";
import SectionHeader from "@/components/ui/SectionHeader";

export const metadata: Metadata = {
  title: "How to use · Investment Intelligence",
  description:
    "A step-by-step guide to screening a US-listed company: dashboard, KPIs, financials, valuation, LBO model, peers, deal score, and memo.",
};

const STEPS: { title: string; body: string }[] = [
  {
    title: "Search a company",
    body: "Start from the search box on the landing page or the top bar. Enter a US-listed company by ticker or name. Press / anywhere to jump to search.",
  },
  {
    title: "Dashboard",
    body: "Open with the snapshot: price, market data, a business description, and recent filings. This is the orientation page before the analysis.",
  },
  {
    title: "KPIs",
    body: "Read the operating and credit metrics. Each figure shows its formula and the inputs behind it, so a number can always be traced back to a filed line item.",
  },
  {
    title: "Financials",
    body: "Review the three statements (income statement, balance sheet, and cash flow) across multiple fiscal years, drawn from the company's filings.",
  },
  {
    title: "Valuation",
    body: "See trading multiples with an implied value range. The range is editable: adjust the assumptions and the implied figures update.",
  },
  {
    title: "LBO Model",
    body: "Work through a simplified five-year LBO with editable assumptions. It returns IRR and multiple of money, plus sensitivity tables across entry, exit, growth, and margin.",
  },
  {
    title: "Peer Comps",
    body: "Compare the company against a peer set on size, growth, margins, and valuation multiples to place it in context.",
  },
  {
    title: "Deal Score",
    body: "Read a transparent 0–100 screening score. Every component and its weight is shown, so the score is a summary of the figures above, not a black box.",
  },
  {
    title: "Memo",
    body: "Open the investment memo, assembled automatically from the figures on these pages. Save it to a watchlist to keep a snapshot. Saving requires an account.",
  },
];

// 16px, 1.5px-stroke document icon for the "Good to know" tile (DESIGN.md
// Iconography), matching the landing tile-row treatment.
function NoteIcon() {
  return (
    <svg
      width={16}
      height={16}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="8" cy="8" r="6.25" />
      <path d="M8 7.25v3.75" />
      <path d="M8 5h.01" />
    </svg>
  );
}

export default function HowToUsePage() {
  return (
    <div className="flex min-h-[calc(100vh-3rem)] flex-col px-4 py-8 sm:px-8">
      <div className="mx-auto w-full max-w-3xl">
        <SectionHeader
          variant="page"
          title="How to use"
          subtitle="Screen a public company as an LBO candidate, one page at a time. Every figure traces back to its source."
        />

        <Card>
          <ol>
            {STEPS.map((step, index) => (
              <li key={step.title}>
                {index > 0 && <div className="divider-dashed" />}
                <div className="flex items-start gap-4 py-4">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded border border-line bg-surface-sunken text-sm font-medium tabular-nums text-ink-secondary">
                    {index + 1}
                  </span>
                  <div className="min-w-0">
                    <h2 className="text-sm font-semibold text-ink">
                      {step.title}
                    </h2>
                    <p className="mt-1 text-sm leading-relaxed text-ink-muted">
                      {step.body}
                    </p>
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </Card>

        <Card className="mt-6">
          <div className="flex items-start gap-4">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded border border-line bg-surface text-ink-secondary">
              <NoteIcon />
            </span>
            <div className="min-w-0">
              <h2 className="text-sm font-semibold text-ink">Good to know</h2>
              <p className="mt-1 max-w-prose text-sm leading-relaxed text-ink-muted">
                Data comes from SEC EDGAR and market data providers. Every figure
                is traceable to a filing or a stated assumption, and missing data
                is shown as missing rather than invented. This is a research and
                screening tool, not investment advice.
              </p>
            </div>
          </div>
        </Card>
      </div>
      <div className="mx-auto w-full max-w-3xl">
        <Disclaimer />
      </div>
    </div>
  );
}
