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
    "I'm a financial engineer with a background in engineering. I studied engineering at the University of Glasgow, where I ran cost and components for the Formula Student team that placed first at the UK competition and co-authored a published paper on carbon-nanotube strain sensors. I then moved into finance, with an MSc in Risk Management and Financial Engineering at Imperial College Business School and a private-markets programme at Oxford's Saïd Business School.",
    "My work sits where engineering and finance meet. I build three-statement and LBO models from first principles, including the circular references and debt schedules, and I benchmark fund returns against public-market equivalents. I also write the software that turns the analysis into something usable. Recent projects include a machine-learning pipeline for forecasting investment-grade corporate-bond returns, an implementation of the Avellaneda–Stoikov market-making model from the mathematics up, and a first-place finish in a trading competition against the MSc and MBA cohort.",
    "Investment Intelligence brings that together. It treats any US-listed public company the way I would treat a buyout target: traceable figures, visible assumptions, and nothing taken on faith. It is built to be open for anyone to use.",
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
