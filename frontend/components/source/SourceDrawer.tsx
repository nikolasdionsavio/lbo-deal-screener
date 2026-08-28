"use client";

// The source record drawer (DESIGN.md: "a signature visual element ... an audit
// note attached to the model"). A right-side panel with a narrow label column
// and a wider value column, sections separated by rules, not cards. It shows
// only what is truthfully known: classification, period, currency, and a real
// link to the filing on SEC EDGAR. It never invents a line-item tag or filing
// date the API does not expose, and it is never called an "AI explanation".

import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

/** Matches the exit animation in globals.css (.drawer-right[data-closing]). */
const EXIT_MS = 160;

export type SourceClass = "filed" | "calculated" | "assumption" | "missing";

export interface SourceRecord {
  /** Metric / line-item name. */
  metric: string;
  /** The value as displayed in the table (already formatted). */
  displayValue: string;
  classification: SourceClass;
  /** e.g. "FY2025 · period ended 27 Sep 2025". */
  period?: string;
  /** Reporting currency + scale note, e.g. "USD, reported in full". */
  unit?: string;
  /** Which statement / page it came from. */
  statement?: string;
  /** Present for calculated values. */
  formula?: string;
  /** Present for calculated values: the inputs and their values. */
  inputs?: { label: string; value: string }[];
  /** Filing description, e.g. "Annual report (10-K / 20-F)". */
  filing?: string;
  /** A real link to the source (SEC EDGAR filing list for the issuer). */
  sourceUrl?: string;
  sourceLabel?: string;
  /** Any honest caveat about what the record can and cannot show. */
  note?: string;
}

const CLASS_LABEL: Record<SourceClass, string> = {
  filed: "Filed — reported in the company's filing",
  calculated: "Calculated — derived from filed figures",
  assumption: "Assumption — a model input you can edit",
  missing: "Not available",
};

const CLASS_MARK: Record<SourceClass, string> = {
  filed: "F",
  calculated: "C",
  assumption: "A",
  missing: "M",
};

const CLASS_MARK_STYLE: Record<SourceClass, string> = {
  filed: "border-line-strong text-ink-secondary",
  calculated: "border-line-strong text-ink-secondary",
  assumption: "border-assumption text-assumption",
  missing: "border-line-strong text-ink-muted",
};

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[7.5rem_1fr] gap-3 border-t border-line py-2.5">
      <dt className="font-mono text-[11px] uppercase tracking-[0.02em] text-ink-muted">
        {label}
      </dt>
      <dd className="text-[0.8125rem] text-ink">{children}</dd>
    </div>
  );
}

export default function SourceDrawer({
  record,
  onClose,
}: {
  record: SourceRecord | null;
  onClose: () => void;
}) {
  // The record is held locally so the panel can finish leaving after the
  // caller has already cleared it. Without this it slides in and then simply
  // disappears, which reads as a glitch rather than a dismissal.
  const [shown, setShown] = useState<SourceRecord | null>(record);
  const [closing, setClosing] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    if (record) {
      setShown(record);
      setClosing(false);
      return;
    }
    if (!shown) return;
    // Reduced motion has no exit travel to wait for, so drop it immediately.
    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      setShown(null);
      return;
    }
    setClosing(true);
    timer.current = setTimeout(() => {
      setShown(null);
      setClosing(false);
    }, EXIT_MS);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [record, shown]);

  const requestClose = useCallback(() => onClose(), [onClose]);

  useEffect(() => {
    if (!shown) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") requestClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [shown, requestClose]);

  if (typeof document === "undefined" || !shown) return null;
  const drawerRecord = shown;

  return createPortal(
    <div className="fixed inset-0 z-[80]" role="dialog" aria-modal="true" aria-label="Source record">
      <button
        type="button"
        aria-label="Close source record"
        onClick={requestClose}
        data-closing={closing}
        className="drawer-scrim absolute inset-0 bg-ink/20"
      />
      <aside
        data-closing={closing}
        className="glass-thick drawer-right absolute right-0 top-0 flex h-full w-full max-w-[24rem] flex-col border-l border-line-strong">
        <div className="flex items-center justify-between border-b border-line px-5 py-3">
          <span className="font-mono text-[11px] uppercase tracking-[0.04em] text-ink-muted">
            Source record
          </span>
          <button
            type="button"
            onClick={requestClose}
            aria-label="Close"
            className="rounded-[3px] p-1 text-ink-muted transition-colors hover:text-ink focus-visible:ring-2 focus-visible:ring-accent"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
              <path d="m4 4 8 8M12 4l-8 8" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          <div className="flex items-baseline gap-2">
            <span
              className={`inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-[2px] border font-mono text-[10px] ${CLASS_MARK_STYLE[drawerRecord.classification]}`}
              aria-hidden="true"
            >
              {CLASS_MARK[drawerRecord.classification]}
            </span>
            <h2 className="text-[0.9375rem] font-semibold text-ink">
              {drawerRecord.metric}
            </h2>
          </div>
          <p className="mt-1 font-mono text-[1.375rem] tabular-nums text-ink">
            {drawerRecord.displayValue}
          </p>

          <dl className="mt-4">
            <Row label="Classification">{CLASS_LABEL[drawerRecord.classification]}</Row>
            {drawerRecord.period && <Row label="Period">{drawerRecord.period}</Row>}
            {drawerRecord.unit && <Row label="Unit">{drawerRecord.unit}</Row>}
            {drawerRecord.statement && <Row label="Statement">{drawerRecord.statement}</Row>}
            {drawerRecord.filing && <Row label="Filing">{drawerRecord.filing}</Row>}
            {drawerRecord.formula && (
              <Row label="Formula">
                <span className="font-mono text-[0.75rem] text-ink-secondary">
                  {drawerRecord.formula}
                </span>
              </Row>
            )}
            {drawerRecord.inputs && drawerRecord.inputs.length > 0 && (
              <Row label="Inputs">
                <ul className="space-y-1">
                  {drawerRecord.inputs.map((inp, i) => (
                    <li key={i} className="flex justify-between gap-3 font-mono text-[0.75rem]">
                      <span className="text-ink-secondary">{inp.label}</span>
                      <span className="tabular-nums text-ink">{inp.value}</span>
                    </li>
                  ))}
                </ul>
              </Row>
            )}
            {drawerRecord.sourceUrl && (
              <Row label="Source">
                <a
                  href={drawerRecord.sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-link underline decoration-line-strong underline-offset-2 transition-colors hover:text-link-hover hover:decoration-link"
                >
                  {drawerRecord.sourceLabel ?? "Open filing on SEC EDGAR"}
                </a>
              </Row>
            )}
          </dl>

          {drawerRecord.note && (
            <p className="mt-4 border-t border-line pt-3 text-[0.75rem] leading-snug text-ink-muted">
              {drawerRecord.note}
            </p>
          )}
        </div>
      </aside>
    </div>,
    document.body,
  );
}
