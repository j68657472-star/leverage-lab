import type { Metadata } from "next";
import "./globals.css";
import Shell from "@/components/Shell";

export const metadata: Metadata = {
  title: "Leverage Lab — Leveraged ETF Strategy Backtester",
  description:
    "Backtest and paper-trade a leveraged ETF strategy (TQQQ / SOXL / GLD / SVXY). Research tool only — not investment advice.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
