"use client";

// Two densities, one identity (DESIGN.md). The public pages are editorial and
// must NOT wear the application shell: no company rail, no second search. The
// research workspace keeps the compact rail and utility bar. The print
// one-pager wears nothing at all.

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import Link from "next/link";
import PublicHeader from "@/components/chrome/PublicHeader";
import TopBar from "@/components/chrome/TopBar";
import Sidebar from "@/components/Sidebar";
import { RELEASES } from "@/lib/version";

// Editorial surfaces. Everything else is the workspace.
const PUBLIC_ROUTES = new Set([
  "/",
  "/about",
  "/contact",
  "/methodology",
  "/changelog",
  "/how-to-use",
  "/whats-new",
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
]);

function isPublic(pathname: string): boolean {
  return PUBLIC_ROUTES.has(pathname) || pathname.startsWith("/auth");
}

function Footer() {
  return (
    <footer className="border-t border-line px-[18px] py-4 sm:px-8 lg:px-12">
      <div className="mx-auto flex max-w-[1240px] flex-wrap items-center justify-between gap-x-4 gap-y-1 font-mono text-[10px] text-ink-muted">
        <span>Investment Intelligence · a personal research tool</span>
        <Link href="/changelog" className="inspectable transition-colors hover:text-ink">
          Last updated {RELEASES[0].date}
        </Link>
      </div>
    </footer>
  );
}

export default function Shell({ children }: { children: ReactNode }) {
  const pathname = usePathname() ?? "/";

  // Print surface: no chrome.
  if (pathname.startsWith("/onepager")) return <>{children}</>;

  if (isPublic(pathname)) {
    return (
      <div className="flex min-h-screen flex-col">
        <PublicHeader />
        <main className="flex-1">{children}</main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="min-w-0 flex-1">{children}</main>
        <Footer />
      </div>
    </div>
  );
}
