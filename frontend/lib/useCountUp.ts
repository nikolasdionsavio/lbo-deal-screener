"use client";

// Count-up for hero figures (PRODUCT register: motion conveys state — the
// number arriving). rAF from 0 to the final value over ~450ms ease-out, once
// on the component's first mount only; later value changes (e.g. an LBO
// recompute) render directly with no animation. Skipped for null values and
// under prefers-reduced-motion. The caller passes one of the existing fmt
// helpers so every animated frame carries the exact resting format.
//
// Applied ONLY to the dashboard Snapshot band tiles and the LBO IRR/MoM
// hero cards (BUILD: motion pass) — nothing else counts up.

import { useEffect, useRef, useState } from "react";

const DURATION_MS = 450;

function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3);
}

export function useCountUp(
  value: number | null,
  format: (value: number | null) => string,
): string {
  // Initial frame: the final value on the server / under reduced motion
  // (no flash of a wrong number), zero when the count-up will run.
  const [animated, setAnimated] = useState<number | null>(() => {
    if (value === null || !Number.isFinite(value)) return value;
    if (typeof window === "undefined") return value;
    // Skip the count-up (show the real value at once) under reduced motion or
    // when the tab is hidden at mount — a backgrounded tab pauses rAF, which
    // would otherwise freeze the figure mid-climb until the tab is focused.
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return value;
    if (typeof document !== "undefined" && document.hidden) return value;
    return 0;
  });
  const ranRef = useRef(false);

  useEffect(() => {
    if (ranRef.current) {
      // Post-mount updates (recomputes) render directly.
      setAnimated(value);
      return;
    }
    ranRef.current = true;
    if (
      value === null ||
      !Number.isFinite(value) ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
      document.hidden // backgrounded tab pauses rAF; show the value directly
    ) {
      setAnimated(value);
      return;
    }
    let completed = false;
    let raf = 0;
    // The clock starts at the first frame the browser can actually paint,
    // not at effect time — page-mount work can block rAF long enough to
    // swallow the whole animation otherwise.
    let start: number | null = null;
    const tick = (now: number) => {
      if (start === null) start = now;
      const t = Math.min(1, (now - start) / DURATION_MS);
      setAnimated(value * easeOutCubic(t));
      if (t < 1) raf = requestAnimationFrame(tick);
      else completed = true;
    };
    raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      // React StrictMode (dev) runs mount effects twice; if this run was
      // cancelled before finishing, re-arm so the rerun still animates.
      if (!completed) ranRef.current = false;
    };
  }, [value]);

  return format(animated);
}
