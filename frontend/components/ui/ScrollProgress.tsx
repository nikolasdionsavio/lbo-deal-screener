"use client";

// Reading progress for the long documents: methodology, changelog, what's new.
//
// It is an indicator, not an effect. On a page that runs to several screens of
// prose the useful question is "how much of this is left", and a scrollbar
// answers that badly on a trackpad where it is hidden until you move.
//
// Composited: it is a full-width bar scaled on the X axis, so progress costs
// one transform per frame and never touches layout. It reads scroll position
// inside a rAF rather than in the scroll handler itself, so a fast flick
// coalesces into one write per frame instead of one per event.

import { useEffect, useRef } from "react";

export default function ScrollProgress() {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    let frame = 0;
    let last = -1;

    const measure = () => {
      frame = 0;
      const doc = document.documentElement;
      const span = doc.scrollHeight - window.innerHeight;
      // A page that does not scroll has no progress to report.
      const p = span > 24 ? Math.min(1, Math.max(0, window.scrollY / span)) : 0;
      const rounded = Math.round(p * 1000) / 1000;
      if (rounded === last) return;
      last = rounded;
      el.style.transform = `scaleX(${rounded})`;
      el.style.opacity = span > 24 ? "1" : "0";
    };

    const onScroll = () => {
      if (frame === 0) frame = requestAnimationFrame(measure);
    };

    measure();
    window.addEventListener("scroll", onScroll, { passive: true });
    const observer = new ResizeObserver(onScroll);
    observer.observe(document.documentElement);
    return () => {
      window.removeEventListener("scroll", onScroll);
      observer.disconnect();
      if (frame !== 0) cancelAnimationFrame(frame);
    };
  }, []);

  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-x-0 top-0 z-40 h-[2px]"
    >
      <div
        ref={ref}
        className="h-full origin-left bg-brand"
        style={{ transform: "scaleX(0)" }}
      />
    </div>
  );
}
