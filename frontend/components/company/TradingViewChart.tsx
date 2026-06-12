"use client";

// Official TradingView Advanced Chart embed widget. The widget supplies its
// own price data and carries TradingView's required attribution; it is purely
// presentational and independent of the app's data providers. The widget is
// torn down and re-created whenever the app theme changes so its colorTheme
// always matches.

import { useEffect, useRef } from "react";
import { useTheme } from "@/lib/theme";

interface TradingViewChartProps {
  ticker: string;
  exchange: string | null;
  /** Fixed pixel height override; without it the container is responsive
   *  (~360px on mobile, 460px from sm up). */
  height?: number;
}

// TradingView resolves bare tickers, but an explicit exchange prefix avoids
// ambiguity for dual-listed names where we know the venue.
function tvSymbol(ticker: string, exchange: string | null): string {
  const ex = (exchange ?? "").toUpperCase();
  if (ex.includes("NASDAQ")) return `NASDAQ:${ticker}`;
  if (ex.includes("NYSE") || ex.includes("NEW YORK")) return `NYSE:${ticker}`;
  return ticker;
}

export default function TradingViewChart({
  ticker,
  exchange,
  height,
}: TradingViewChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { theme } = useTheme();

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const widget = document.createElement("div");
    widget.className = "tradingview-widget-container__widget";
    widget.style.height = "100%";
    widget.style.width = "100%";

    const script = document.createElement("script");
    script.src =
      "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    script.type = "text/javascript";
    script.async = true;
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol: tvSymbol(ticker, exchange),
      interval: "D",
      timezone: "Etc/UTC",
      theme,
      style: "1",
      locale: "en",
      hide_top_toolbar: false,
      hide_legend: false,
      allow_symbol_change: false,
      save_image: false,
      support_host: "https://www.tradingview.com",
    });

    container.appendChild(widget);
    container.appendChild(script);

    return () => {
      container.innerHTML = "";
    };
  }, [ticker, exchange, theme]);

  // The embed script overwrites the .tradingview-widget-container element's
  // inline style with height:100%, so the height must live on an outer
  // wrapper the script never touches. Default is responsive: full card
  // width, ~360px tall on mobile, 460px from sm up.
  return (
    <div
      className={`w-full overflow-hidden rounded-lg border border-line bg-surface ${
        height === undefined ? "h-[360px] sm:h-[460px]" : ""
      }`}
      style={height !== undefined ? { height } : undefined}
    >
      <div
        className="tradingview-widget-container"
        ref={containerRef}
        style={{ height: "100%", width: "100%" }}
      />
    </div>
  );
}
