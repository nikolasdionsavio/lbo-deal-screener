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
  tagline: "Quantitative finance and private markets, plus the code behind them.",
  photo: "/nikolas.jpg",
  greeting: "Hi, I'm Nikolas",
  bio: [
    "I'm a finance person with an engineer's habits. When something catches my interest I want to know how it actually works, and then I usually try to build it myself. Markets are where that settled. I like how much information sits inside a single price, and how a whole company eventually comes down to a number you can defend. The part I enjoy most is settling a question with real figures rather than a confident opinion.",
    "Most of what I do now is finance. I build financial models from scratch, the full three-statement and LBO kind, circular references and debt schedules included, and I use them to value companies and compare fund performance against the public markets. I trained for this with an MSc in Risk Management and Financial Engineering at Imperial College Business School and then a private-markets programme at Oxford's Saïd Business School. I keep building in between. There's a machine-learning pipeline that forecasts investment-grade bond returns, the Avellaneda-Stoikov market-making model written straight from the maths, some time-series work on equities and rates, and a trading competition I won against the MSc and MBA cohort. Private equity and the mechanics of valuation are the parts I keep coming back to.",
    "The engineering came first. I studied it at the University of Glasgow and spent most of my time on the Formula Student team, running cost and components for a car that placed first at the UK competition. I also co-authored a paper on carbon-nanotube strain sensors. That background taught me to build carefully and to trust what the numbers say. I still read a company the same way.",
    "Investment Intelligence is where this comes together. It runs the kind of analysis I would do on a buyout target, the fundamentals, the valuation, a five-year LBO model and a memo, and applies it to any US-listed company. Every number shows the formula and source behind it, so you can check the work yourself. Have a look around, and if you want to talk shop or send feedback, my details are below.",
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
