import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#f6f7f9",
        surface: "#ffffff",
        ink: "#0f172a",
        brand: "#1e3a5f",
        accent: "#0d9488",
        negative: "#b91c1c",
        warn: "#b45309",
      },
    },
  },
  plugins: [],
};

export default config;
