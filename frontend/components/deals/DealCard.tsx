"use client";

// One saved deal: ticker (links to the company dashboard), score and rating,
// dates, saved LBO assumptions summary, an expandable embedded memo snapshot
// (collapsed by default), and delete with inline confirmation.

import Link from "next/link";
import { useState } from "react";
import MemoRenderer from "@/components/memo/MemoRenderer";
import Card from "@/components/ui/Card";
import RatingBadge from "@/components/ui/RatingBadge";
import { ApiError, deleteDeal } from "@/lib/api";
import { fmtMultiple } from "@/lib/format";
import type { SavedDeal } from "@/lib/types";

function fmtDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

interface DealCardProps {
  deal: SavedDeal;
  /** Called after a successful delete so the list can refresh. */
  onDeleted: () => void;
}

export default function DealCard({ deal, onDeleted }: DealCardProps) {
  const [memoOpen, setMemoOpen] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const companyHref = `/company/${encodeURIComponent(deal.ticker)}/dashboard`;
  const lboHref = `/company/${encodeURIComponent(deal.ticker)}/lbo`;
  const assumptions = deal.lbo_assumptions;

  const onDelete = async () => {
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteDeal(deal.id);
      onDeleted();
    } catch (err: unknown) {
      setDeleteError(
        err instanceof ApiError
          ? err.detail
          : "Could not delete the deal. Try again.",
      );
      setDeleting(false);
      setConfirming(false);
    }
  };

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <Link
              href={companyHref}
              className="text-base font-semibold text-brand underline-offset-2 hover:underline"
            >
              {deal.ticker}
            </Link>
            <span className="text-sm text-slate-600">{deal.company_name}</span>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Analysed {fmtDate(deal.created_at)} · Updated{" "}
            {fmtDate(deal.updated_at)}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <span
            className="text-lg font-semibold tabular-nums text-ink"
            title="Deal score at the time of saving"
          >
            {deal.score !== null ? `${deal.score.toFixed(1)} / 100` : "—"}
          </span>
          {deal.rating !== null && <RatingBadge rating={deal.rating} />}
        </div>
      </div>

      <div className="mt-4 border-t border-slate-100 pt-3">
        {assumptions !== null ? (
          <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 text-sm text-slate-600">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Saved assumptions
            </span>
            <span className="tabular-nums">
              Entry {fmtMultiple(assumptions.entry_multiple)} · Debt{" "}
              {fmtMultiple(assumptions.debt_multiple)} · Exit{" "}
              {fmtMultiple(assumptions.exit_multiple)} ·{" "}
              {assumptions.holding_period}-year hold
            </span>
            <Link
              href={lboHref}
              className="font-medium text-brand underline-offset-2 hover:underline"
            >
              Open in LBO model
            </Link>
          </div>
        ) : (
          <p className="text-sm text-slate-500">
            No saved LBO assumptions.{" "}
            <Link
              href={lboHref}
              className="font-medium text-brand underline-offset-2 hover:underline"
            >
              Open in LBO model
            </Link>
          </p>
        )}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => setMemoOpen((open) => !open)}
          disabled={deal.memo === null}
          className="rounded border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-default disabled:opacity-50"
        >
          {deal.memo === null
            ? "No memo snapshot"
            : memoOpen
              ? "Hide memo"
              : "View memo"}
        </button>

        {confirming ? (
          <span className="flex items-center gap-2 text-sm">
            <span className="text-slate-600">Delete this saved deal?</span>
            <button
              type="button"
              onClick={onDelete}
              disabled={deleting}
              className="rounded bg-negative px-3 py-1.5 text-sm font-medium text-white hover:bg-negative/90 disabled:opacity-50"
            >
              {deleting ? "Deleting" : "Confirm delete"}
            </button>
            <button
              type="button"
              onClick={() => setConfirming(false)}
              disabled={deleting}
              className="rounded border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              Cancel
            </button>
          </span>
        ) : (
          <button
            type="button"
            onClick={() => setConfirming(true)}
            className="rounded border border-negative/40 px-3 py-1.5 text-sm font-medium text-negative hover:bg-negative/5"
          >
            Delete
          </button>
        )}

        {deleteError !== null && (
          <span className="text-sm text-negative">{deleteError}</span>
        )}
      </div>

      {memoOpen && deal.memo !== null && (
        <div className="mt-4 rounded-lg border border-slate-200 bg-bg p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-ink">
              Memo snapshot — {deal.memo.ticker}
            </h3>
            <span className="text-xs text-slate-500">
              Generated {fmtDate(deal.memo.generated_at)}
            </span>
          </div>
          <div className="mt-4 space-y-6">
            {deal.memo.sections.map((section) =>
              section.key === "data_gaps" ? (
                <section
                  key={section.key}
                  className="rounded-lg border border-warn/30 bg-warn/10 p-4"
                >
                  <h4 className="text-sm font-semibold text-warn">
                    {section.title}
                  </h4>
                  <MemoRenderer
                    content={section.content}
                    className="mt-2 text-warn"
                  />
                </section>
              ) : (
                <section key={section.key}>
                  <h4 className="text-sm font-semibold text-ink">
                    {section.title}
                  </h4>
                  <MemoRenderer content={section.content} className="mt-2" />
                </section>
              ),
            )}
          </div>
          <p className="mt-4 text-xs text-slate-500">{deal.memo.disclaimer}</p>
        </div>
      )}
    </Card>
  );
}
