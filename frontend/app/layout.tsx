import type { Metadata } from "next";
import { FULL_NAME, SITE_NAME, SITE_URL, siteGraph } from "@/lib/seo";
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

// Search identity lives in lib/seo.ts. The title carries the full name
// because "Nikolas Savio" is what the site says and "Nikolas Dion Savio" is
// what people search, and those are different strings to a search engine.
export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: `${SITE_NAME} by ${FULL_NAME}`,
    template: `%s · ${SITE_NAME}`,
  },
  description:
    `Company research you can check, built by ${FULL_NAME}. Screen every US-listed filer, then work through one company's filings, operating KPIs, valuation, peer set, and a five-year LBO model. Every calculated figure shows the source or assumption behind it.`,
  applicationName: SITE_NAME,
  authors: [{ name: FULL_NAME, url: "https://nikolasdionsavio.com" }],
  creator: FULL_NAME,
  publisher: FULL_NAME,
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    siteName: SITE_NAME,
    url: SITE_URL,
    title: `${SITE_NAME} by ${FULL_NAME}`,
    description:
      `Company research you can check, built by ${FULL_NAME}. Every calculated figure shows the source or assumption behind it.`,
    locale: "en_GB",
  },
  twitter: {
    card: "summary_large_image",
    title: `${SITE_NAME} by ${FULL_NAME}`,
    description:
      `Company research you can check, built by ${FULL_NAME}.`,
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true, "max-snippet": -1, "max-image-preview": "large" },
  },
};

// Applies the persisted (or system) theme class before first paint so the
// page never flashes the wrong theme. Must stay dependency-free and tiny.
// Dark is the house style now: the war table is what the product looks like,
// so it is what a first visit gets regardless of OS preference. Light remains
// a deliberate choice and is remembered once made.
const themeInitScript = `(function(){try{var t=localStorage.getItem("theme");document.documentElement.classList.toggle("dark",t!=="light");}catch(e){document.documentElement.classList.add("dark");}})();`;

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
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(siteGraph) }}
        />
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
