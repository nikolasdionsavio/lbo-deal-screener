"use client";

// Mobile navigation (below lg, where the desktop sidebar is hidden): a
// hamburger in the top bar opens an off-canvas drawer carrying the full
// Sidebar content in a fixed ~280px left panel on the sidebar tokens.
// Slide-in 200ms ease-out over a bg-black/40 scrim fade (globals.css; the
// global reduced-motion rule makes both instant). Closes on scrim click,
// Escape, any link click, and route change; body scroll is locked while
// open; focus moves into the panel on open and back to the hamburger on
// close.

import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import Sidebar from "@/components/Sidebar";

function MenuIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      aria-hidden="true"
    >
      <path d="M3 5.5h14M3 10h14M3 14.5h14" />
    </svg>
  );
}

export default function MobileNav() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const panelRef = useRef<HTMLDivElement | null>(null);
  const buttonRef = useRef<HTMLButtonElement | null>(null);

  // Route change closes the drawer (navigation happened).
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  // While open: Escape closes, body scroll is locked, focus sits in the
  // panel. The cleanup (close or unmount) releases the lock and returns
  // focus to the hamburger.
  useEffect(() => {
    if (!open) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", onKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    panelRef.current?.focus();
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
      buttonRef.current?.focus();
    };
  }, [open]);

  return (
    <div className="lg:hidden">
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Open navigation"
        aria-expanded={open}
        aria-controls="mobile-nav-drawer"
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded text-ink-secondary transition-colors duration-150 hover:bg-brand-soft hover:text-ink"
      >
        <MenuIcon />
      </button>

      {open && (
        <div className="fixed inset-0 z-50">
          <div
            className="drawer-scrim absolute inset-0 bg-black/40"
            onClick={() => setOpen(false)}
            aria-hidden="true"
          />
          <div
            ref={panelRef}
            id="mobile-nav-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Navigation"
            tabIndex={-1}
            className="drawer-panel absolute inset-y-0 left-0 w-[280px] max-w-[85vw] border-r border-line bg-bg shadow-card-hover outline-none"
            // Any link tap closes the drawer, covering same-route links that
            // do not change the pathname.
            onClick={(event) => {
              if ((event.target as HTMLElement).closest("a") !== null) {
                setOpen(false);
              }
            }}
          >
            <Sidebar variant="drawer" />
          </div>
        </div>
      )}
    </div>
  );
}
