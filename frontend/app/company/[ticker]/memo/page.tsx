"use client";

// Investment memo page: POST /api/companies/{ticker}/memo with null
// lbo_assumptions (default LBO case), rendered as a clean document in
// section order. The data gaps section is visually distinct (amber).
// Save to watchlist requires auth; 409 is treated as already saved.

import Link from "next/link";
import { useState } from "react";
import { useCompany } from "@/components/company/CompanyContext";
import MemoRenderer from "@/components/memo/MemoRenderer";
import Disclaimer from "@/components/ui/Disclaimer";
import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
import RatingBadge from "@/components/ui/RatingBadge";
import SectionHeader from "@/components/ui/SectionHeader";
import { ApiError, generateMemo, saveDeal } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/hooks";
import type { MemoSection } from "@/lib/types";

function fmtDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

type SaveState =
  | { status: "idle" }
  | { status: "saving" }
  | { status: "saved" }
  | { status: "already" }
  | { status: "error"; message: string };

function SaveToWatchlist({ ticker }: { ticker: string }) {
  const { user, loading } = useAuth();
  const [save, setSave] = useState<SaveState>({ status: "idle" });

  if (loading) return null;

  if (!user) {
    return (
      <p className="text-sm text-ink-muted">
        <Link
          href={`/login?next=${encodeURIComponent(`/company/${encodeURIComponent(ticker)}/memo`)}`}
          className="font-medium text-brand-text underline-offset-2 hover:underline"
        >
          Log in
        </Link>{" "}
        to save this deal to your watchlist.
      </p>
    );
  }

  if (save.status === "saved" || save.status === "already") {
    return (
      <p className="text-sm text-ink-secondary">
        {save.status === "saved" ? "Saved to watchlist." : "Already in watchlist."}{" "}
        <Link
          href="/deals"
          className="font-medium text-brand-text underline-offset-2 hover:underline"
        >
          View saved deals
        </Link>
      </p>
    );
  }

  const onSave = async () => {
    setSave({ status: "saving" });
    try {
      await saveDeal({ ticker, lbo_assumptions: null });
      setSave({ status: "saved" });
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 409) {
        setSave({ status: "already" });
      } else {
        setSave({
          status: "error",
          message:
            err instanceof ApiError
              ? err.detail
              : "Could not save the deal. Try again.",
        });
      }
    }
  };

  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        onClick={onSave}
        disabled={save.status === "saving"}
        className="btn btn-primary px-3 py-1.5 text-sm"
      >
        {save.status === "saving" ? "Saving" : "Save to watchlist"}
      </button>
      {save.status === "error" && (
        <span className="text-sm text-negative-text">{save.message}</span>
      )}
    </div>
  );
}

function MemoSectionBlock({ section }: { section: MemoSection }) {
  // Shaded note block, reserved for missing evidence / gaps (DESIGN.md).
  if (section.key === "data_gaps") {
    return (
      <section className="border border-warn-soft bg-warn-soft px-4 py-3">
        <h2 className="text-[0.8125rem] font-semibold text-warn-text">
          {section.title}
        </h2>
        <MemoRenderer content={section.content} tone="warn" className="mt-2" />
      </section>
    );
  }
  return (
    <section>
      <h2 className="text-[1.0625rem] font-semibold text-ink">
        {section.title}
      </h2>
      <MemoRenderer content={section.content} className="mt-2" />
    </section>
  );
}

/** One labelled row in the memo metadata rail. */
function RailRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="border-t border-line py-2.5">
      <dt className="font-mono text-[10px] uppercase tracking-[0.03em] text-ink-muted">
        {label}
      </dt>
      <dd className="mt-0.5 text-[0.8125rem] text-ink">{children}</dd>
    </div>
  );
}

export default function MemoPage() {
  const { profile } = useCompany();
  const ticker = profile.ticker;

  const { data, error, loading, retry } = useApi(
    () => generateMemo(ticker, null),
    [ticker],
  );

  if (loading) {
    return (
      <div>
        <SectionHeader title="Investment memo" variant="page" as="h2" />
        <LoadingState lines={10} />
        <Disclaimer />
      </div>
    );
  }

  if (error !== null || data === null) {
    return (
      <div>
        <SectionHeader title="Investment memo" variant="page" as="h2" />
        <ErrorState
          message={
            error !== null
              ? error.message
              : `Could not generate the memo for ${ticker}.`
          }
          onRetry={retry}
        />
        <Disclaimer />
      </div>
    );
  }

  const gaps = data.sections.find((s) => s.key === "data_gaps");

  return (
    <div key="content" className="fade-in">
      <header className="flex flex-wrap items-baseline justify-between gap-4 border-b border-line pb-5">
        <div>
          <h2 className="font-display text-[1.625rem] font-semibold leading-snug text-ink">
            First-pass investment memo
          </h2>
          <p className="mt-1 font-mono text-[11px] text-ink-muted">
            {profile.name} · {ticker}
            {profile.exchange ? ` · ${profile.exchange}` : ""}
          </p>
        </div>
        <SaveToWatchlist ticker={ticker} />
      </header>

      {/* Reading column + narrow metadata rail (DESIGN.md memo layout). */}
      <div className="mt-8 gap-10 lg:grid lg:grid-cols-[minmax(0,720px)_13rem]">
        <article className="max-w-[720px] space-y-7">
          {data.sections
            .filter((s) => s.key !== "data_gaps")
            .map((section) => (
              <MemoSectionBlock key={section.key} section={section} />
            ))}
          {gaps && <MemoSectionBlock section={gaps} />}
          <p className="border-t border-line pt-4 text-[0.8125rem] text-ink-muted">
            {data.disclaimer}
          </p>
        </article>

        <aside className="mt-10 lg:mt-0">
          <div className="lg:sticky lg:top-6">
            <p className="font-mono text-[11px] uppercase tracking-[0.04em] text-ink-muted">
              About this draft
            </p>
            <dl className="mt-2">
              <RailRow label="Rating">
                <RatingBadge rating={data.rating} />
              </RailRow>
              <RailRow label="Fiscal period">
                <span className="font-mono">
                  {profile.latest_fiscal_year
                    ? `FY${profile.latest_fiscal_year}`
                    : "n/a"}
                </span>
              </RailRow>
              <RailRow label="Generated">
                <span className="font-mono">
                  {fmtDateTime(data.generated_at)}
                </span>
              </RailRow>
              <RailRow label="Assumptions">Default LBO case</RailRow>
              <RailRow label="Missing inputs">
                {gaps ? "Noted in the draft" : "None flagged"}
              </RailRow>
              <RailRow label="Sources">
                <Link
                  href={`/company/${ticker}/financials`}
                  className="text-link underline decoration-line-strong underline-offset-2 hover:text-link-hover"
                >
                  Filed financials
                </Link>
              </RailRow>
            </dl>
            <p className="mt-3 text-[0.75rem] leading-snug text-ink-muted">
              Assembled from the figures on the analysis pages at the default
              LBO case. Anything missing is stated as missing, not filled in.
            </p>
          </div>
        </aside>
      </div>

      <Disclaimer />
    </div>
  );
}
