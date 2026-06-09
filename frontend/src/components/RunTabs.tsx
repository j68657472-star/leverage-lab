"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

export default function RunTabs({ runId }: { runId: string }) {
  const pathname = usePathname();
  const tabs = [
    { href: `/backtest/${runId}`, label: "Summary" },
    { href: `/backtest/${runId}/trades`, label: "Trades" },
    { href: `/backtest/${runId}/holdings`, label: "Holdings" },
    { href: `/backtest/${runId}/signals`, label: "Signals" },
  ];
  return (
    <div className="flex gap-1 overflow-x-auto rounded-xl border border-line bg-white p-1">
      {tabs.map((t) => {
        const active = pathname === t.href;
        return (
          <Link
            key={t.href}
            href={t.href}
            className={`whitespace-nowrap rounded-lg px-4 py-2 text-sm font-semibold transition-colors ${
              active ? "bg-canvas text-ink" : "text-muted hover:text-ink"
            }`}
          >
            {t.label}
          </Link>
        );
      })}
    </div>
  );
}
