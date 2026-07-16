import type { Metadata } from "next";
import { Source_Sans_3, Source_Serif_4, DM_Mono } from "next/font/google";
import "./globals.css";
import TopBar from "@/components/chrome/TopBar";
import Sidebar from "@/components/Sidebar";
import Link from "next/link";
import { AuthProvider } from "@/lib/auth";
import { ThemeProvider } from "@/lib/theme";
import { RELEASES } from "@/lib/version";

// Humanist sans for the whole interface (nav, labels, body, tables). Source
// Serif 4 is reserved for short editorial text only (founder note, memo title,
// methodology intro). DM Mono carries tickers, dates, source refs, formulas and
// aligned financial metadata.
const sourceSans = Source_Sans_3({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sans",
});

const sourceSerif = Source_Serif_4({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-display",
});

const dmMono = DM_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  display: "swap",
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "Investment Intelligence",
  description:
    "Company research you can check. Search a US-listed company and work through its filings, operating KPIs, valuation, peer set, and a five-year LBO model. Every calculated figure shows the source or assumption behind it.",
};

// Applies the persisted (or system) theme class before first paint so the
// page never flashes the wrong theme. Must stay dependency-free and tiny.
const themeInitScript = `(function(){try{var t=localStorage.getItem("theme");var d=t==="dark"||(t!=="light"&&window.matchMedia("(prefers-color-scheme: dark)").matches);document.documentElement.classList.toggle("dark",d);}catch(e){}})();`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${sourceSans.variable} ${sourceSerif.variable} ${dmMono.variable}`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="font-sans">
        <ThemeProvider>
          <AuthProvider>
            <div className="flex min-h-screen">
              <Sidebar />
              <div className="flex min-w-0 flex-1 flex-col">
                <TopBar />
                <main className="min-w-0 flex-1">{children}</main>
                <footer className="border-t border-line px-4 py-4 sm:px-8">
                  <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 font-mono text-xs text-ink-muted">
                    <span>Investment Intelligence · a personal research tool</span>
                    <Link
                      href="/changelog"
                      className="transition-colors hover:text-ink"
                    >
                      Last updated {RELEASES[0].date}
                    </Link>
                  </div>
                </footer>
              </div>
            </div>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
