"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { use, useEffect, useState } from "react";
import { api, exportUrl, Metrics, RunDetail } from "@/lib/api";
import { useAnonId } from "@/lib/user";
import { fmtDate, fmtMoney, fmtNum, fmtPct, signClass } from "@/lib/format";
import { Card, ErrorBanner, MetricTile, Spinner, InfoBanner } from "@/components/ui";
import { DrawdownChart, EquityChart } from "@/components/Charts";
import RunTabs from "@/components/RunTabs";

export default function ResultPage({
  params,
}: {
  params: Promise<{ run_id: string }>;
}) {
  const { run_id } = use(params);
  const router = useRouter();
  const uid = useAnonId();

  const [run, setRun] = useState<RunDetail | null>(null);
  const [equity, setEquity] = useState<any[] | null>(null);
  const [drawdown, setDrawdown] = useState<any[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .getRun(run_id)
      .then(setRun)
      .catch((e) => setError(e.message));
    api.equity(run_id).then(setEquity).catch(() => setEquity([]));
    api.drawdown(run_id).then(setDrawdown).catch(() => setDrawdown([]));
  }, [run_id]);

  if (error) return <ErrorBanner message={error} />;
  if (!run) return <Card><Spinner label="Loading results…" /></Card>;

  if (run.status === "failed") {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold text-ink">{run.run_name}</h1>
        <ErrorBanner
          message={
            run.error_message ||
            "This backtest could not be completed (data may have been unavailable)."
          }
        />
        <Link href="/backtest" className="btn-primary">
          Try a new backtest
        </Link>
      </div>
    );
  }

  const byPeriod = (p: string) => run.metrics.find((m) => m.period_name === p);
  const full = byPeriod("full");

  async function duplicate() {
    setBusy(true);
    try {
      const dup = await api.duplicate(run_id);
      router.push(`/backtest/${dup.run_id}`);
    } catch (e: any) {
      setError(e.message);
      setBusy(false);
    }
  }

  async function startPaper() {
    if (!uid) return;
    setBusy(true);
    try {
      const p = await api.createPaper({
        anonymous_user_id: uid,
        name: `${run!.run_name} (paper)`,
        initial_capital: run!.initial_capital,
        params: run!.params,
      });
      router.push(`/paper/${p.portfolio_id}`);
    } catch (e: any) {
      setError(e.message);
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">
            {run.run_name}
          </h1>
          <p className="text-sm text-muted">
            {fmtDate(run.start_date)} – {fmtDate(run.end_date)} ·{" "}
            {fmtMoney(run.initial_capital)} start
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <a href={exportUrl(run_id, "trades")} className="btn-secondary">
            Export CSV
          </a>
          <button onClick={duplicate} disabled={busy} className="btn-secondary">
            Duplicate
          </button>
          <button onClick={startPaper} disabled={busy} className="btn-primary">
            Paper trade this →
          </button>
        </div>
      </div>

      <RunTabs runId={run_id} />

      {/* Headline summary */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricTile
          label="Final value"
          value={fmtMoney(full?.final_value)}
          sub={`from ${fmtMoney(run.initial_capital)}`}
        />
        <MetricTile label="CAGR" value={fmtPct(full?.cagr)} tone={full?.cagr} sub={`SPY ${fmtPct(full?.spy_cagr)}`} />
        <MetricTile label="Max drawdown" value={fmtPct(full?.max_drawdown)} tone={full?.max_drawdown} sub={`SPY ${fmtPct(full?.spy_max_drawdown)}`} />
        <MetricTile label="Sharpe" value={fmtNum(full?.sharpe)} sub="Risk-adjusted return" />
      </div>

      {/* Equity */}
      <Card>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-bold text-ink">Strategy vs SPY</h2>
          <span className="text-xs text-muted">Growth of {fmtMoney(run.initial_capital)}</span>
        </div>
        {equity == null ? <Spinner /> : <EquityChart data={equity} />}
      </Card>

      {/* Drawdown */}
      <Card>
        <h2 className="mb-3 text-base font-bold text-ink">Drawdown</h2>
        <p className="mb-2 text-xs text-muted">
          How far below its previous peak the strategy fell, over time.
        </p>
        {drawdown == null ? <Spinner /> : <DrawdownChart data={drawdown} />}
      </Card>

      {/* Period comparison */}
      <Card>
        <h2 className="mb-1 text-base font-bold text-ink">
          In-sample vs out-of-sample
        </h2>
        <p className="mb-4 text-xs text-muted">
          Out-of-sample is the held-out period the strategy never &quot;saw&quot;
          during design — the most honest read on robustness.
        </p>
        <PeriodTable
          rows={[
            { name: "Full period", m: byPeriod("full") },
            { name: "In-sample", m: byPeriod("in_sample") },
            { name: "Out-of-sample", m: byPeriod("out_of_sample") },
          ]}
        />
      </Card>

      <InfoBanner>
        Simulated results based on historical data. Past performance does not
        guarantee future results. Not investment advice.
      </InfoBanner>
    </div>
  );
}

function PeriodTable({
  rows,
}: {
  rows: { name: string; m?: Metrics }[];
}) {
  const cols: { key: keyof Metrics; label: string; pct?: boolean; tone?: boolean }[] = [
    { key: "cagr", label: "CAGR", pct: true, tone: true },
    { key: "total_return", label: "Total return", pct: true, tone: true },
    { key: "max_drawdown", label: "Max DD", pct: true, tone: true },
    { key: "sharpe", label: "Sharpe" },
    { key: "volatility", label: "Volatility", pct: true },
    { key: "win_rate", label: "Win rate", pct: true },
    { key: "number_of_trades", label: "Trades" },
    { key: "final_value", label: "Final value" },
  ];
  return (
    <div className="scroll-area overflow-x-auto">
      <table className="w-full min-w-[640px] border-collapse">
        <thead>
          <tr className="border-b border-line">
            <th className="th">Period</th>
            {cols.map((c) => (
              <th key={c.key} className="th text-right">
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.name} className="border-b border-line last:border-0">
              <td className="td font-semibold">{r.name}</td>
              {cols.map((c) => {
                const v = r.m ? (r.m[c.key] as number) : null;
                let text = "—";
                if (v != null)
                  text = c.pct
                    ? fmtPct(v)
                    : c.key === "final_value"
                    ? fmtMoney(v)
                    : fmtNum(v);
                return (
                  <td
                    key={c.key}
                    className={`td text-right tabular-nums ${
                      c.tone ? signClass(v) : ""
                    }`}
                  >
                    {text}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
