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
    "Hello, and thank you for stopping by. I really hope you find something here that is useful to you. I have always been the sort of person who gets quietly curious about how things work, and that same curiosity is what drew me toward markets and made me want to understand them properly. For me there is a genuine pleasure in studying a company patiently through its numbers and watching the picture slowly come together. I would much rather sit with the figures for a while than reach for a quick answer.",
    "Most of my time these days goes into finance. I love building financial models from the ground up and using them to understand how a business really works and what it might be worth. Much of what I know has come from an MSc in Risk Management and Financial Engineering at Imperial College Business School and a private-markets programme at Oxford's Saïd Business School, and I am very much still learning as I go. On the side I like to tinker with small projects, mostly because building something is how I come to understand it. Private equity and the patient craft of valuation are the areas I keep finding myself drawn to.",
    "Before finance, I trained as an engineer. I spent my university years at Glasgow and a good part of my free time with the Formula Student team, where I looked after the cost and components side of the car. Those years taught me to build things with care and to treat the numbers with respect, and that has stayed with me in everything since. I still owe a lot to that early, hands-on way of working.",
    "Investment Intelligence came out of wanting a tool like this for myself, and then hoping other people might find it helpful too. It tries to do the careful, honest kind of analysis I would want to rely on, and it shows the formula and source behind every figure so you never have to simply take my word for anything. Please feel free to look around at your own pace. If you ever want to share a thought or tell me where it could be better, I would be really glad to hear from you, and my details are just below.",
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
      title: "Formula Student, University of Glasgow",
      detail: "Cost and components engineer; first at the UK final",
      icon: "racing",
      color: "amber",
    },
    {
      title: "Trading competition",
      detail: "Finished first among the MSc and MBA entrants",
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
