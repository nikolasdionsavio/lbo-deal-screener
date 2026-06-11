"use client";

// Company-scoped layout: fetches the profile once, renders the company
// header, and provides the profile to child pages via CompanyContext.

import { useEffect, type ReactNode } from "react";
import { CompanyContext } from "@/components/company/CompanyContext";
import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
import WarningList from "@/components/ui/WarningList";
import { getProfile } from "@/lib/api";
import { useApi } from "@/lib/hooks";

export default function CompanyLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: { ticker: string };
}) {
  const ticker = decodeURIComponent(params.ticker).toUpperCase();
  const {
    data: profile,
    error,
    loading,
    retry,
  } = useApi(() => getProfile(ticker), [ticker]);

  useEffect(() => {
    window.localStorage.setItem("lastTicker", ticker);
  }, [ticker]);

  if (loading) {
    return (
      <div className="px-8 py-8">
        <LoadingState lines={6} />
      </div>
    );
  }

  if (error !== null || profile === null) {
    return (
      <div className="px-8 py-8">
        <ErrorState
          message={
            error !== null
              ? error.message
              : `Could not load company data for ${ticker}.`
          }
          onRetry={retry}
        />
      </div>
    );
  }

  const sectorIndustry = [profile.sector, profile.industry]
    .filter((v): v is string => v !== null && v !== "")
    .join(" · ");

  return (
    <CompanyContext.Provider value={{ profile, refetch: retry }}>
      <div className="px-8 py-8">
        <header className="mb-6 border-b border-line pb-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <h1 className="font-display text-[1.75rem] font-semibold leading-tight text-ink">
                  {profile.name}
                </h1>
                <span className="text-sm font-medium tabular-nums text-ink-muted">
                  {profile.ticker}
                  {profile.exchange !== null && profile.exchange !== ""
                    ? ` · ${profile.exchange}`
                    : ""}
                </span>
              </div>
              <p className="mt-1 text-sm text-ink-muted">
                {sectorIndustry !== ""
                  ? sectorIndustry
                  : "Sector and industry not available"}
              </p>
            </div>
            <span
              className="inline-flex shrink-0 items-center rounded-full border border-line-strong bg-surface px-3 py-1 text-xs text-ink-secondary"
              title="Data source, data date and reporting currency"
            >
              {profile.data_source}
              {profile.data_as_of !== null
                ? ` · as of ${profile.data_as_of}`
                : ""}
              {profile.currency != null && profile.currency !== "USD"
                ? ` · reported in ${profile.currency}`
                : ""}
            </span>
          </div>
          <WarningList warnings={profile.warnings} className="mt-4" />
        </header>
        {children}
      </div>
    </CompanyContext.Provider>
  );
}
