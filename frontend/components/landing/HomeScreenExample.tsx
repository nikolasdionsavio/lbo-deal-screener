"use client";

// The deal screen, shown by running it rather than describing it. Every figure
// below is fetched live from the same endpoint the screen page uses, so this is
// real output on real filings. Nothing here is hardcoded, including the counts,
// which would otherwise drift as new filings land.

import Link from "next/link";
import { getScreen } from "@/lib/api";
import { useApi } from "@/lib/hooks";

// The origination criteria the screen was built to answer.
const QUERY = {
  revenue_min: 3_000_000,
  revenue_max: 20_000_000,
  ebitda_positive: true,
  exclude_flagged: true,
  sort: "ebitda",
  direction: "desc" as const,
  limit: 5,
};

const SCREEN_HREF =
  "/screen?revenue_min=3000000&revenue_max=20000000&ebitda_positive=true";

function money(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(2)}bn`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(1)}m`;
  return `${sign}$${(abs / 1e3).toFixed(0)}k`;
}

export default function HomeScreenExample() {
  const { data, loading } = useApi(() => getScreen(QUERY), []);
  const rows = data?.rows ?? [];
  const coverage = data?.coverage;

  return (
    <section className="mt-20 border-t border-line pt-8">
      <div className="grid grid-cols-12 gap-x-6 gap-y-6">
        <div className="col-span-12 lg:col-span-5">
          <p className="font-mono text-[11px] uppercase tracking-[0.04em] text-ink-muted">
            New
          </p>
          <h2 className="mt-2 font-display text-[1.75rem] font-normal leading-[1.15] tracking-[-0.01em] text-ink">
            Find companies, not just research one
          </h2>
          <p className="mt-4 max-w-[52ch] text-[1.0625rem] leading-[1.55] text-ink-secondary">
            The deal screen filters every US-listed filer on figures taken from
            their own SEC filings. Set a revenue band, require positive EBITDA,
            narrow by sector, then open any company straight into the workspace.
          </p>
          <p className="mt-4 max-w-[52ch] text-[0.9375rem] leading-[1.55] text-ink-secondary">
            EBITDA is calculated as operating income plus depreciation and
            amortisation. Where a company does not report D&amp;A separately it
            is left blank, because filling it in would be a guess.
          </p>
          <p className="mt-5">
            <Link href="/screen" className="btn btn-primary px-4 py-2 text-sm">
              Open the deal screen
            </Link>
          </p>
        </div>

        {/* The live result. A worked query, not a mock-up. */}
        <div className="col-span-12 lg:col-span-7">
          <div className="border border-line bg-surface px-4 py-4 sm:px-5">
            <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
              <p className="font-mono text-[11px] text-ink-muted">
                Revenue $3m to $20m · positive EBITDA
              </p>
              <p className="font-mono text-[11px] text-ink-muted">
                {data ? `${data.total} companies` : "running the screen"}
              </p>
            </div>

            {loading && !data ? (
              <div className="mt-4 space-y-2">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="skeleton h-5 w-full" />
                ))}
              </div>
            ) : rows.length > 0 ? (
              <table className="mt-3 w-full border-collapse text-left">
                <thead>
                  <tr className="border-y border-line">
                    <th className="py-1.5 font-mono text-[10px] font-normal uppercase tracking-[0.04em] text-ink-muted">
                      Company
                    </th>
                    <th className="py-1.5 text-right font-mono text-[10px] font-normal uppercase tracking-[0.04em] text-ink-muted">
                      Revenue
                    </th>
                    <th className="py-1.5 text-right font-mono text-[10px] font-normal uppercase tracking-[0.04em] text-ink-muted">
                      EBITDA
                    </th>
                    <th className="py-1.5 text-right font-mono text-[10px] font-normal uppercase tracking-[0.04em] text-ink-muted">
                      Margin
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.cik} className="border-b border-line">
                      <td className="py-2 pr-3">
                        <span className="font-mono text-[0.8125rem] text-link">
                          {r.ticker ?? "—"}
                        </span>
                        <span className="ml-2 text-[0.8125rem] text-ink">
                          {r.name.length > 26
                            ? `${r.name.slice(0, 26)}…`
                            : r.name}
                        </span>
                      </td>
                      <td className="whitespace-nowrap py-2 text-right font-mono text-[0.8125rem] tabular-nums text-ink">
                        {money(r.revenue)}
                      </td>
                      <td className="whitespace-nowrap py-2 pl-2 text-right font-mono text-[0.8125rem] tabular-nums text-ink">
                        {money(r.ebitda)}
                      </td>
                      <td className="whitespace-nowrap py-2 pl-2 text-right font-mono text-[0.8125rem] tabular-nums text-ink-secondary">
                        {r.ebitda_margin === null
                          ? "—"
                          : `${(r.ebitda_margin * 100).toFixed(1)}%`}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="mt-4 text-[0.875rem] text-ink-secondary">
                The screen is not returning results right now. The link below
                still opens the real page.
              </p>
            )}

            {coverage && (
              <p className="mt-3 font-mono text-[10px] leading-relaxed text-ink-muted">
                {coverage.total.toLocaleString()} US-listed filers indexed ·{" "}
                {coverage.with_ebitda.toLocaleString()} with a calculable
                EBITDA · {coverage.ebit_only.toLocaleString()} do not disclose
                D&amp;A
              </p>
            )}
          </div>
          <p className="mt-2 text-right">
            <Link
              href={SCREEN_HREF}
              className="text-[0.8125rem] text-link underline-offset-2 hover:underline"
            >
              See all {data ? data.total : ""} results
            </Link>
          </p>
        </div>
      </div>
    </section>
  );
}
