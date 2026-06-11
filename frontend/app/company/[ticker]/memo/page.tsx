"use client";

// Investment memo page: POST /api/companies/{ticker}/memo with null
// lbo_assumptions (default LBO case), rendered as a clean document in
// section order. The data gaps section is visually distinct (amber).
// Save to watchlist requires auth; 409 is treated as already saved.

import Link from "next/link";
import { useState } from "react";
import { useCompany } from "@/components/company/CompanyContext";
import MemoRenderer from "@/components/memo/MemoRenderer";
import Card from "@/components/ui/Card";
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
  if (section.key === "data_gaps") {
    return (
      <section className="rounded-lg bg-warn-soft p-5">
        <h2 className="font-display text-lg font-semibold text-warn-text">
          {section.title}
        </h2>
        <MemoRenderer content={section.content} tone="warn" className="mt-3" />
      </section>
    );
  }
  return (
    <section>
      <SectionHeader title={section.title} variant="document" className="mb-2" />
      <MemoRenderer content={section.content} />
    </section>
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
        <SectionHeader title="Investment memo" variant="page" />
        <LoadingState lines={10} />
        <Disclaimer />
      </div>
    );
  }

  if (error !== null || data === null) {
    return (
      <div>
        <SectionHeader title="Investment memo" variant="page" />
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

  return (
    <div className="max-w-3xl">
      <header className="mb-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <h1 className="font-display text-[1.375rem] font-semibold leading-snug text-ink">
              Investment memo
            </h1>
            <RatingBadge rating={data.rating} />
          </div>
          <SaveToWatchlist ticker={ticker} />
        </div>
        <p className="mt-2 text-sm text-ink-muted">
          Generated {fmtDateTime(data.generated_at)} · Data source:{" "}
          {profile.data_source}
          {profile.data_as_of !== null ? ` · data as of ${profile.data_as_of}` : ""}
        </p>
        <p className="mt-1 text-sm text-ink-muted">{data.disclaimer}</p>
        <p className="mt-1 text-xs text-ink-muted">
          Generated from deterministic templates over computed data at default
          LBO assumptions. Missing data is stated as missing, never invented.
        </p>
      </header>

      <Card>
        <article className="space-y-8">
          {data.sections.map((section) => (
            <MemoSectionBlock key={section.key} section={section} />
          ))}
        </article>
      </Card>

      <Disclaimer />
    </div>
  );
}
