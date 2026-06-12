"use client";

// Deal score page: total score with rating, then one card per scoring
// component showing weight, effective weight, a 0-100 score bar, the reason
// string, traced inputs, and warnings. GET /api/companies/{ticker}/score.
// Methodology is stated explicitly — no black-box outputs (BUILD_SPEC section 9).

import { useCompany } from "@/components/company/CompanyContext";
import Card from "@/components/ui/Card";
import Disclaimer from "@/components/ui/Disclaimer";
import ErrorState from "@/components/ui/ErrorState";
import LoadingState from "@/components/ui/LoadingState";
import RatingBadge from "@/components/ui/RatingBadge";
import SectionHeader from "@/components/ui/SectionHeader";
import WarningList from "@/components/ui/WarningList";
import { getScore } from "@/lib/api";
import {
  fmtCurrency,
  fmtDate,
  fmtDays,
  fmtMultiple,
  fmtNumber,
  fmtPercent,
} from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { ScoreComponent, TracedValue } from "@/lib/types";

function fmtTraced(input: TracedValue, currency: string | null): string {
  if (input.value === null) return "—";
  switch (input.unit) {
    case "percent":
      return fmtPercent(input.value);
    case "multiple":
      return fmtMultiple(input.value);
    case "ratio":
      return fmtNumber(input.value, { digits: 2 });
    case "days":
      return fmtDays(input.value);
    case "currency":
    case "per_share":
      return fmtCurrency(input.value, currency);
  }
}

function fmtWeight(weight: number): string {
  const pct = weight * 100;
  return fmtPercent(weight, { digits: Number.isInteger(pct) ? 0 : 1 });
}

function ComponentCard({
  component,
  currency,
}: {
  component: ScoreComponent;
  currency: string | null;
}) {
  const weightsDiffer =
    Math.abs(component.effective_weight - component.weight) > 1e-9;

  return (
    <Card>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold text-ink">{component.label}</h3>
        <div className="text-xs text-ink-muted">
          Weight {fmtWeight(component.weight)}
          {weightsDiffer && (
            <span> · effective {fmtWeight(component.effective_weight)}</span>
          )}
        </div>
      </div>

      <div className="mt-3 flex items-center gap-3">
        <div
          className="h-2 flex-1 overflow-hidden rounded-full bg-surface-sunken"
          role="img"
          aria-label={
            component.score !== null
              ? `Score ${component.score.toFixed(0)} out of 100`
              : "Not scored"
          }
        >
          {component.score !== null && (
            <div
              className="h-full rounded-full bg-brand"
              style={{
                width: `${Math.max(0, Math.min(100, component.score))}%`,
              }}
            />
          )}
        </div>
        <div className="w-20 shrink-0 text-right text-sm font-medium tabular-nums text-ink">
          {component.score !== null
            ? `${component.score.toFixed(0)} / 100`
            : "Not scored"}
        </div>
      </div>

      <p className="mt-3 text-sm text-ink-secondary">{component.reason}</p>

      {component.weighted_points !== null && (
        <p className="mt-1 text-xs text-ink-muted">
          Contributes {component.weighted_points.toFixed(1)} points to the
          total.
        </p>
      )}

      {component.inputs.length > 0 && (
        <dl className="mt-3 space-y-0.5 border-t border-line pt-2">
          {component.inputs.map((input) => (
            <div
              key={input.key}
              className="flex justify-between gap-3 text-xs text-ink-muted"
            >
              <dt>
                {input.label}
                {input.period !== "" ? ` (${input.period})` : ""}
              </dt>
              <dd className="tabular-nums">{fmtTraced(input, currency)}</dd>
            </div>
          ))}
        </dl>
      )}

      <WarningList warnings={component.warnings} className="mt-3" />
    </Card>
  );
}

export default function ScorePage() {
  const { profile } = useCompany();
  const ticker = profile.ticker;

  const { data, error, loading, retry } = useApi(
    () => getScore(ticker),
    [ticker],
  );

  if (loading) {
    return (
      <div>
        <SectionHeader variant="page" as="h2" title="Deal score" />
        <LoadingState lines={8} />
        <Disclaimer />
      </div>
    );
  }

  if (error !== null || data === null) {
    return (
      <div>
        <SectionHeader variant="page" as="h2" title="Deal score" />
        <ErrorState
          message={
            error !== null
              ? error.message
              : `Could not compute the deal score for ${ticker}.`
          }
          onRetry={retry}
        />
        <Disclaimer />
      </div>
    );
  }

  return (
    <div>
      <section>
        <SectionHeader
          variant="page"
          as="h2"
          title="Deal score"
          subtitle={`Computed ${fmtDate(data.as_of)} from the traced figures on these pages.`}
        />
        <Card>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
            <div className="text-5xl font-semibold tabular-nums text-ink">
              {data.total.toFixed(1)}
              <span className="ml-1 text-xl font-normal text-ink-muted">
                / 100
              </span>
            </div>
            <RatingBadge rating={data.rating} />
            <p className="max-w-md text-sm text-ink-muted">{data.disclaimer}</p>
          </div>
        </Card>
      </section>

      <section className="divider-dashed mt-8 pt-8">
        <SectionHeader
          title="Components"
          subtitle="Each component is scored 0–100 and contributes its weight to the total."
        />
        <div className="grid gap-4 lg:grid-cols-2">
          {data.components.map((component) => (
            <ComponentCard
              key={component.key}
              component={component}
              currency={profile.currency ?? null}
            />
          ))}
        </div>
      </section>

      <section className="divider-dashed mt-8 pt-8">
        <SectionHeader title="Methodology" />
        <Card>
          <p className="text-sm leading-relaxed text-ink-secondary">
            The total score is the sum of each component score multiplied by
            its effective weight, using the weights shown on the cards above.
            Each input is scored linearly between a defined worst and best
            threshold, and a component score is the average of its available
            input scores. When every input for a component is unavailable, the
            component is excluded and its weight is redistributed
            proportionally across the remaining components; in that case the
            effective weight shown differs from the base weight. Ratings:
            70 and above Attractive, 50 and above Watchlist, otherwise Pass.
          </p>
        </Card>
      </section>

      <Disclaimer />
    </div>
  );
}
