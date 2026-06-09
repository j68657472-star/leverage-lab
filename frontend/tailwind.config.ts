import type { Config } from "tailwindcss";
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0f172a",
        muted: "#64748b",
        line: "#e2e8f0",
        pos: "#059669",
        neg: "#dc2626",
        brand: "#1d4ed8",
        branddark: "#1e3a8a",
        surface: "#ffffff",
        canvas: "#f8fafc",
      },
      borderRadius: { xl: "0.875rem", "2xl": "1.125rem" },
      boxShadow: { card: "0 1px 2px rgba(15,23,42,0.04), 0 1px 3px rgba(15,23,42,0.06)" },
    },
  },
  plugins: [],
};
export default config;
