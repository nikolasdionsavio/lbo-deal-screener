"use client";

// Generic wrapper around TradingView's official embed widgets (screener, market
// overview, stock heatmap, economic calendar, technical analysis). Each widget
// supplies its own market data and carries TradingView's required attribution;
// it is purely presentational and independent of the app's data providers.
//
// The widget is torn down and re-created whenever the app theme changes so its
// colour theme always matches. Most widgets key theme on `colorTheme`; the
// advanced chart uses `theme` — hence the configurable themeKey.

import { useEffect, useRef } from "react";
import { useTheme } from "@/lib/theme";

interface TradingViewWidgetProps {
  /** Embed script filename, e.g. "embed-widget-stock-heatmap.js". */
  scriptSrc: string;
  /** Widget config, minus the theme key (injected from the active theme). */
  config: Record<string, unknown>;
  /** Theme config key: "colorTheme" for most widgets, "theme" for the chart. */
  themeKey?: "colorTheme" | "theme";
  /** Height utility classes on the outer wrapper the embed script never touches. */
  className?: string;
}

/** Map a bare ticker + exchange to a TradingView symbol; prefixes the venue
 *  when known so dual-listed names resolve unambiguously. */
export function tvSymbol(ticker: string, exchange: string | null): string {
  const ex = (exchange ?? "").toUpperCase();
  if (ex.includes("NASDAQ")) return `NASDAQ:${ticker}`;
  if (ex.includes("NYSE") || ex.includes("NEW YORK")) return `NYSE:${ticker}`;
  return ticker;
}

export default function TradingViewWidget({
  scriptSrc,
  config,
  themeKey = "colorTheme",
  className,
}: TradingViewWidgetProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { theme } = useTheme();
  // Re-run when the config content changes, not just its object identity.
  const configKey = JSON.stringify(config);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const widget = document.createElement("div");
    widget.className = "tradingview-widget-container__widget";
    widget.style.height = "100%";
    widget.style.width = "100%";

    const script = document.createElement("script");
    script.src = `https://s3.tradingview.com/external-embedding/${scriptSrc}`;
    script.type = "text/javascript";
    script.async = true;
    script.innerHTML = JSON.stringify({
      ...config,
      [themeKey]: theme,
      locale: "en",
      support_host: "https://www.tradingview.com",
    });

    container.appendChild(widget);
    container.appendChild(script);

    return () => {
      container.innerHTML = "";
    };
  }, [scriptSrc, configKey, themeKey, theme]);

  return (
    <div
      className={`w-full overflow-hidden rounded-lg border border-line bg-surface ${
        className ?? "h-[420px]"
      }`}
    >
      <div
        className="tradingview-widget-container"
        ref={containerRef}
        style={{ height: "100%", width: "100%" }}
      />
    </div>
  );
}
