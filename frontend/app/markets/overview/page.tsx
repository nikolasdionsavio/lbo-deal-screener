// Markets Overview (route /markets/overview): TradingView market overview —
// indices, futures, bonds and FX at a glance for macro context.

import type { Metadata } from "next";
import MarketToolPage from "@/components/markets/MarketToolPage";

export const metadata: Metadata = {
  title: "Markets Overview",
  description: "Global indices, futures, bonds and FX, live from TradingView.",
};

export default function MarketsOverviewPage() {
  return (
    <MarketToolPage
      title="Markets Overview"
      subtitle="Indices, futures, bonds and FX at a glance: the macro backdrop for any screen."
      scriptSrc="embed-widget-market-overview.js"
      config={{
        width: "100%",
        height: "100%",
        showChart: true,
        showSymbolLogo: true,
        isTransparent: false,
        dateRange: "12M",
        showFloatingTooltip: true,
        tabs: [
          {
            title: "Indices",
            symbols: [
              { s: "FOREXCOM:SPXUSD", d: "S&P 500" },
              { s: "FOREXCOM:NSXUSD", d: "US 100" },
              { s: "FOREXCOM:DJI", d: "Dow 30" },
              { s: "INDEX:NKY", d: "Nikkei 225" },
              { s: "INDEX:DEU40", d: "DAX" },
              { s: "FOREXCOM:UKXGBP", d: "FTSE 100" },
            ],
          },
          {
            title: "Futures",
            symbols: [
              { s: "CME_MINI:ES1!", d: "S&P 500" },
              { s: "COMEX:GC1!", d: "Gold" },
              { s: "NYMEX:CL1!", d: "Crude Oil" },
              { s: "NYMEX:NG1!", d: "Natural Gas" },
            ],
          },
          {
            title: "Bonds",
            symbols: [
              { s: "CBOT:ZB1!", d: "T-Bond" },
              { s: "CBOT:UB1!", d: "Ultra T-Bond" },
              { s: "EUREX:FGBL1!", d: "Euro Bund" },
            ],
          },
          {
            title: "Forex",
            symbols: [
              { s: "FX:EURUSD", d: "EUR/USD" },
              { s: "FX:GBPUSD", d: "GBP/USD" },
              { s: "FX:USDJPY", d: "USD/JPY" },
            ],
          },
        ],
      }}
    />
  );
}
