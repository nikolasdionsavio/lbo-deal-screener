"use client";

// Motion runtime.
//
// Three rules this file exists to enforce.
//
// 1. One observer and one animation frame loop for the whole page. A reveal
//    hook per element would mean an IntersectionObserver per element and a rAF
//    per pointer effect; on a page with fifty revealed items that is fifty
//    observers competing for the same main thread. Everything here shares one
//    of each.
//
// 2. Content is visible until JS decides otherwise. Nothing is authored in a
//    hidden state. The hooks add the hidden attribute themselves, after mount,
//    and never under prefers-reduced-motion. A crawler, a no-JS reader, a
//    headless screenshot and a reduced-motion visitor all get the finished
//    page.
//
// 3. Pointer effects write transforms through a spring integrated per frame,
//    not through CSS transitions. A transition restarts on every pointer move
//    and produces lag; integrating velocity gives the element momentum, so it
//    keeps travelling briefly after the pointer leaves, which is what makes it
//    feel physical rather than attached.

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

/* ------------------------------------------------------------------------- */
/* Environment                                                                */
/* ------------------------------------------------------------------------- */

export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return true;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** Pointer effects are meaningless without a pointer that hovers. */
export function hasFinePointer(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(hover: hover) and (pointer: fine)").matches;
}

/* ------------------------------------------------------------------------- */
/* Shared frame loop                                                          */
/* ------------------------------------------------------------------------- */

type FrameFn = (dt: number) => void;
const frameSubs = new Set<FrameFn>();
let frameHandle = 0;
let lastT = 0;

function tick(t: number) {
  // Clamped so a backgrounded tab returning does not integrate one enormous
  // step and fling every spring across the screen.
  const dt = Math.min((t - lastT) / 1000, 1 / 30);
  lastT = t;
  for (const fn of frameSubs) fn(dt);
  frameHandle = frameSubs.size > 0 ? requestAnimationFrame(tick) : 0;
}

function subscribeFrame(fn: FrameFn): () => void {
  frameSubs.add(fn);
  if (frameHandle === 0) {
    lastT = performance.now();
    frameHandle = requestAnimationFrame(tick);
  }
  return () => {
    frameSubs.delete(fn);
    if (frameSubs.size === 0 && frameHandle !== 0) {
      cancelAnimationFrame(frameHandle);
      frameHandle = 0;
    }
  };
}

/* ------------------------------------------------------------------------- */
/* Spring integrator (for pointer-driven motion)                              */
/* ------------------------------------------------------------------------- */

export interface SpringConfig {
  stiffness: number;
  damping: number;
  mass: number;
}

/** Same physical roles as the CSS presets in motion.css, for JS-driven values. */
export const SPRING: Record<string, SpringConfig> = {
  tight: { stiffness: 520, damping: 30, mass: 0.7 },
  responsive: { stiffness: 320, damping: 30, mass: 1 },
  soft: { stiffness: 190, damping: 30, mass: 1.4 },
  heavy: { stiffness: 330, damping: 52, mass: 2.2 },
  elastic: { stiffness: 420, damping: 21, mass: 1 },
};

class Spring {
  value = 0;
  target = 0;
  velocity = 0;
  constructor(private cfg: SpringConfig) {}
  step(dt: number): boolean {
    const { stiffness, damping, mass } = this.cfg;
    // Semi-implicit Euler, substepped so a long frame cannot go unstable.
    const steps = Math.max(1, Math.ceil(dt / (1 / 120)));
    const h = dt / steps;
    for (let i = 0; i < steps; i++) {
      const f =
        -stiffness * (this.value - this.target) - damping * this.velocity;
      this.velocity += (f / mass) * h;
      this.value += this.velocity * h;
    }
    const atRest =
      Math.abs(this.velocity) < 0.02 &&
      Math.abs(this.value - this.target) < 0.02;
    if (atRest) {
      this.value = this.target;
      this.velocity = 0;
    }
    return !atRest;
  }
}

/* ------------------------------------------------------------------------- */
/* Reveal                                                                     */
/* ------------------------------------------------------------------------- */

let revealObserver: IntersectionObserver | null = null;
let watchdog = 0;

function reveal(el: HTMLElement) {
  el.classList.remove("m-off");
}

/**
 * Last resort.
 *
 * An IntersectionObserver does not fire in a headless renderer, and rAF does
 * not run in a background tab. Either one leaves an element that JS has
 * already hidden with nothing to un-hide it, and the section ships blank. That
 * is not a hypothetical: the first build of this system rendered a completely
 * empty homepage in exactly that situation.
 *
 * So a timer, which fires in all of those cases, sweeps up anything still
 * hidden that is anywhere near the viewport. Genuine below-the-fold reveals
 * are untouched, because they are nowhere near it.
 */
