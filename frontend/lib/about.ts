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
    "Welcome, and thanks for taking a look around. I tend to get curious about how things actually work, and once I start pulling at a thread I usually end up building something to understand it better. Markets pulled me in that way and never quite let go. I like how much sits inside a single share price, and how a whole company can be reasoned about as a set of numbers you have to defend. Settling a question with real figures rather than a strong hunch is the part I find most satisfying.",
    "These days most of what I do is finance. I build financial models from scratch, the full three-statement and LBO kind, working through the circular references and debt schedules that tend to scare people off, and I lean on them to value companies and see how funds have really done against the market. I picked most of this up through an MSc in Risk Management and Financial Engineering at Imperial College Business School, and later a private-markets programme at Oxford's Saïd Business School. The learning carried on outside the coursework, mostly because I find it hard to leave an idea alone. I have put together a small machine-learning pipeline for bond returns, rebuilt the Avellaneda-Stoikov market-making model from the underlying maths just to see if I could, poked around in time-series work on equities and rates, and somehow came out on top of a trading competition against the MSc and MBA crowd. Private equity and the mechanics of valuation are what I keep finding my way back to.",
    "Before any of that, I trained as an engineer. I studied at the University of Glasgow and spent most of my spare time with the Formula Student team, looking after cost and components for a car that the team took to first place at the UK competition. Around the same time I helped write a paper on carbon-nanotube strain sensors. Engineering taught me to build things carefully and to take numbers seriously, and that habit has stayed with me ever since.",
    "Investment Intelligence grew out of all of that. It runs the same kind of analysis I would do on a buyout target, the fundamentals, the valuation, a five-year LBO model and a memo, and lets you point it at any US-listed company. Every figure shows the formula and the source it came from, so nothing asks you to take my word for it. Have a proper look around, and if you ever want to talk shop or tell me what could be better, my details are just below.",
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
