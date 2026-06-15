// About-page content. SINGLE SOURCE OF TRUTH — edit this file to change the
// /about page. The page (app/about/page.tsx) is purely presentational and
// reads everything from the exported `about` object below.
//
// Values marked "[... to be filled]" are placeholders; replace them with real
// content. Links with href "#" render de-emphasized until a real URL is set.

export type AboutLinkKind = "linkedin" | "web" | "email" | "generic";

export interface AboutLink {
  label: string;
  href: string;
  kind: AboutLinkKind;
}

export interface About {
  name: string;
  role: string;
  /** Bio paragraphs, rendered in order as prose. */
  bio: string[];
  links: AboutLink[];
}

export const about: About = {
  name: "Nikolas Dion Savio",
  role: "[role — to be filled]",
  bio: ["[Short bio paragraph — to be filled.]"],
  links: [
    { label: "LinkedIn", href: "#", kind: "linkedin" },
    { label: "Personal site", href: "https://nikolasdionsavio.com", kind: "web" },
    { label: "Email", href: "mailto:contact@nikolasdionsavio.com", kind: "email" },
  ],
};
