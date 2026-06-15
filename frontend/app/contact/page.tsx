// Contact (route /contact): a single Card with a direct email contact and a
// link to the About page. Static, server-rendered. No phone or address.

import type { Metadata } from "next";
import Link from "next/link";
import Card from "@/components/ui/Card";
import Disclaimer from "@/components/ui/Disclaimer";
import SectionHeader from "@/components/ui/SectionHeader";

export const metadata: Metadata = {
  title: "Contact · Investment Intelligence",
  description: "Get in touch about Investment Intelligence.",
};

const CONTACT_EMAIL = "contact@nikolasdionsavio.com";

function MailIcon() {
  return (
    <svg
      width={16}
      height={16}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="1.75" y="3.5" width="12.5" height="9" rx="1.5" />
      <path d="m2.5 4.5 5.5 4 5.5-4" />
    </svg>
  );
}

export default function ContactPage() {
  return (
    <div className="flex min-h-[calc(100vh-3rem)] flex-col px-4 py-8 sm:px-8">
      <div className="mx-auto w-full max-w-2xl">
        <SectionHeader variant="page" title="Contact" />

        <Card>
          <p className="max-w-prose text-sm leading-relaxed text-ink-secondary">
            Questions, feedback, or opportunities — reach me directly by email.
          </p>
          <a
            href={`mailto:${CONTACT_EMAIL}`}
            className="btn btn-primary mt-5 gap-2 px-4 py-2 text-sm"
          >
            <MailIcon />
            {CONTACT_EMAIL}
          </a>
          <p className="mt-5 text-sm text-ink-muted">
            More about the project and the author on the{" "}
            <Link
              href="/about"
              className="font-medium text-brand-text underline-offset-2 hover:underline"
            >
              About
            </Link>{" "}
            page.
          </p>
        </Card>
      </div>
      <div className="mx-auto w-full max-w-2xl">
        <Disclaimer />
      </div>
    </div>
  );
}
