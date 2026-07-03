"use client";

// Shared shell for the global Markets tools (screener, overview, heatmap,
// calendar): a page header, a tall TradingView widget, and a one-line source
// note. Keeps the four tools visually identical (product register: consistent
// vocabulary screen to screen).

import TradingViewWidget from "@/components/markets/TradingViewWidget";
import Disclaimer from "@/components/ui/Disclaimer";
import SectionHeader from "@/components/ui/SectionHeader";

interface MarketToolPageProps {
  title: string;
  subtitle: string;
  scriptSrc: string;
  config: Record<string, unknown>;
}

export default function MarketToolPage({
  title,
  subtitle,
  scriptSrc,
  config,
}: MarketToolPageProps) {
  return (
    <div className="px-4 py-8 sm:px-8">
      <SectionHeader variant="page" as="h1" title={title} subtitle={subtitle} />
      <div className="mt-6">
        <TradingViewWidget
          scriptSrc={scriptSrc}
          config={config}
          className="h-[calc(100vh-15rem)] min-h-[540px]"
        />
      </div>
      <p className="mt-3 text-xs text-ink-muted">
        Live market data and this widget are provided by TradingView, independent
        of the app&apos;s primary-source fundamentals.
      </p>
      <Disclaimer />
    </div>
  );
}