function armWatchdog() {
  // Debounced, not one-shot. SplitLines mounts its line masks only after a
  // measuring pass, so they register AFTER the first elements on the page do.
  // A single timer armed by the first registration would sweep before those
  // masks existed and never run again, leaving exactly the elements that need
  // it most uncovered. Re-arming means the sweep always happens 1.6s after the
  // last thing registered.
  if (watchdog !== 0) clearTimeout(watchdog);
  watchdog = window.setTimeout(() => {
    watchdog = 0;
    for (const el of Array.from(document.querySelectorAll<HTMLElement>(".m-off"))) {
      const r = el.getBoundingClientRect();
      if (r.top < window.innerHeight * 1.5 && r.bottom > -window.innerHeight * 0.5) {
        reveal(el);
      }
    }
  }, 1600);
}

function getRevealObserver(): IntersectionObserver {
  if (revealObserver) return revealObserver;
  revealObserver = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const el = entry.target as HTMLElement;
        reveal(el);
        // One shot. A section that re-animates every time it scrolls back into
        // view turns a page into a slideshow.
        revealObserver?.unobserve(el);
      }
    },
    // Fires slightly before the element reaches the fold, so the motion is
    // finishing as it becomes comfortably readable rather than starting then.
    { rootMargin: "0px 0px -12% 0px", threshold: 0.01 },
  );
  return revealObserver;
}

export type RevealVariant =
  "rule" | "wipe" | "rise" | "lift" | "settle" | "line";

/**
 * Opts an element into the reveal vocabulary in motion.css.
 * The hidden state is applied here, after mount, so it can never strand
 * content for a reader whose JS or motion preference says otherwise.
 */
export function useReveal<T extends HTMLElement>(
  variant: RevealVariant,
  {
    index = 0,
    step = 60,
    lead = 0,
  }: { index?: number; step?: number; lead?: number } = {},
) {
  const ref = useRef<T | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || prefersReducedMotion()) return;

    // Delay is resolved here rather than in a CSS calc(). The cap belongs in
    // one place and JS is the honest place for it: a long list must not leave
    // the last item waiting three seconds for its turn.
    const delay = Math.min(index * step, 480);
    el.style.setProperty("--m-delay", `${delay}ms`);
    if (lead) el.style.setProperty("--m-lead", `${lead}ms`);
    el.dataset.m = variant;
    el.classList.add("m-off");

    // Anything already on screen is an ENTRANCE, not a scroll reveal, and is
    // played from the next frame rather than waiting on an observer that has
    // nothing left to observe. Two frames: one for the browser to record the
    // hidden state, one for the transition to have somewhere to start from.
    const rect = el.getBoundingClientRect();
    const onScreen = rect.top < window.innerHeight && rect.bottom > 0;

    let raf1 = 0;
    let raf2 = 0;
    let safety = 0;
    const observer = getRevealObserver();

    if (onScreen) {
      raf1 = requestAnimationFrame(() => {
        raf2 = requestAnimationFrame(() => reveal(el));
      });
      // requestAnimationFrame does not run while the tab is in the background,
      // so on its own it can leave an entrance stranded until the tab is
      // focused. A timer does run there. Whichever fires first wins; removing
      // the class twice costs nothing.
      safety = window.setTimeout(() => reveal(el), 400);
    } else {
      observer.observe(el);
    }
    armWatchdog();

    return () => {
      cancelAnimationFrame(raf1);
      cancelAnimationFrame(raf2);
      clearTimeout(safety);
      observer.unobserve(el);
      reveal(el);
    };
  }, [variant, index, step, lead]);

  return ref;
}

export function Reveal({
  as: Tag = "div",
  variant = "rise",
  index,
  step,
  lead,
  className = "",
  children,
}: {
  as?: "div" | "section" | "li" | "p" | "span" | "figure";
  variant?: RevealVariant;
  index?: number;
  step?: number;
  lead?: number;
  className?: string;
  children: ReactNode;
}) {
  const ref = useReveal<HTMLDivElement>(variant, { index, step, lead });
  const Component = Tag as "div";
  return (
    <Component ref={ref} className={className}>
      {children}
    </Component>
  );
}

/* ------------------------------------------------------------------------- */
/* Line-masked headings                                                       */
/* ------------------------------------------------------------------------- */

