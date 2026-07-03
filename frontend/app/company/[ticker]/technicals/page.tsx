"use client";

// Technicals (route /company/[ticker]/technicals): TradingView's technical
// analysis gauge for the current company — a markets read (oscillators, moving
// averages, an overall signal) that complements the fundamental analysis. It is
// framed explicitly as a secondary, market-sentiment view, not a screening input.

import { useCompany } from "@/components/company/CompanyContext";
import TradingViewWidget, { tvSymbol } from "@/components/markets/TradingViewWidget";
import Disclaimer from "@/components/ui/Disclaimer";
import SectionHeader from "@/components/ui/SectionHeader";

export default function TechnicalsPage() {
  const { profile } = useCompany();
  const symbol = tvSymbol(profile.ticker, profile.exchange);

  return (
    <div>
      <SectionHeader
        variant="page"
        as="h2"
        title="Technicals"
        subtitle="Oscillators, moving averages and an overall signal from TradingView. A market-sentiment read, complementary to the fundamental case, not a screening input."
      />
      <div className="mx-auto mt-6 max-w-3xl">
        <TradingViewWidget
          scriptSrc="embed-widget-technical-analysis.js"
          config={{
            interval: "1D",
            width: "100%",
            height: "100%",
            symbol,
            showIntervalTabs: true,
            displayMode: "multiple",
            isTransparent: false,
          }}
          className="h-[520px]"
        />
      </div>
      <p className="mt-3 text-center text-xs text-ink-muted">
        Technical summary and this widget are provided by TradingView, independent
        of the app&apos;s primary-source fundamentals.
      </p>
      <Disclaimer />
    </div>
  );
}
