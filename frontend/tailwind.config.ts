import type { Config } from "tailwindcss";

// Semantic color names map onto the CSS variables defined in app/globals.css
// (light on :root, dark on .dark). Variables hold full color values, so
// Tailwind opacity modifiers (e.g. bg-brand/50) must not be used on them;
// soft tints have dedicated tokens (brand-soft, warn-soft, ...).
const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        surface: {
          DEFAULT: "var(--surface)",
          raised: "var(--surface-raised)",
          sunken: "var(--surface-sunken)",
        },
        ink: {
          DEFAULT: "var(--ink)",
          secondary: "var(--ink-secondary)",
          muted: "var(--ink-muted)",
        },
        line: {
          DEFAULT: "var(--line)",
          strong: "var(--line-strong)",
        },
        brand: {
          DEFAULT: "var(--brand)",
          hover: "var(--brand-hover)",
          soft: "var(--brand-soft)",
          text: "var(--brand-text)",
        },
        accent: {
          DEFAULT: "var(--accent)",
          soft: "var(--accent-soft)",
        },
        positive: {
          text: "var(--positive-text)",
          soft: "var(--positive-soft)",
        },
        // Source / document links are the only blue in the system.
        link: {
          DEFAULT: "var(--link)",
          hover: "var(--link-hover)",
        },
        // Provenance: filed figures are plain ink; ochre marks editable
        // assumptions only.
        filed: "var(--filed)",
        assumption: {
          DEFAULT: "var(--assumption)",
          soft: "var(--assumption-soft)",
        },
        negative: {
          DEFAULT: "var(--negative)",
          hover: "var(--negative-hover)",
          text: "var(--negative-text)",
          soft: "var(--negative-soft)",
        },
        warn: {
          DEFAULT: "var(--warn)",
          text: "var(--warn-text)",
          soft: "var(--warn-soft)",
        },
        // Screening data roles. Colour is information here: leverage is read
        // by band, and every value still shows its number so colour is never
        // the only carrier of meaning.
        lev: {
          low: "var(--lev-low)",
          mid: "var(--lev-mid)",
          high: "var(--lev-high)",
          "low-soft": "var(--lev-low-soft)",
          "mid-soft": "var(--lev-mid-soft)",
          "high-soft": "var(--lev-high-soft)",
        },
        metric: {
          profit: "var(--metric-profit)",
          "profit-soft": "var(--metric-profit-soft)",
        },
        action: {
          DEFAULT: "var(--action)",
          hover: "var(--action-hover)",
          ink: "var(--action-ink)",
        },
        group: {
          size: "var(--group-size)",
          profit: "var(--group-profit)",
          balance: "var(--group-balance)",
          classify: "var(--group-classify)",
          quality: "var(--group-quality)",
          "size-soft": "var(--group-size-soft)",
          "profit-soft": "var(--group-profit-soft)",
          "balance-soft": "var(--group-balance-soft)",
          "classify-soft": "var(--group-classify-soft)",
          "quality-soft": "var(--group-quality-soft)",
          "size-rule": "var(--group-size-rule)",
          "profit-rule": "var(--group-profit-rule)",
          "balance-rule": "var(--group-balance-rule)",
          "classify-rule": "var(--group-classify-rule)",
          "quality-rule": "var(--group-quality-rule)",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        // Editorial only. Prefer a locally installed Charter (Matthew Carter's
        // Bitstream face, not on Google Fonts); fall back to Charis SIL, which
        // is derived from Charter and ships here as the webfont.
        display: [
          "Charter",
          "Bitstream Charter",
          "var(--font-charis)",
          "Charis SIL",
          "Georgia",
          "serif",
        ],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      // Restrained radii (redesign): 3px controls, 5px search, 6px drawers /
      // menus / chart frames. Nothing larger reads as a research surface, not a
      // SaaS card. Everything above md is capped at 6px so untouched components
      // pick up the discipline; rounded-full stays for the few true pills.
      // DESIGN.md caps radius at 6px and bans pill buttons. Every key was
      // capped except `full`, which fell through to Tailwind's 9999px, so 24
      // pills had grown across the app. Capping it here retires all of them at
      // once; genuinely circular things (status dots, avatars) opt in through
      // `rounded-circle`, which makes the intent visible at the call site
      // instead of looking like another stray pill.
      borderRadius: {
        DEFAULT: "3px",
        sm: "3px",
        md: "5px",
        lg: "6px",
        xl: "6px",
        "2xl": "6px",
        "3xl": "6px",
        full: "6px",
        circle: "9999px",
      },
      boxShadow: {
        card: "var(--shadow-card)",
        "card-hover": "var(--shadow-card-hover)",
        pop: "var(--shadow-pop)",
      },
    },
  },
  plugins: [],
};

export default config;