/**
 * Splits a heading into its rendered LINES and rides each up inside its own
 * mask.
 *
 * Splitting by word is easy and looks wrong: words arrive at ragged times
 * across a line and the eye reads it as noise. Real lines have to be measured
 * after layout, because where a line breaks depends on the font, the width and
 * the copy. Words are rendered as spans, grouped by their offsetTop, and only
 * then wrapped in masks.
 *
 * Re-measures on resize, because a line break at 1440px is not the line break
 * at 375px.
 */
export function SplitLines({
  text,
  className = "",
  lead = 0,
  step = 90,
}: {
  text: string;
  className?: string;
  lead?: number;
  step?: number;
}) {
  const ref = useRef<HTMLSpanElement | null>(null);
  const [lines, setLines] = useState<string[] | null>(null);
  const words = useMemo(() => text.split(/\s+/).filter(Boolean), [text]);

  const measure = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    const spans = Array.from(el.querySelectorAll<HTMLElement>("[data-w]"));
    if (spans.length === 0) return;
    const grouped: string[] = [];
    let top: number | null = null;
    let current: string[] = [];
    for (const span of spans) {
      const y = Math.round(span.offsetTop);
      if (top === null || Math.abs(y - top) > 2) {
        if (current.length) grouped.push(current.join(" "));
        current = [];
        top = y;
      }
      current.push((span.textContent ?? "").trim());
    }
    if (current.length) grouped.push(current.join(" "));
    setLines(grouped);
  }, []);

  useEffect(() => {
    if (prefersReducedMotion()) return;
    measure();
    const el = ref.current;
    if (!el) return;
    // Re-measure on width change only; height changes are our own doing.
    let lastW = el.getBoundingClientRect().width;
    const observer = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width ?? lastW;
      if (Math.abs(w - lastW) < 1) return;
      lastW = w;
      setLines(null);
      requestAnimationFrame(measure);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [measure, text]);

  // Measuring pass, and the permanent output for reduced motion / no JS.
  if (lines === null) {
    return (
      <span ref={ref} className={className}>
        {words.map((w, i) => (
          <span data-w key={i}>
            {w}
            {i < words.length - 1 ? " " : ""}
          </span>
        ))}
      </span>
    );
  }

  return (
    <span ref={ref} className={className}>
      {/* One copy of the text, not two. An sr-only duplicate beside an
          aria-hidden visual copy gives the right accessible name but puts the
          heading in the DOM twice, which a crawler reads as written. Instead
          each line keeps a trailing space: invisible inside a block-level
          mask, and enough for the lines to concatenate into the real sentence
          rather than "Companyresearch youcan check". */}
      {lines.map((line, i) => (
        <MaskedLine key={`${i}-${line}`} index={i} lead={lead} step={step}>
          {line}{" "}
        </MaskedLine>
      ))}
    </span>
  );
}

function MaskedLine({
  children,
  index,
  lead,
  step,
}: {
  children: ReactNode;
  index: number;
  lead: number;
  step: number;
}) {
  const ref = useReveal<HTMLSpanElement>("line", { index, step, lead });
  return (
    <span className="m-line-mask">
      <span ref={ref} className="block">
        {children}
      </span>
    </span>
  );
}

/* ------------------------------------------------------------------------- */
/* Magnetic pointer attraction                                                */
/* ------------------------------------------------------------------------- */

/**
 * Pulls an element toward the pointer while the pointer is near it, then
 * springs home when it leaves.
 *
 * Two things keep this from being a gimmick. The pull is capped well inside
 * the element's own bounds, so the hit area never runs away from the cursor.
 * And the return is integrated, not transitioned, so the element carries its
 * velocity out of the interaction instead of stopping dead the instant the
 * pointer crosses the boundary.
 */
