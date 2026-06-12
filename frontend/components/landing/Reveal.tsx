"use client";

// Landing-only scroll reveal (DESIGN.md Aesthetic v2 Motion): one gentle
// fade + 6px rise per section on first intersection, 280ms ease-out.
// Content is visible by default — the hidden state (.reveal-init) is only
// added from JS and never under prefers-reduced-motion, so no-JS and
// reduced-motion users always see static, visible content.

import { useEffect, useRef, type ReactNode } from "react";

interface RevealProps {
  children: ReactNode;
  className?: string;
}

export default function Reveal({ children, className = "" }: RevealProps) {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (el === null) return;
    if (typeof IntersectionObserver === "undefined") return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    el.classList.add("reveal-init");
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          el.classList.add("reveal-in");
          observer.disconnect();
        }
      },
      { threshold: 0.1 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  );
}
