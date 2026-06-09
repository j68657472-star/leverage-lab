"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, RunSummary } from "@/lib/api";
import { useAnonId } from "@/lib/user";
import { fmtDate, fmtMoney, fmtPct, signClass } from "@/lib/format";
import { Card, Spinner, MetricTile, InfoBanner } from "@/components/ui";
import { AllocationBar } from "@/components/Charts";
import { ASSET_COLORS } from "@/lib/assets";

export default function Dashboard() {
  const uid = useAnonId();
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  const [papers, setPapers] = useState<any[] | null>(null);
  const [latestSignal, setLatestSignal] = useState<any | null>(null);

  useEffect(() => {
    if (!uid) return;
    api.listRuns(uid).then(setRuns).catch(() => setRuns([]));
    api.listPaper(uid).then(setPapers).catch(() => setPapers([]));
  }, [uid]);

  // Pull the latest signal from the most recent completed run, if any.
  useEffect(() => {
    if (!runs || runs.length === 0) return;
    const done = runs.find((r) => r.status === "complete");
    if (!done) return;
    api
      .signals(done.run_id)
      .then((s) => setLatestSignal(s[s.length - 1] || null))
      .catch(() => {});
  }, [runs]);

  const latestPaper = papers && papers.length ? papers[0] : null;

  return (
    <div className="space-y-6">
      {/* Hero */}
      <div className="card overflow-hidden">
        <div className="grid gap-6 p-6 md:grid-cols-[1.3fr_1fr] md:p-8">
          <div>
            <span className="pill bg-blue-50 text-branddark">Research tool</span>
            <h1 className="mt-3 text-2xl font-bold tracking-tight text-ink md:text-3xl">
              Backtest a leveraged ETF strategy in seconds.
            </h1>
            <p className="mt-2 max-w-lg text-sm text-muted">
              Test a rules-based TQQQ / SOXL strategy over 5–10 years, see how it
              compares to SPY, and simulate it forward with paper trading. No
              login, no real money.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <Link href="/backtest" className="btn-primary">
                Run a backtest →
              </Link>
              <Link href="/paper" className="btn-secondary">
                Start paper trading
              </Link>
            </div>
          </div>
          <div className="rounded-xl border border-line bg-canvas p-5">
            <div className="text-xs font-semibold uppercase tracking-wide text-muted">
              How it works
            </div>
            <ol className="mt-3 space-y-3 text-sm text-ink">
              {[
                "Set your starting capital and date range.",
                "We run the strategy day-by-day with no look-ahead.",
                "Review performance, trades, and holdings — then save it.",
              ].map((t, i) => (
                <li key={i} className="flex gap-3">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand text-xs font-bold text-white">
                    {i + 1}
                  </span>
                  <span>{t}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </div>

      {/* Quick status row */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricTile
          label="Saved backtests"
          value={runs == null ? "…" : String(runs.length)}
          sub="Your experiments"
        />
        <MetricTile
          label="Paper portfolio value"
          value={latestPaper ? fmtMoney(latestPaper.current_value) : "—"}
          sub={latestPaper ? latestPaper.name : "No paper portfolio yet"}
        />
        <MetricTile
          label="Latest signal"
          value={
            latestSignal
              ? `${latestSignal.tqqq_signal ? "TQQQ on" : "TQQQ off"} · ${
                  latestSignal.soxl_signal ? "SOXL on" : "SOXL off"
                }`
              : "—"
          }
          sub={latestSignal ? fmtDate(latestSignal.date) : "Run a backtest first"}
        />
        <MetricTile
          label="Best saved CAGR"
          value={
            runs && runs.length
              ? fmtPct(
                  Math.max(...runs.filter((r) => r.cagr != null).map((r) => r.cagr!))
                )
              : "—"
          }
          sub="Across your runs"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        {/* Recent runs */}
        <Card>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-bold text-ink">Recent backtests</h2>
            <Link href="/saved-runs" className="text-sm font-medium text-brand">
              View all
            </Link>
          </div>
          {runs == null ? (
            <Spinner />
          ) : runs.length === 0 ? (
            <div className="rounded-xl border border-dashed border-line p-8 text-center">
              <p className="text-sm text-muted">
                No backtests yet. Your saved runs will appear here.
              </p>
              <Link href="/backtest" className="btn-primary mt-4">
                Run your first backtest
              </Link>
            </div>
          ) : (
            <div className="divide-y divide-line">
              {runs.slice(0, 5).map((r) => (
                <Link
                  key={r.run_id}
                  href={`/backtest/${r.run_id}`}
                  className="flex items-center justify-between gap-3 py-3 hover:opacity-80"
                >
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold text-ink">
                      {r.run_name}
                    </div>
                    <div className="text-xs text-muted">
                      {fmtDate(r.start_date)} – {fmtDate(r.end_date)}
                    </div>
                  </div>
                  <div className="flex items-center gap-5 text-right">
                    <div>
                      <div className={`text-sm font-bold ${signClass(r.cagr)}`}>
                        {fmtPct(r.cagr)}
                      </div>
                      <div className="text-[11px] text-muted">CAGR</div>
                    </div>
                    <div className="hidden sm:block">
                      <div className={`text-sm font-bold ${signClass(r.max_drawdown)}`}>
                        {fmtPct(r.max_drawdown)}
                      </div>
                      <div className="text-[11px] text-muted">Max DD</div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </Card>

        {/* Current target weights */}
        <Card>
          <h2 className="mb-3 text-base font-bold text-ink">
            Current target weights
          </h2>
          {latestSignal ? (
            <>
              <AllocationBar
                weights={[
                  { label: "TQQQ", value: latestSignal.target_weight_tqqq, color: ASSET_COLORS.TQQQ },
                  { label: "SOXL", value: latestSignal.target_weight_soxl, color: ASSET_COLORS.SOXL },
                  { label: "GLD", value: latestSignal.target_weight_gld, color: ASSET_COLORS.GLD },
                  { label: "SVXY", value: latestSignal.target_weight_svxy, color: ASSET_COLORS.SVXY },
                  { label: "CASH", value: latestSignal.target_weight_cash, color: ASSET_COLORS.CASH },
                ]}
              />
              <p className="mt-4 text-xs leading-relaxed text-muted">
                {latestSignal.signal_reason}
              </p>
            </>
          ) : (
            <p className="text-sm text-muted">
              Run a backtest to see the strategy&apos;s most recent target
              allocation.
            </p>
          )}
        </Card>
      </div>

      <InfoBanner>
        This is a simulated research tool for educational use. It is not
        investment advice and is not connected to any brokerage.
      </InfoBanner>
    </div>
  );
}
