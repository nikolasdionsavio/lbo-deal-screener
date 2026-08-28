"use client";

// The signature scroll-linked sequence.
//
// It exists because the product's central claim is that it does not guess: an
// EBITDA it cannot compute is left blank rather than filled in. That claim is
// a sentence everywhere else on the site. Here it is the actual shape of the
// index, drawn from the live coverage figures, and the reader scrubs through
// it: the bar fills as the section crosses the viewport, and the three
// segments arrive in sequence rather than together, so the proportion lands
// before the caveat does.
//
// Nothing here is decorative. Every number is the one the API returned, and
// the widths are those numbers as a percentage. If the index changes, the
// drawing changes with it.

import Link from "next/link";
import Container from "@/components/ui/Container";
import { Reveal, useScrollProgress } from "@/lib/motion";
import { getScreen } from "@/lib/api";
import { useApi } from "@/lib/hooks";

interface Band {
  key: string;
  label: string;
  note: string;
  value: number;
  /** Scrub window. Staggered so the segments arrive one after another. */
  from: number;
  to: number;
  tone: string;
}

export default function HomeCoverage() {
  const { data } = useApi(() => getScreen({ limit: 1 }), []);
  const coverage = data?.coverage;
  const ref = useScrollProgress<HTMLDivElement>({ varName: "--p" });

  if (!coverage || coverage.total === 0) return null;

  const total = coverage.total;
  const bands: Band[] = [
    {
      key: "with_ebitda",
      label: "EBITDA can be calculated",
      note: "Operating income and D&A are both tagged.",
      value: coverage.with_ebitda,
      from: 0.06,
      to: 0.48,
      tone: "bg-brand",
    },
    {
      key: "ebit_only",
      label: "D&A not disclosed",
      note: "Operating income only. EBITDA is left blank, not estimated.",
      value: coverage.ebit_only,
      from: 0.26,
      to: 0.72,
      tone: "bg-line-strong",
    },
    {
      key: "revenue_only",
      label: "Revenue only",
      note: "Nothing below the top line is tagged in a usable form.",
      value: coverage.revenue_only,
      from: 0.46,
      to: 0.94,
      tone: "bg-line",
    },
  ];

  return (
    <section className="glass-thin mt-28 border-y border-line py-16 lg:mt-36 lg:py-24">
      <Container>
        <div ref={ref} className="scrub">
          <div className="grid grid-cols-12 gap-x-6 gap-y-10">
            <div className="col-span-12 lg:col-span-4">
              <Reveal variant="rule">
                <p className="tape">Index coverage</p>
              </Reveal>
              <Reveal variant="lift" lead={80}>
                <h2 className="ed-section mt-6">
                  Four in ten filers cannot have an EBITDA
                </h2>
              </Reveal>
              <Reveal variant="rise" lead={160}>
                <p className="ed-body mt-5 !text-[1rem]">
                  Not every company tags depreciation and amortisation
                  separately. Where the filing does not carry it, the number is
                  left blank and the row says so. The alternative is to infer
                  one, which is how a screen quietly stops being checkable.
                </p>
              </Reveal>
              <Reveal variant="rise" lead={240}>
                <p className="mt-6">
                  <Link
                    href="/methodology"
                    className="text-[0.9375rem] text-link underline decoration-line-strong underline-offset-[3px] transition-colors hover:text-link-hover hover:decoration-link"
                  >
                    How EBITDA is calculated
                  </Link>
                </p>
              </Reveal>
            </div>

            <div className="col-span-12 lg:col-span-7 lg:col-start-6">
              <div className="flex items-baseline justify-between gap-4">
                <span className="font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.08em] text-ink-muted">
                  US-listed filers indexed
                </span>
                <span className="font-mono text-[1.75rem] font-semibold tabular-nums text-ink">
                  {total.toLocaleString()}
                </span>
              </div>

              {/* The bar. One track, three segments, each scrubbed on its own
                  window so they fill in sequence. */}
              <div className="mt-4 flex h-3 w-full gap-[2px] overflow-hidden bg-line/40">
                {bands.map((b) => (
                  <div
                    key={b.key}
                    className={`scrub-seg ${b.tone}`}
                    style={
                      {
                        width: `${(b.value / total) * 100}%`,
                        "--from": b.from,
                        "--to": b.to,
                      } as React.CSSProperties
                    }
                  />
                ))}
              </div>

              <dl className="mt-8">
                {bands.map((b, i) => (
                  <Reveal
                    as="div"
                    key={b.key}
                    variant="settle"
                    index={i}
                    step={80}
                    className="grid grid-cols-[auto_1fr] items-baseline gap-x-4 border-t border-line py-4 sm:grid-cols-[7rem_1fr_auto]"
                  >
                    <dt className="font-mono text-[1.0625rem] font-semibold tabular-nums text-ink">
                      {b.value.toLocaleString()}
                    </dt>
                    <dd className="col-span-1 min-w-0">
                      <span className="block text-[0.9375rem] font-medium text-ink">
                        {b.label}
                      </span>
                      <span className="mt-0.5 block max-w-[46ch] text-[0.8125rem] leading-snug text-ink-muted">
                        {b.note}
                      </span>
                    </dd>
                    <dd className="hidden font-mono text-[0.8125rem] tabular-nums text-ink-muted sm:block">
                      {((b.value / total) * 100).toFixed(1)}%
                    </dd>
                  </Reveal>
                ))}
              </dl>
            </div>
          </div>
        </div>
      </Container>
    </section>
  );
}
