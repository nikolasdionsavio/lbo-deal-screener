"use client";

import Link from "next/link";
import SearchBar from "@/components/search/SearchBar";
import Disclaimer from "@/components/ui/Disclaimer";

const SAMPLE_TICKERS = ["AAPL", "MSFT", "HD", "KO", "DE"];

const POINTS = [
  {
    title: "Screen",
    body: "Company dashboard, traceable KPIs, valuation multiples, and a transparent 0-100 deal score. Every figure shows its formula, inputs, and period.",
  },
  {
    title: "Model",
    body: "A simplified five-year LBO with editable assumptions, IRR and multiple of money, and sensitivity tables across entry, exit, growth, and margin.",
  },
  {
    title: "Memo",
    body: "An auto-generated investment memo built only from computed figures. Missing data is stated as missing, never invented.",
  },
];

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col px-8">
      <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col justify-center py-16">
        <h1 className="text-center font-display text-[2.5rem] font-semibold leading-tight text-ink">
          LBO Deal Screener
        </h1>
        <p className="mt-3 text-center text-base text-ink-secondary">
          A private equity style deal screening tool for public companies.
        </p>

        <SearchBar className="mt-10" autoFocus />

        <div className="mt-5 flex flex-wrap items-center justify-center gap-2 text-sm">
          <span className="text-ink-muted">Sample companies:</span>
          {SAMPLE_TICKERS.map((ticker) => (
            <Link
              key={ticker}
              href={`/company/${ticker}/dashboard`}
              className="rounded-full border border-line bg-surface px-3 py-1 font-medium tabular-nums text-ink-secondary transition-colors duration-150 hover:border-line-strong hover:text-ink"
            >
              {ticker}
            </Link>
          ))}
        </div>

        <div className="mt-16 grid gap-8 border-t border-line pt-10 sm:grid-cols-3">
          {POINTS.map((point) => (
            <div key={point.title}>
              <h2 className="text-sm font-semibold text-ink">{point.title}</h2>
              <p className="mt-1.5 text-sm leading-relaxed text-ink-muted">
                {point.body}
              </p>
            </div>
          ))}
        </div>
      </div>

      <div className="mx-auto w-full max-w-2xl">
        <Disclaimer />
      </div>
    </div>
  );
}
