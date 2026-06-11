"use client";

// Official TradingView Advanced Chart embed widget. The widget supplies its
// own price data and carries TradingView's required attribution; it is purely
// presentational and independent of the app's data providers.

import { useEffect, useRef } from "react";

interface TradingViewChartProps {
  ticker: string;
  exchange: string | null;
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
  height = 460,
}: TradingViewChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);

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
      theme: "light",
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
  }, [ticker, exchange]);

  // The embed script overwrites the .tradingview-widget-container element's
  // inline style with height:100%, so the fixed height must live on an outer
  // wrapper the script never touches.
  return (
    <div
      className="overflow-hidden rounded-lg border border-slate-200 bg-surface"
      style={{ height }}
    >
      <div
        className="tradingview-widget-container"
        ref={containerRef}
        style={{ height: "100%", width: "100%" }}
      />
    </div>
  );
}
