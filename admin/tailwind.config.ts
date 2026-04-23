import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-inter)", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      colors: {
        surface: {
          DEFAULT: "#f4f6f9",
          card: "#ffffff",
        },
        accent: {
          DEFAULT: "#2563eb",
          muted: "#93c5fd",
        },
        coral: {
          DEFAULT: "#f97316",
        },
        ink: {
          DEFAULT: "#0f172a",
          muted: "#64748b",
        },
      },
      boxShadow: {
        card: "0 1px 3px rgba(15, 23, 42, 0.06), 0 8px 24px rgba(15, 23, 42, 0.04)",
      },
      borderRadius: {
        xl: "14px",
      },
    },
  },
  plugins: [],
};

export default config;
