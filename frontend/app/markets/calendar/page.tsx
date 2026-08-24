// Economic Calendar (route /markets/calendar): TradingView events widget —
// upcoming macro releases across the major economies, for deal-timing context.

import type { Metadata } from "next";
import MarketToolPage from "@/components/markets/MarketToolPage";

export const metadata: Metadata = {
  title: "Economic Calendar",
  description:
    "Upcoming macroeconomic releases across the major economies (TradingView).",
};

export default function CalendarPage() {
  return (
    <MarketToolPage
      title="Economic Calendar"
      subtitle="Upcoming macro releases across the major economies: context for entry timing."
      scriptSrc="embed-widget-events.js"
      config={{
        width: "100%",
        height: "100%",
        importanceFilter: "0,1",
        countryFilter: "us,eu,gb,jp,cn,ca",
        isTransparent: false,
      }}
    />
  );
}
