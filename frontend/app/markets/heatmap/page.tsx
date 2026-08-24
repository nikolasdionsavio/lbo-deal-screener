// Sector Heatmap (route /markets/heatmap): TradingView stock heatmap — the
// S&P 500 sized by market cap and coloured by change, grouped by sector.

import type { Metadata } from "next";
import MarketToolPage from "@/components/markets/MarketToolPage";

export const metadata: Metadata = {
  title: "Sector Heatmap",
  description:
    "The S&P 500 by sector and market cap, coloured by daily change (TradingView).",
};

export default function HeatmapPage() {
  return (
    <MarketToolPage
      title="Sector Heatmap"
      subtitle="The S&P 500 sized by market cap and coloured by change, grouped by sector."
      scriptSrc="embed-widget-stock-heatmap.js"
      config={{
        dataSource: "SPX500",
        blockSize: "market_cap_basic",
        blockColor: "change",
        grouping: "sector",
        symbolUrl: "",
        hasTopBar: false,
        isDataSetEnabled: false,
        isZoomEnabled: true,
        hasSymbolTooltip: true,
        isMonoSize: false,
        width: "100%",
        height: "100%",
      }}
    />
  );
}
