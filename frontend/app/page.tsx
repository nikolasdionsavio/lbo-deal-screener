"use client";

// Landing page (DESIGN.md Aesthetic v2): a hero inside a soft rounded
// container — outlined capsule label (the one deliberate capsule in the
// app), serif headline, sub line, and the search as a large prompt box with
// sample-ticker chips in its footer. Below, the Screen/Model/Memo points as
// icon-tile rows separated by dashed dividers.

import Link from "next/link";
import SearchBar from "@/components/search/SearchBar";
import Reveal from "@/components/landing/Reveal";
import Disclaimer from "@/components/ui/Disclaimer";

const SAMPLE_TICKERS = ["AAPL", "MSFT", "HD", "KO", "DE"];

// 16px, 1.5px-stroke tile icons (DESIGN.md Iconography).
function tileIconAttrs() {
  return {
    width: 16,
    height: 16,
    viewBox: "0 0 16 16",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.5,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true as const,
  };
}

function ScreenIcon() {
  return (
    <svg {...tileIconAttrs()}>
      <circle cx="7" cy="7" r="4.25" />
      <path d="M10.2 10.2 14 14" />
    </svg>
  );
}

function ModelIcon() {
  return (
    <svg {...tileIconAttrs()}>
      <rect x="3" y="1.5" width="10" height="13" rx="1.5" />
      <path d="M5.5 4.5h5" />
      <path d="M5.5 8h.01M8 8h.01M10.5 8h.01M5.5 11h.01M8 11h.01M10.5 11h.01" />
    </svg>
  );
}

function MemoIcon() {
  return (
    <svg {...tileIconAttrs()}>
      <path d="M9.5 1.5h-5a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1h7a1 1 0 0 0 1-1V4.5l-3-3Z" />
      <path d="M9.5 1.5v3h3" />
      <path d="M5.5 8.5h5M5.5 11h5" />
    </svg>
  );
}

const POINTS = [
  {
    title: "Screen",
    body: "Company dashboard, traceable KPIs, valuation multiples, and a transparent 0-100 deal score. Every figure shows its formula, inputs, and period.",
    Icon: ScreenIcon,
  },
  {
    title: "Model",
    body: "A simplified five-year LBO with editable assumptions, IRR and multiple of money, and sensitivity tables across entry, exit, growth, and margin.",
    Icon: ModelIcon,
  },
  {
    title: "Memo",
    body: "An auto-generated investment memo built only from computed figures. Missing data is stated as missing, never invented.",
    Icon: MemoIcon,
  },
];

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col px-8">
      <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center py-16">
        <Reveal>
          <section className="rounded-3xl bg-surface-sunken px-6 py-12 text-center sm:px-12 sm:py-14">
            <span className="inline-flex items-center rounded-full border border-line-strong px-3 py-1 text-[11px] font-medium tracking-wide text-ink-muted">
              DEAL SCREENING
            </span>
            <h1 className="mt-5 font-display text-[2.5rem] font-semibold leading-tight text-ink">
              LBO Deal Screener
            </h1>
            <p className="mt-3 text-base text-ink-secondary">
              A private equity style deal screening tool for public companies.
            </p>

            <SearchBar
              className="mx-auto mt-8 w-full max-w-xl text-left"
              autoFocus
              footer={SAMPLE_TICKERS.map((ticker) => (
                <Link
                  key={ticker}
                  href={`/company/${ticker}/dashboard`}
                  className="rounded-full border border-line px-2.5 py-1 text-xs font-medium tabular-nums text-ink-muted transition-colors duration-150 hover:border-line-strong hover:text-ink"
                >
                  {ticker}
                </Link>
              ))}
            />
          </section>
        </Reveal>

        <Reveal className="mt-12">
          <div className="mx-auto max-w-2xl">
            {POINTS.map((point, index) => (
              <div key={point.title}>
                {index > 0 && <div className="divider-dashed" />}
                <div className="flex items-start gap-4 py-5">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded border border-line bg-surface text-ink-secondary">
                    <point.Icon />
                  </span>
                  <div className="min-w-0">
                    <h2 className="text-sm font-semibold text-ink">
                      {point.title}
                    </h2>
                    <p className="mt-1 text-sm leading-relaxed text-ink-muted">
                      {point.body}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Reveal>
      </div>

      <Reveal className="mx-auto w-full max-w-3xl">
        <Disclaimer />
      </Reveal>
    </div>
  );
}
