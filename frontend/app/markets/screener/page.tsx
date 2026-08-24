// Stock Screener (route /markets/screener): TradingView's stock screener —
// filter the US market by fundamentals to source screening candidates.

import type { Metadata } from "next";
import MarketToolPage from "@/components/markets/MarketToolPage";

export const metadata: Metadata = {
  title: "Stock Screener",
  description:
    "Screen the US market by fundamentals with TradingView's stock screener.",
};

export default function ScreenerPage() {
  return (
    <MarketToolPage
      title="Stock Screener"
      subtitle="Filter the US market by valuation, growth and profitability to source candidates."
      scriptSrc="embed-widget-screener.js"
      config={{
        width: "100%",
        height: "100%",
        defaultColumn: "overview",
        defaultScreen: "most_capitalized",
        market: "america",
        showToolbar: true,
        isTransparent: false,
      }}
    />
  );
}
