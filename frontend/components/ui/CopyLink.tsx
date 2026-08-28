"use client";

// Copy the current URL.
//
// The deal screen's headline feature is that every screen IS a link: the
// filters live in the address bar so a shortlist can be sent to someone. There
// was no way to copy that link except selecting the address bar, which is the
// one part of the feature the page never mentioned.
//
// The motion here is a state morph, not decoration. The label and the icon
// cross-fade in place while the button holds its width, so the control does
// not resize under the pointer and the row of buttons beside it does not
// reflow. Width is held by rendering both labels stacked and letting the
// longer one set the box.

import { useCallback, useEffect, useRef, useState } from "react";

type State = "idle" | "copied" | "failed";

export default function CopyLink({
  label = "Copy link",
  className = "",
}: {
  label?: string;
  className?: string;
}) {
  const [state, setState] = useState<State>("idle");
  const timer = useRef<number>(0);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  const copy = useCallback(async () => {
    const url = window.location.href;
    try {
      await navigator.clipboard.writeText(url);
      setState("copied");
    } catch {
      // Clipboard access is refused outside a secure context and in some
      // embedded viewers. Say so rather than showing a success that did not
      // happen.
      setState("failed");
    }
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setState("idle"), 2200);
  }, []);

  const message =
    state === "copied" ? "Copied" : state === "failed" ? "Press Cmd+C" : label;

  return (
    <button
      type="button"
      onClick={copy}
      // The live region announces the outcome; without it the change is
      // purely visual and a screen reader user gets no confirmation.
      aria-live="polite"
      className={`btn pressable inline-flex items-center gap-2 border border-line-strong px-2.5 py-1.5 text-[0.8125rem] font-medium text-ink-secondary hover:border-accent hover:text-ink ${className}`}
    >
      <span aria-hidden className="copy-glyph relative h-3.5 w-3.5 shrink-0">
        <svg
          viewBox="0 0 14 14"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="copy-glyph-link absolute inset-0"
          data-on={state === "idle"}
        >
          <rect x="1.75" y="4.25" width="8" height="8" rx="1" />
          <path d="M4.25 4.25v-1.5a1 1 0 0 1 1-1h7a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1h-1.5" />
        </svg>
        <svg
          viewBox="0 0 14 14"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.75"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="copy-glyph-tick absolute inset-0"
          data-on={state !== "idle"}
        >
          <path d="M2.5 7.5 5.75 10.75 11.5 3.5" />
        </svg>
      </span>
      {/* Both labels occupy the box so the button cannot change width when the
          text changes; only the visible one is readable. */}
      <span className="grid">
        <span
          className="col-start-1 row-start-1 whitespace-nowrap"
          style={{ visibility: "hidden" }}
          aria-hidden
        >
          {label.length >= message.length ? label : message}
        </span>
        <span className="col-start-1 row-start-1 whitespace-nowrap">
          {message}
        </span>
      </span>
    </button>
  );
}
