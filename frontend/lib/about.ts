// About-page content. SINGLE SOURCE OF TRUTH — edit this file to change the
// /about page. The page (app/about/page.tsx) is purely presentational and
// reads everything from the exported `about` object below.

export type AboutLinkKind = "linkedin" | "web" | "email" | "generic";

export interface AboutLink {
  label: string;
  href: string;
  kind: AboutLinkKind;
}

export type HighlightIcon =
  | "school"
  | "markets"
  | "research"
  | "racing"
  | "trading";
export type HighlightColor =
  | "blue"
  | "indigo"
  | "teal"
  | "amber"
  | "emerald";

export interface AboutHighlight {
  title: string;
  detail: string;
  icon: HighlightIcon;
  color: HighlightColor;
}

export interface About {
  name: string;
  role: string;
  tagline: string;
  /** Photo in /public. */
  photo: string;
  /** Warm one-line greeting shown above the name. */
  greeting: string;
  /** Bio paragraphs, first person, rendered in order. */
  bio: string[];
  highlights: AboutHighlight[];
  links: AboutLink[];
}

export const about: About = {
  name: "Nikolas Dion Savio",
  role: "Financial engineer",
  tagline: "Quantitative finance, private markets, and the software behind them.",
  photo: "/nikolas.jpg",
  greeting: "Hi, I'm Nikolas",
  bio: [
    "I'm a finance person at heart with an engineer's habits: I like to understand exactly how something works, then build it myself. Markets are where that curiosity settled. I find them genuinely interesting, the way prices carry information, the way a business becomes a number, the way risk and return trade off, and I like the discipline of settling questions with real figures instead of opinion.",
    "Most of what I do is finance. I build three-statement and LBO models from first principles, circular references and debt schedules included, value companies, and benchmark fund returns against the public markets. I trained for it with an MSc in Risk Management and Financial Engineering at Imperial College Business School and a private-markets programme at Oxford's Saïd Business School, and I stay sharp by building: a machine-learning pipeline that forecasts corporate-bond returns, the Avellaneda–Stoikov market-making model coded from the mathematics up, and a trading competition I finished first in against the MSc and MBA field. Private equity and the mechanics of valuation are the parts I enjoy most.",
    "The engineering came first. I studied it at the University of Glasgow, ran cost and components for our Formula Student team to a first-place finish at the UK competition, and co-authored a published paper on carbon-nanotube strain sensors. It taught me to build things properly and to respect the numbers, which is how I approach a company today.",
    "Investment Intelligence is where all of that meets. I wanted a tool that treats any US-listed company the way I would treat a buyout target, traceable figures, assumptions you can see, nothing taken on faith, and that anyone can pick up and use. Take a look around, and feel free to get in touch.",
  ],
  highlights: [
    {
      title: "Imperial College Business School",
      detail: "MSc, Risk Management and Financial Engineering",
      icon: "school",
      color: "blue",
    },
    {
      title: "Oxford Saïd Business School",
      detail: "Private-markets programme, origination to exit",
      icon: "markets",
      color: "indigo",
    },
    {
      title: "Published researcher",
      detail: "Carbon-nanotube strain sensors, ICMR 2024",
      icon: "research",
      color: "teal",
    },
    {
      title: "Formula Student UK, 1st place",
      detail: "Cost and components engineer, University of Glasgow",
      icon: "racing",
      color: "amber",
    },
    {
      title: "Trading competition, finished 1st",
      detail: "Top of the MSc and MBA field, +231% from a -31% drawdown",
      icon: "trading",
      color: "emerald",
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
