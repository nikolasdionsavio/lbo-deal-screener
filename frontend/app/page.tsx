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
        <h1 className="text-center text-3xl font-semibold text-brand">
          LBO Deal Screener
        </h1>
        <p className="mt-3 text-center text-base text-slate-600">
          A private equity style deal screening tool for public companies.
        </p>

        <SearchBar className="mt-8" autoFocus />

        <div className="mt-4 flex flex-wrap items-center justify-center gap-2 text-sm">
          <span className="text-slate-500">Sample companies:</span>
          {SAMPLE_TICKERS.map((ticker) => (
            <Link
              key={ticker}
              href={`/company/${ticker}/dashboard`}
              className="rounded border border-slate-300 bg-surface px-2.5 py-1 font-medium tabular-nums text-brand hover:border-brand"
            >
              {ticker}
            </Link>
          ))}
        </div>

        <div className="mt-14 grid gap-8 sm:grid-cols-3">
          {POINTS.map((point) => (
            <div key={point.title}>
              <h2 className="text-sm font-semibold uppercase tracking-wide text-ink">
                {point.title}
              </h2>
              <p className="mt-1.5 text-sm leading-relaxed text-slate-600">
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
