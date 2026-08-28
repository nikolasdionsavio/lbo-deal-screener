// Contact (route /contact): feedback-first. Four concrete reasons, each opening
// an email with a subject already set, so a report lands sorted. Static.

import type { Metadata } from "next";
import Link from "next/link";
import Disclaimer from "@/components/ui/Disclaimer";

export const metadata: Metadata = {
  title: "Contact",
  description:
    "Report a data issue, question a calculation, or suggest a feature for Investment Intelligence.",
};

const CONTACT_EMAIL = "contact@nikolasdionsavio.com";

const REASONS = [
  {
    label: "Report a data issue",
    detail: "A figure looks wrong, stale, or mismapped from the filing.",
    subject: "Data issue",
  },
  {
    label: "Question a calculation",
    detail: "A formula, KPI, or model output does not add up.",
    subject: "Calculation question",
  },
  {
    label: "Suggest a feature",
    detail: "Something that would make the research process clearer or faster.",
    subject: "Feature suggestion",
  },
  {
    label: "General message",
    detail: "Anything else.",
    subject: "Hello",
  },
];

function mailto(subject: string) {
  return `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(
    `Investment Intelligence: ${subject}`,
  )}`;
}

export default function ContactPage() {
  return (
    <div className="px-4 py-10 sm:px-8">
      <div className="mx-auto w-full max-w-2xl">
        <h1 className="ed-title text-ink">
          Feedback is welcome
        </h1>
        <p className="mt-3 max-w-prose text-[0.95rem] leading-relaxed text-ink-secondary">
          If you find a data error, an unclear calculation, or a feature that
          would improve the research process, please send it through. It helps
          to mention the company and the page you were on.
        </p>

        <div className="mt-8">
          {REASONS.map((r) => (
            <a
              key={r.label}
              href={mailto(r.subject)}
              className="group flex items-baseline justify-between gap-4 border-t border-line py-3.5 transition-colors hover:bg-brand-soft"
            >
              <div>
                <div className="text-[0.95rem] font-medium text-brand-text">
                  {r.label}
                </div>
                <div className="mt-0.5 text-sm text-ink-muted">{r.detail}</div>
              </div>
              <span
                aria-hidden
                className="shrink-0 font-mono text-xs text-ink-muted transition-colors group-hover:text-brand-text"
              >
                email &rarr;
              </span>
            </a>
          ))}
          <div className="border-t border-line" />
        </div>

        <p className="mt-6 text-sm text-ink-muted">
          Or write directly to{" "}
          <a
            href={`mailto:${CONTACT_EMAIL}`}
            className="font-mono text-brand-text underline decoration-line-strong underline-offset-2 hover:decoration-brand"
          >
            {CONTACT_EMAIL}
          </a>
          . More about the project on the{" "}
          <Link
            href="/about"
            className="text-brand-text underline decoration-line-strong underline-offset-2 hover:decoration-brand"
          >
            About
          </Link>{" "}
          page.
        </p>

        <Disclaimer />
      </div>
    </div>
  );
}
