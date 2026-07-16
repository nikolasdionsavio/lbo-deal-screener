"use client";

// Risks (route /company/[ticker]/risks): a rating-agency-style read — a
// Financial Risk profile computed from the filed statements (distress scores +
// RAG credit metrics), market risk, sector (peer-relative) context, and the
// company's OWN disclosed risk factors pulled verbatim from the 10-K Item 1A
// (keyword-categorised, never summarised). Every figure is traceable; anything
// that can't be computed shows an honest "n/a" rather than a fabricated value.

import { useCompany } from "@/components/company/CompanyContext";
import Card from "@/components/ui/Card";
import Disclaimer from "@/components/ui/Disclaimer";
import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
import SectionHeader from "@/components/ui/SectionHeader";
import WarningList from "@/components/ui/WarningList";
import { getRisks } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type {
  DistressScore,
  RiskBand,
  RiskFlag,
  RiskMetric,
  SectorComparison,
} from "@/lib/types";

const FLAG: Record<RiskFlag, { cls: string; label: string }> = {
  low: { cls: "bg-accent-soft text-positive-text", label: "Low" },
  medium: { cls: "bg-warn-soft text-warn-text", label: "Moderate" },
  high: { cls: "bg-negative/10 text-negative-text", label: "High" },
  na: { cls: "bg-surface-sunken text-ink-muted", label: "n/a" },
};

const BAND: Record<RiskBand, { cls: string; label: string }> = {
  low: { cls: "text-positive-text", label: "Low" },
  moderate: { cls: "text-warn-text", label: "Moderate" },
  elevated: { cls: "text-warn-text", label: "Elevated" },
  high: { cls: "text-negative-text", label: "High" },
  na: { cls: "text-ink-muted", label: "Not assessed" },
};

