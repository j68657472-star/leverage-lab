"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/", label: "Dashboard" },
  { href: "/backtest", label: "New Backtest" },
  { href: "/saved-runs", label: "Saved Runs" },
  { href: "/compare", label: "Compare" },
  { href: "/paper", label: "Paper Trading" },
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-line bg-surface/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link href="/" className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand text-sm font-bold text-white">
              L
            </span>
            <span className="text-[15px] font-bold tracking-tight text-ink">
              Leverage Lab
            </span>
          </Link>
          <nav className="hidden items-center gap-1 md:flex">
            {NAV.map((n) => (
              <Link
                key={n.href}
                href={n.href}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                  isActive(n.href)
                    ? "bg-canvas text-ink"
                    : "text-muted hover:bg-canvas hover:text-ink"
                }`}
              >
                {n.label}
              </Link>
            ))}
          </nav>
          <Link href="/backtest" className="btn-primary md:hidden">
            Run
          </Link>
        </div>
        {/* mobile nav */}
        <nav className="flex gap-1 overflow-x-auto border-t border-line px-3 py-2 md:hidden">
          {NAV.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              className={`whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium ${
                isActive(n.href) ? "bg-canvas text-ink" : "text-muted"
              }`}
            >
              {n.label}
            </Link>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
      <footer className="mx-auto max-w-6xl px-4 py-8 text-center text-xs text-muted">
        Simulated research tool · Not investment advice · Not connected to any broker
      </footer>
    </div>
  );
}
