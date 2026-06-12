"use client";

// Financial statements page (BUILD_SPEC section 19.7): the full filed
// history from GET /api/companies/{ticker}/statements, one statement at a
// time behind a keyboard-accessible segmented control. EDGAR is uncapped
// here (up to 15 years); mock mode carries its five.

import { useRef, useState, type KeyboardEvent } from "react";
import { useCompany } from "@/components/company/CompanyContext";
import StatementTable, {
  type StatementKey,
} from "@/components/financials/StatementTable";
import Card from "@/components/ui/Card";
import Disclaimer from "@/components/ui/Disclaimer";
import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
import SectionHeader from "@/components/ui/SectionHeader";
import WarningList from "@/components/ui/WarningList";
import { getStatements } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { useApi } from "@/lib/hooks";

const TABS: { key: StatementKey; label: string }[] = [
  { key: "income_statement", label: "Income statement" },
  { key: "balance_sheet", label: "Balance sheet" },
  { key: "cash_flow", label: "Cash flow" },
];

/**
 * Segmented control (8px-radius group, 6px segments). Implemented as a
 * tablist with roving tabindex: Left/Right/Home/End move and select, so the
 * control is fully keyboard operable.
 */
function StatementTabs({
  active,
  onChange,
}: {
  active: StatementKey;
  onChange: (key: StatementKey) => void;
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const index = TABS.findIndex((tab) => tab.key === active);
    let next: number | null = null;
    if (event.key === "ArrowRight") next = (index + 1) % TABS.length;
    else if (event.key === "ArrowLeft")
      next = (index - 1 + TABS.length) % TABS.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = TABS.length - 1;
    if (next === null) return;
    event.preventDefault();
    onChange(TABS[next].key);
    refs.current[next]?.focus();
  }

  return (
    <div
      role="tablist"
      aria-label="Statement"
      onKeyDown={handleKeyDown}
      className="inline-flex rounded border border-line bg-surface-sunken p-1"
    >
      {TABS.map((tab, index) => {
        const selected = tab.key === active;
        return (
          <button
            key={tab.key}
            ref={(el) => {
              refs.current[index] = el;
            }}
            type="button"
            role="tab"
            id={`statement-tab-${tab.key}`}
            aria-selected={selected}
            aria-controls="statement-panel"
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(tab.key)}
            className={`rounded-[6px] px-3 py-1.5 text-sm transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent ${
              selected
                ? "bg-surface font-medium text-ink shadow-card"
                : "text-ink-muted hover:text-ink"
            }`}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}

export default function FinancialsPage() {
  const { profile } = useCompany();
  const ticker = profile.ticker;
  const [active, setActive] = useState<StatementKey>("income_statement");

  const { data, error, loading, retry } = useApi(
    () => getStatements(ticker),
    [ticker],
  );

  if (loading) {
    return (
      <div>
        <SectionHeader
          variant="page"
          as="h2"
          title="Financial statements"
          subtitle="Pulling the filed annual history. EDGAR carries up to fifteen years."
        />
        <Card>
          <LoadingState lines={10} />
        </Card>
        <Disclaimer />
      </div>
    );
  }

  if (error !== null || data === null) {
    return (
      <div>
        <SectionHeader variant="page" as="h2" title="Financial statements" />
        <ErrorState
          message={
            error !== null
              ? error.message
              : `Could not load statements for ${ticker}.`
          }
          onRetry={retry}
        />
        <Disclaimer />
      </div>
    );
  }

  // The API contract is newest-first; sort defensively so columns are
  // always newest-left even if a provider slips.
  const years = [...data.years].sort((a, b) => b.fiscal_year - a.fiscal_year);
  const yearCount = years.length;

  return (
    <div>
      <section>
        <SectionHeader
          variant="page"
          as="h2"
          title="Financial statements"
          subtitle={`${data.data_source} · ${yearCount} fiscal ${
            yearCount === 1 ? "year" : "years"
          } of filed annual data · retrieved ${fmtDate(data.fetched_at)}`}
        />
        <WarningList warnings={data.warnings} className="mb-4" />

        {yearCount === 0 ? (
          <Card>
            <p className="text-sm text-ink-muted">
              No filed annual statements are available for {ticker}.
            </p>
          </Card>
        ) : (
          <>
            <StatementTabs active={active} onChange={setActive} />
            <Card className="mt-4">
              <div
                id="statement-panel"
                role="tabpanel"
                aria-labelledby={`statement-tab-${active}`}
              >
                <StatementTable
                  statement={active}
                  years={years}
                  currency={data.currency ?? null}
                />
              </div>
            </Card>
            <p className="mt-3 text-xs text-ink-muted">
              Annual figures as filed; the LBO page carries the forward case.
            </p>
          </>
        )}
      </section>

      <Disclaimer />
    </div>
  );
}
