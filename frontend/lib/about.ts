// About-page content. SINGLE SOURCE OF TRUTH: edit this file to change the
// /about page. The page (app/about/page.tsx) is purely presentational.
//
// Voice: short and spoken, first person, no reflective filler. The person
// behind the tool, stated plainly, then the facts.

export interface Credential {
  org: string;
  detail: string;
}

export interface AboutLink {
  label: string;
  href: string;
}

export interface About {
  name: string;
  greeting: string;
  /** Natural photo in /public, shown small. No gradient frame, not circular. */
  photo: string;
  /** Bio paragraphs, first person, rendered in order. Kept short. */
  bio: string[];
  /** Factual credentials, most relevant first. */
  credentials: Credential[];
  /** Plain text links. */
  links: AboutLink[];
}

export const about: About = {
  name: "Nikolas Savio",
  greeting: "Hi, I'm Nikolas.",
  photo: "/nikolas.jpg",
  bio: [
    "I built Investment Intelligence because I wanted one place to move from company filings to a first-pass investment view without losing the audit trail.",
    "I study Risk Management and Financial Engineering at Imperial College Business School. Before moving into finance, I trained as a mechatronics engineer at Glasgow and worked on the university's Formula Student car. That background still shapes how I approach financial work: define the inputs, show the calculation, test the result, and state what remains uncertain.",
    "The tool is a personal project and is still developing. I use it to study public companies, practise valuation, and test investment cases. I have made the formulas and sources visible so users can check the work rather than accept an unexplained output.",
    "I would value feedback, especially where a calculation, data mapping, or workflow could be clearer.",
  ],
  credentials: [
    {
      org: "Imperial College Business School",
      detail: "MSc Risk Management and Financial Engineering",
    },
    {
      org: "University of Glasgow",
      detail: "BEng Mechatronics Engineering, First Class Honours",
    },
    {
      org: "Oxford Saïd Business School",
      detail: "Private-markets programme",
    },
    {
      org: "Published research",
      detail: "Carbon-nanotube strain sensors, ICMR 2024",
    },
  ],
  links: [
    { label: "LinkedIn", href: "https://www.linkedin.com/in/nikolasdionsavio/" },
    { label: "Portfolio", href: "https://nikolasdionsavio.com" },
    { label: "Published paper", href: "https://doi.org/10.1051/matecconf/202440104011" },
    { label: "Email", href: "mailto:contact@nikolasdionsavio.com" },
  ],
};