function FlagBadge({ flag }: { flag: RiskFlag }) {
  const f = FLAG[flag];
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${f.cls}`}
    >
      {f.label}
    </span>
  );
}

/** A left accent bar keyed to the flag, used on metric rows. */
function flagBar(flag: RiskFlag): string {
  return flag === "high"
    ? "bg-negative"
    : flag === "medium"
      ? "bg-warn"
      : flag === "low"
        ? "bg-accent"
        : "bg-line-strong";
}

function MetricRow({ m }: { m: RiskMetric }) {
  return (
    <div className="flex items-start gap-3 py-3">
      <span
        aria-hidden
        className={`mt-1 h-8 w-1 shrink-0 rounded-full ${flagBar(m.flag)}`}
      />
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-3">
          <span className="text-sm font-medium text-ink">{m.label}</span>
          <span className="tabular-nums text-sm font-semibold text-ink">
            {m.formatted}
          </span>
        </div>
        <p className="mt-0.5 text-xs leading-snug text-ink-muted">
          {m.interpretation}
        </p>
      </div>
      <FlagBadge flag={m.flag} />
    </div>
  );
}

function DistressCard({ d }: { d: DistressScore }) {
  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-medium text-ink-secondary">{d.name}</div>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="text-2xl font-semibold tabular-nums text-ink">
              {d.formatted}
            </span>
            <span className="text-sm text-ink-muted">{d.zone}</span>
          </div>
        </div>
        <FlagBadge flag={d.flag} />
      </div>
      <p className="mt-2 text-xs leading-snug text-ink-muted">
        {d.interpretation}
      </p>
      <p className="mt-2 border-t border-line pt-2 text-[11px] text-ink-muted">
        {d.formula}
      </p>
    </Card>
  );
}

function SectorRow({ s }: { s: SectorComparison }) {
  return (
    <div className="flex items-start gap-3 py-3">
      <span
        aria-hidden
        className={`mt-1 h-8 w-1 shrink-0 rounded-full ${flagBar(s.flag)}`}
      />
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-3">
          <span className="text-sm font-medium text-ink">{s.metric}</span>
          <span className="tabular-nums text-sm text-ink">
            <span className="font-semibold">{s.company_formatted}</span>
            <span className="text-ink-muted">
              {" "}
              vs {s.peer_median_formatted} median
            </span>
          </span>
        </div>
        <p className="mt-0.5 text-xs leading-snug text-ink-muted">
          {s.note} ({s.peer_count} peers)
        </p>
      </div>
      <FlagBadge flag={s.flag} />
    </div>
  );
}

export default function RisksPage() {
  const { profile } = useCompany();
  const ticker = profile.ticker;
  const { data, error, loading, retry } = useApi(() => getRisks(ticker), [ticker]);

  const header = (
    <SectionHeader
      variant="page"
      as="h2"
      title="Risk Assessment"
      subtitle="A financial risk profile computed from the filings, sector context, and the company's own disclosed risk factors. Every figure is traceable to its source."
    />
  );

  if (loading) {
    return (
      <div className="space-y-6">
        {header}
        <p className="text-sm text-ink-muted">
          Computing risk metrics and reading the latest 10-K. The first load can
          take a moment.
        </p>
        <LoadingState lines={10} />
        <Disclaimer />
      </div>
    );
  }
  if (error !== null || data === null) {
    return (
      <div className="space-y-6">
        {header}
        <ErrorState
          message={error?.message ?? `Risk data is unavailable for ${ticker}.`}
          onRetry={retry}
        />
        <Disclaimer />
      </div>
    );
  }

  const band = BAND[data.financial_band];
  const categories = Object.entries(data.risk_factor_categories).sort(
    (a, b) => b[1] - a[1],
  );

  return (
    <div className="fade-in space-y-6">
      {header}
      <WarningList warnings={data.warnings} />

      {/* Composite read */}
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="text-xs font-medium uppercase tracking-wide text-ink-muted">
              Financial risk
            </div>
            <div className={`mt-1 text-3xl font-semibold ${band.cls}`}>
              {band.label}
            </div>
          </div>
          {data.going_concern_flagged && (
            <span className="inline-flex items-center rounded-full bg-negative/10 px-3 py-1 text-sm font-medium text-negative-text">
              Going-concern language in the filing
            </span>
          )}
        </div>
        <p className="mt-3 border-t border-line pt-3 text-sm text-ink-secondary">
          {data.financial_summary}
        </p>
      </Card>

      {/* Distress scores */}
      {data.distress.length > 0 && (
        <section>
          <SectionHeader
            title="Distress & strength scores"
            subtitle="Standard bankruptcy-risk and financial-strength models"
          />
          <div className="grid gap-4 sm:grid-cols-2">
            {data.distress.map((d) => (
              <DistressCard key={d.name} d={d} />
            ))}
          </div>
        </section>
      )}

      {/* Financial risk metrics */}
      {data.financial_metrics.length > 0 && (
        <section className="divider-dashed mt-8 pt-8">
          <SectionHeader
            title="Credit metrics"
            subtitle="Leverage, coverage, liquidity and earnings quality, flagged against standard thresholds"
          />
          <Card>
            <div className="divide-y divide-line">
              {data.financial_metrics.map((m) => (
                <MetricRow key={m.key} m={m} />
              ))}
            </div>
          </Card>
        </section>
      )}

      {/* Market risk */}
      {data.market_metrics.length > 0 && (
        <section className="divider-dashed mt-8 pt-8">
          <SectionHeader
            title="Market risk"
            subtitle="Systematic risk and realised price volatility"
          />
          <Card>
            <div className="divide-y divide-line">
              {data.market_metrics.map((m) => (
                <MetricRow key={m.key} m={m} />
              ))}
            </div>
          </Card>
        </section>
      )}

      {/* Sector context */}
      <section className="divider-dashed mt-8 pt-8">
        <SectionHeader
          title="Sector context"
          subtitle="How the company's risk metrics compare to its peers"
        />
        <Card>
          {data.sector_comparisons.length > 0 ? (
            <div className="divide-y divide-line">
              {data.sector_comparisons.map((s) => (
                <SectorRow key={s.metric} s={s} />
              ))}
              <p className="pt-3 text-xs text-ink-muted">{data.sector_note}</p>
            </div>
          ) : (
            <p className="text-sm text-ink-secondary">{data.sector_note}</p>
          )}
        </Card>
      </section>

      {/* Disclosed risk factors (qualitative) */}
      <section className="divider-dashed mt-8 pt-8">
        <SectionHeader
          title="Disclosed risk factors"
          subtitle={
            data.risk_factors_period
              ? `The company's own risk factors, as disclosed in its ${data.risk_factors_period} (Item 1A)`
              : "The company's own disclosed risk factors"
          }
        />
        <Card>
          {data.risk_factors.length > 0 ? (
            <>
              {categories.length > 0 && (
                <div className="mb-4 flex flex-wrap gap-2">
                  {categories.map(([cat, n]) => (
                    <span
                      key={cat}
                      className="inline-flex items-center gap-1.5 rounded-full border border-line-strong px-2.5 py-0.5 text-xs text-ink-secondary"
                    >
                      {cat}
                      <span className="tabular-nums font-medium text-ink">
                        {n}
                      </span>
                    </span>
                  ))}
                </div>
              )}
              <ul className="divide-y divide-line">
                {data.risk_factors.map((f, i) => (
                  <li key={i} className="flex items-start gap-3 py-2.5">
                    <span className="mt-0.5 shrink-0 rounded bg-surface-sunken px-1.5 py-0.5 text-[10px] font-medium text-ink-muted">
                      {f.category}
                    </span>
                    <span className="text-sm leading-snug text-ink-secondary">
                      {f.heading}
                    </span>
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p className="text-sm text-ink-secondary">
              Individual risk factors could not be parsed from the filing.
            </p>
          )}
          {data.risk_factors_source && (
            <p className="mt-4 border-t border-line pt-3 text-xs text-ink-muted">
              Source:{" "}
              <a
                href={data.risk_factors_source}
                target="_blank"
                rel="noopener noreferrer"
                className="underline decoration-dotted underline-offset-2 hover:text-ink"
              >
                {data.risk_factors_period ?? "10-K"}, Item 1A · SEC EDGAR
              </a>
              . Shown verbatim; not summarised.
            </p>
          )}
        </Card>
      </section>

      {data.sources.length > 0 && (
        <p className="text-xs text-ink-muted">
          Sources: {data.sources.join("; ")}. As of {fmtDate(data.as_of)}.
          Metrics computed from standardised XBRL; some may be unavailable where
          the company did not tag the underlying line item.
        </p>
      )}
      <Disclaimer />
    </div>
  );
}
