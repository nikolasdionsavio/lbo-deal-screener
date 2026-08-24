// Search identity for the site.
//
// The goal this exists to serve: someone searches "Nikolas Dion Savio" and
// this site is one of the results. That needs three things Google cannot
// infer on its own.
//
// 1. The full name has to appear. The site says "Nikolas Savio" everywhere,
//    which is a different string from the one people search.
// 2. The site has to be crawlable and enumerable, which means a robots.txt
//    and a sitemap. Both were 404 before this file existed.
// 3. The person has to be stated as an entity, not left to be guessed from
//    prose. That is Person schema, and its most load-bearing property is
//    sameAs: it says the Nikolas Savio here is the one at that LinkedIn and
//    that portfolio, rather than leaving Google to infer it slowly.
//
// Every fact below is already claimed on /about (lib/about.ts) or on a live
// property. Nothing here is asserted that the site does not already stand
// behind.

export const SITE_URL = "https://nikolasproject.com";
export const SITE_NAME = "Investment Intelligence";

/** Formal name, as searched and as it appears on the LinkedIn slug. */
export const FULL_NAME = "Nikolas Dion Savio";
/** What the product calls him. Schema needs both, or they read as two people. */
export const SHORT_NAME = "Nikolas Savio";

/** Verified, live URLs only. A wrong sameAs is worse than a missing one: it
 *  merges this person with somebody else. */
export const PROFILES = [
  "https://www.linkedin.com/in/nikolasdionsavio/",
  "https://nikolasdionsavio.com",
] as const;

const personId = `${SITE_URL}/#nikolas-dion-savio`;

export const personSchema = {
  "@type": "Person",
  "@id": personId,
  name: FULL_NAME,
  alternateName: SHORT_NAME,
  url: "https://nikolasdionsavio.com",
  mainEntityOfPage: `${SITE_URL}/about`,
  image: `${SITE_URL}/nikolas.jpg`,
  description:
    "Risk Management and Financial Engineering postgraduate at Imperial College Business School, previously a mechatronics engineer at Glasgow. Builds Investment Intelligence, a company research tool that shows the source or assumption behind every calculated figure.",
  sameAs: [...PROFILES],
  affiliation: {
    "@type": "CollegeOrUniversity",
    name: "Imperial College Business School",
  },
  alumniOf: [
    {
      "@type": "CollegeOrUniversity",
      name: "Imperial College Business School",
    },
    { "@type": "CollegeOrUniversity", name: "University of Glasgow" },
    { "@type": "CollegeOrUniversity", name: "University of Oxford" },
  ],
  knowsAbout: [
    "Equity research",
    "Leveraged buyout modelling",
    "Financial statement analysis",
    "Risk management",
    "Financial engineering",
  ],
};

/** The site itself, attributed to the person, so the two are one entity in
 *  the graph rather than a page and an unrelated name that appears on it. */
export const siteSchema = {
  "@type": "WebSite",
  "@id": `${SITE_URL}/#website`,
  url: SITE_URL,
  name: SITE_NAME,
  description:
    "Company research you can check. Screen every US-listed filer, then work through one company's filings, operating results, valuation, peer set and a simplified LBO case.",
  inLanguage: "en",
  author: { "@id": personId },
  creator: { "@id": personId },
  publisher: { "@id": personId },
};

export const siteGraph = {
  "@context": "https://schema.org",
  "@graph": [personSchema, siteSchema],
};

/** Routes worth having in the index. Auth and per-company pages are left out
 *  deliberately: see app/robots.ts. */
export const INDEXABLE_ROUTES = [
  "/",
  "/about",
  "/screen",
  "/methodology",
  "/how-to-use",
  "/whats-new",
  "/changelog",
  "/contact",
  "/markets/overview",
  "/markets/screener",
  "/markets/heatmap",
  "/markets/calendar",
] as const;
