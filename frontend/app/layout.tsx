import type { Metadata } from "next";
import { Source_Sans_3, Charis_SIL, Azeret_Mono } from "next/font/google";
import "./globals.css";
import Shell from "@/components/chrome/Shell";
import { AuthProvider } from "@/lib/auth";
import { ThemeProvider } from "@/lib/theme";

// Three roles, per DESIGN.md:
//  - Source Sans 3: the whole interface (nav, body, buttons, forms, tables).
//  - Charter: authored editorial only (homepage statement, Nikolas's notes,
//    methodology intros, memo titles). Charter is Matthew Carter's Bitstream
//    face and is NOT on Google Fonts, so the stack prefers a locally installed
//    Charter and falls back to Charis SIL, which is derived from Charter and
//    is served here as the webfont. See tailwind.config fontFamily.display.
//  - Azeret Mono: data only (tickers, dates, filing types, formula variables,
//    source refs, model assumptions, technical metadata).
const sourceSans = Source_Sans_3({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sans",
});

const charisSil = Charis_SIL({
  subsets: ["latin"],
  weight: ["400", "700"],
  style: ["normal", "italic"],
  display: "swap",
  variable: "--font-charis",
});

const azeretMono = Azeret_Mono({
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
      className={`${sourceSans.variable} ${charisSil.variable} ${azeretMono.variable}`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="font-sans">
        <ThemeProvider>
          <AuthProvider>
            <Shell>{children}</Shell>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