export function useMagnetic<T extends HTMLElement>({
  strength = 0.32,
  max = 10,
  radius = 1.6,
  spring = "tight",
}: {
  strength?: number;
  max?: number;
  radius?: number;
  spring?: keyof typeof SPRING;
} = {}) {
  const ref = useRef<T | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || prefersReducedMotion() || !hasFinePointer()) return;

    const sx = new Spring(SPRING[spring]);
    const sy = new Spring(SPRING[spring]);
    let unsubscribe: (() => void) | null = null;
    let running = false;

    const start = () => {
      if (running) return;
      running = true;
      unsubscribe = subscribeFrame((dt) => {
        const a = sx.step(dt);
        const b = sy.step(dt);
        el.style.transform = `translate3d(${sx.value.toFixed(2)}px, ${sy.value.toFixed(2)}px, 0)`;
        if (!a && !b) {
          el.style.transform = "";
          unsubscribe?.();
          unsubscribe = null;
          running = false;
        }
      });
    };

    const onMove = (e: PointerEvent) => {
      const r = el.getBoundingClientRect();
      const cx = r.left + r.width / 2;
      const cy = r.top + r.height / 2;
      const dx = e.clientX - cx;
      const dy = e.clientY - cy;
      // Proximity field scaled to the element, so a wide button has a wide
      // field and a small icon has a small one.
      const within =
        Math.abs(dx) < (r.width / 2) * radius &&
        Math.abs(dy) < (r.height / 2) * radius;
      sx.target = within ? Math.max(-max, Math.min(max, dx * strength)) : 0;
      sy.target = within ? Math.max(-max, Math.min(max, dy * strength)) : 0;
      start();
    };

    const onLeave = () => {
      sx.target = 0;
      sy.target = 0;
      start();
    };

    // Listening on the window is what gives attraction BEFORE the pointer
    // arrives; listening on the element could only ever react once it is
    // already inside.
    window.addEventListener("pointermove", onMove, { passive: true });
    el.addEventListener("pointerleave", onLeave);
    return () => {
      window.removeEventListener("pointermove", onMove);
      el.removeEventListener("pointerleave", onLeave);
      unsubscribe?.();
      el.style.transform = "";
    };
  }, [strength, max, radius, spring]);

  return ref;
}

/* ------------------------------------------------------------------------- */
/* Scroll-linked progress                                                     */
/* ------------------------------------------------------------------------- */

/**
 * Writes an element's own scroll progress (0 to 1) into a CSS variable on it,
 * so the styling stays in CSS and this file stays out of the business of
 * deciding what progress looks like.
 *
 * Reads happen once per frame inside the shared loop and writes happen
 * immediately after, so there is no interleaved read/write and therefore no
 * layout thrash. Elements outside the viewport are skipped entirely.
 */
export function useScrollProgress<T extends HTMLElement>({
  varName = "--p",
  from = "enter",
}: { varName?: string; from?: "enter" | "cover" } = {}) {
  const ref = useRef<T | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || prefersReducedMotion()) return;

    let visible = false;
    const io = new IntersectionObserver(
      ([e]) => {
        visible = e.isIntersecting;
      },
      { rootMargin: "20% 0px 20% 0px" },
    );
    io.observe(el);

    let last = -1;
    const unsubscribe = subscribeFrame(() => {
      if (!visible) return;
      const r = el.getBoundingClientRect();
      const vh = window.innerHeight;
      const span = from === "cover" ? r.height : r.height + vh;
      const travelled = from === "cover" ? -r.top : vh - r.top;
      const p = Math.max(0, Math.min(1, travelled / Math.max(span, 1)));
      const rounded = Math.round(p * 1000) / 1000;
      if (rounded !== last) {
        last = rounded;
        el.style.setProperty(varName, String(rounded));
      }
    });

    return () => {
      io.disconnect();
      unsubscribe();
    };
  }, [varName, from]);

  return ref;
}

/* ------------------------------------------------------------------------- */
/* Tilt                                                                       */
/* ------------------------------------------------------------------------- */

/** Perspective response for a single hero-weight object. Heavier spring than a
 *  button: a panel this size should not flick. */
export function useTilt<T extends HTMLElement>({
  max = 4,
}: { max?: number } = {}) {
  const ref = useRef<T | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || prefersReducedMotion() || !hasFinePointer()) return;

    const rx = new Spring(SPRING.soft);
    const ry = new Spring(SPRING.soft);
    let unsubscribe: (() => void) | null = null;

    const run = () => {
      if (unsubscribe) return;
      unsubscribe = subscribeFrame((dt) => {
        const a = rx.step(dt);
        const b = ry.step(dt);
        el.style.transform = `perspective(1400px) rotateX(${rx.value.toFixed(3)}deg) rotateY(${ry.value.toFixed(3)}deg)`;
        if (!a && !b) {
          el.style.transform = "";
          unsubscribe?.();
          unsubscribe = null;
        }
      });
    };

    const onMove = (e: PointerEvent) => {
      const r = el.getBoundingClientRect();
      const px = (e.clientX - r.left) / r.width - 0.5;
      const py = (e.clientY - r.top) / r.height - 0.5;
      ry.target = px * max * 2;
      rx.target = -py * max * 2;
      run();
    };
    const onLeave = () => {
      rx.target = 0;
      ry.target = 0;
      run();
    };

    el.addEventListener("pointermove", onMove, { passive: true });
    el.addEventListener("pointerleave", onLeave);
    return () => {
      el.removeEventListener("pointermove", onMove);
      el.removeEventListener("pointerleave", onLeave);
      unsubscribe?.();
      el.style.transform = "";
    };
  }, [max]);

  return ref;
}
