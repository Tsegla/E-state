import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        forest: {
          DEFAULT: "#3F5E3B",
          600: "#365233",
          700: "#2D4529",
        },
        olive: {
          DEFAULT: "#B6B774",
          700: "#9FA062",
        },
        sand: {
          DEFAULT: "#E3C9A9",
          300: "#EEDCC4",
        },
        rose: {
          DEFAULT: "#C97A7F",
          700: "#B06166",
        },
        surface: {
          DEFAULT: "#FFFFFF",
          muted: "#F7F6F2",
        },
        ink: {
          DEFAULT: "#1F2421",
          muted: "#545B54",
        },
        success: { DEFAULT: "#3F5E3B" },
        warning: { DEFAULT: "#C79A3C" },
        info: { DEFAULT: "#4F6E8F" },
        danger: { DEFAULT: "#C97A7F" },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "Inter", "ui-sans-serif", "system-ui"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      boxShadow: {
        soft: "0 1px 2px rgba(31,36,33,0.04), 0 6px 20px rgba(31,36,33,0.04)",
        card: "0 1px 2px rgba(31,36,33,0.04), 0 1px 3px rgba(31,36,33,0.03)",
        elevated:
          "0 1px 2px rgba(31,36,33,0.05), 0 12px 30px rgba(31,36,33,0.07)",
      },
      borderRadius: {
        lg: "0.625rem",
        xl: "0.875rem",
        "2xl": "1.125rem",
        "3xl": "1.5rem",
      },
      keyframes: {
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-in": "fade-in 200ms ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
