"use client";

// Shared Recharts theming (DESIGN.md "Charts"). Recharts writes fill/stroke
// as SVG presentation attributes, where CSS var() does not resolve, so the
// live token values are read from the document with getComputedStyle.
// useChartTheme() re-reads them whenever the <html> class changes (theme
// toggle), so every chart renders correctly in both themes.

import { useEffect, useState, type CSSProperties } from "react";

export interface ChartTheme {
  /** Categorical series palette: brand, accent, ink-muted (warn as a 4th). */
  series: string[];
  brand: string;
  accent: string;
  inkMuted: string;
  negative: string;
  /** Gridline color (--line). */
  grid: string;
  /** Axis stroke / tick color (--ink-muted); axes render at 11px. */
  axis: string;
  /** Reference / marker line color. */
  reference: string;
  /** Hover cursor fill for bar charts. */
  cursorFill: string;
  /** Shared tooltip style: surface bg, line-strong border, 10px radius. */
  tooltip: {
    contentStyle: CSSProperties;
    labelStyle: CSSProperties;
  };
  /** Series animation (DESIGN.md Motion): 400ms ease-out, disabled under
   *  prefers-reduced-motion. Spread onto every Bar/Line series element. */
  animation: {
    isAnimationActive: boolean;
    animationDuration: number;
    animationEasing: "ease-out";
  };
}

export const CHART_AXIS_FONT_SIZE = 11;

// Light-theme fallbacks for the first (pre-mount) render; the mounted
// re-read supplies the live values. These literals are the one sanctioned
// place for hex outside globals.css.
const FALLBACK_VARS: Record<string, string> = {
  "--brand": "#1e3a5f",
  "--accent": "#0d9488",
  "--ink": "#0f172a",
  "--ink-muted": "#5b6779",
  "--negative": "#b91c1c",
  "--warn": "#b45309",
  "--line": "rgba(15, 23, 42, 0.08)",
  "--line-strong": "rgba(15, 23, 42, 0.16)",
  "--surface": "#ffffff",
  "--brand-soft": "rgba(30, 58, 95, 0.07)",
  "--shadow-card": "0 1px 2px rgba(15, 23, 42, 0.04)",
};

function buildTheme(
  read: (name: string) => string,
  reducedMotion = false,
): ChartTheme {
  const brand = read("--brand");
  const accent = read("--accent");
  const inkMuted = read("--ink-muted");
  return {
    series: [brand, accent, inkMuted, read("--warn")],
    brand,
    accent,
    inkMuted,
    negative: read("--negative"),
    grid: read("--line"),
    axis: inkMuted,
    reference: inkMuted,
    cursorFill: read("--brand-soft"),
    tooltip: {
      contentStyle: {
        backgroundColor: read("--surface"),
        border: `1px solid ${read("--line-strong")}`,
        borderRadius: 10,
        boxShadow: read("--shadow-card"),
        fontSize: 12,
        color: read("--ink"),
      },
      labelStyle: { color: read("--ink"), fontWeight: 500 },
    },
    animation: {
      isAnimationActive: !reducedMotion,
      animationDuration: 400,
      animationEasing: "ease-out",
    },
  };
}

const FALLBACK_THEME = buildTheme((name) => FALLBACK_VARS[name] ?? "");

export function readChartTheme(): ChartTheme {
  const styles = getComputedStyle(document.documentElement);
  const reducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)",
  ).matches;
  return buildTheme((name) => {
    const value = styles.getPropertyValue(name).trim();
    return value !== "" ? value : (FALLBACK_VARS[name] ?? "");
  }, reducedMotion);
}

/**
 * Live chart theme: reads the CSS variables on mount and re-reads them when
 * the html class changes (MutationObserver), covering the theme toggle and
 * OS preference changes alike.
 */
export function useChartTheme(): ChartTheme {
  const [theme, setTheme] = useState<ChartTheme>(FALLBACK_THEME);

  useEffect(() => {
    const update = () => setTheme(readChartTheme());
    update();
    const observer = new MutationObserver(update);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });
    // Re-read when the reduced-motion preference changes so the animation
    // flag tracks the OS setting live.
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    media.addEventListener("change", update);
    return () => {
      observer.disconnect();
      media.removeEventListener("change", update);
    };
  }, []);

  return theme;
}
