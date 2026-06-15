// About-page content. SINGLE SOURCE OF TRUTH — edit this file to change the
// /about page. The page (app/about/page.tsx) is purely presentational and
// reads everything from the exported `about` object below.

export type AboutLinkKind = "linkedin" | "web" | "email" | "generic";

export interface AboutLink {
  label: string;
  href: string;
  kind: AboutLinkKind;
}

export interface AboutHighlight {
  /** Short bold lead-in (e.g. "MSc, Imperial College Business School"). */
  title: string;
  /** One-line detail under the title. */
  detail: string;
}

export interface About {
  name: string;
  role: string;
  /** One-line positioning shown under the role. */
  tagline: string;
  /** Bio paragraphs, rendered in order as prose. */
  bio: string[];
  /** Selected credentials, rendered as a marked list. */
  highlights: AboutHighlight[];
  links: AboutLink[];
}

export const about: About = {
  name: "Nikolas Dion Savio",
  role: "Financial engineer",
  tagline: "Quantitative finance, private markets, and the software behind them.",
  bio: [
    "Nikolas Dion Savio came to markets through engineering. He trained as an engineer at the University of Glasgow, running cost and components for the university's Formula Student team to a first-place finish at the UK competition and co-authoring published research on carbon-nanotube strain sensors, before turning to finance with an MSc in Risk Management and Financial Engineering at Imperial College Business School and a practitioner-led private-markets programme at Oxford's Saïd Business School.",
    "That route shows in how he works. He builds three-statement and LBO models from first principles, handling circular references, working-capital mechanics, and debt schedules by hand; he benchmarks fund returns against public-market equivalents; and he writes the code that turns the analysis into software. His projects range from a machine-learning pipeline forecasting investment-grade corporate-bond excess returns on thirty years of FRED data, to an implementation of the Avellaneda–Stoikov market-making model built from the mathematics up, to GARCH time-series work on equities and rates.",
    "Investment Intelligence is one of those builds. It applies the discipline he uses on a buyout target, traceable numbers, explicit assumptions, nothing taken on faith, to any US-listed public company, and puts it in a tool anyone can open.",
  ],
  highlights: [
    {
      title: "MSc, Imperial College Business School",
      detail: "Risk Management and Financial Engineering, London",
    },
    {
      title: "Private markets, Oxford Saïd Business School",
      detail: "Practitioner-led programme, from origination to exit",
    },
    {
      title: "Published researcher",
      detail:
        "Carbon-nanotube strain sensors, MATEC Web of Conferences (ICMR 2024)",
    },
    {
      title: "Formula Student UK, 1st place",
      detail: "Cost and components engineer, University of Glasgow racing team",
    },
    {
      title: "Trading competition, finished #1",
      detail: "Top of all MSc and MBA entrants, +231% from a -31% drawdown",
    },
  ],
  links: [
    {
      label: "LinkedIn",
      href: "https://www.linkedin.com/in/nikolasdionsavio/",
      kind: "linkedin",
    },
    { label: "Portfolio", href: "https://nikolasdionsavio.com", kind: "web" },
    { label: "nikolassavio.com", href: "https://nikolassavio.com", kind: "web" },
    { label: "Aviora Clinic", href: "https://avioraclinic.com", kind: "generic" },
    {
      label: "Published paper",
      href: "https://doi.org/10.1051/matecconf/202440104011",
      kind: "generic",
    },
    {
      label: "Email",
      href: "mailto:contact@nikolasdionsavio.com",
      kind: "email",
    },
  ],
};
