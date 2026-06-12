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
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "Georgia", "serif"],
      },
      // Radius scale per DESIGN.md Aesthetic v2: 8px controls, 14px cards,
      // 999px pills. Tailwind defaults supply 16px (2xl, hero prompt box)
      // and 24px (3xl, hero container).
      borderRadius: {
        DEFAULT: "8px",
        lg: "14px",
      },
      boxShadow: {
        card: "var(--shadow-card)",
        "card-hover": "var(--shadow-card-hover)",
      },
    },
  },
  plugins: [],
};

export default config;
