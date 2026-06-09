"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, RunSummary } from "@/lib/api";
import { useAnonId } from "@/lib/user";
import { fmtDate, fmtMoney, fmtNum, fmtPct, signClass } from "@/lib/format";
import { Card, EmptyState, ErrorBanner, Spinner } from "@/components/ui";

export default function SavedRuns() {
  const uid = useAnonId();
  const router = useRouter();
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = () => {
    if (!uid) return;
    api.listRuns(uid).then(setRuns).catch((e) => setError(e.message));
  };
  useEffect(load, [uid]);

  const toggle = (id: string) =>
    setSelected((s) =>
      s.includes(id) ? s.filter((x) => x !== id) : s.length < 4 ? [...s, id] : s
    );

  async function rename(r: RunSummary) {
    const name = prompt("Rename run", r.run_name);
    if (!name) return;
    await api.rename(r.run_id, name);
    load();
  }
  async function duplicate(r: RunSummary) {
    setBusyId(r.run_id);
    try {
      const dup = await api.duplicate(r.run_id);
      router.push(`/backtest/${dup.run_id}`);
    } catch (e: any) {
      setError(e.message);
      setBusyId(null);
    }
  }
  async function remove(r: RunSummary) {
    if (!confirm(`Delete "${r.run_name}"? This cannot be undone.`)) return;
    await api.deleteRun(r.run_id);
    load();
  }

  if (error) return <ErrorBanner message={error} />;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">Saved runs</h1>
          <p className="text-sm text-muted">
            Your strategy experiments. Select 2–4 to compare.
          </p>
        </div>
        <div className="flex gap-2">
          {selected.length >= 2 && (
            <Link
              href={`/compare?runs=${selected.join(",")}`}
              className="btn-primary"
            >
              Compare {selected.length} →
            </Link>
          )}
          <Link href="/backtest" className="btn-secondary">
            New backtest
          </Link>
        </div>
      </div>

      {runs == null ? (
        <Card><Spinner /></Card>
      ) : runs.length === 0 ? (
        <EmptyState
          title="No saved runs yet"
          body="Run a backtest and it will be saved here automatically."
          action={
            <Link href="/backtest" className="btn-primary">
              Run a backtest
            </Link>
          }
        />
      ) : (
        <Card className="!p-0">
          <div className="scroll-area overflow-x-auto">
            <table className="w-full min-w-[960px] border-collapse">
              <thead className="border-b border-line bg-canvas">
                <tr>
                  <th className="th w-10" />
                  <th className="th">Name</th>
                  <th className="th">Range</th>
                  <th className="th text-right">Capital</th>
                  <th className="th text-right">CAGR</th>
                  <th className="th text-right">Sharpe</th>
                  <th className="th text-right">Max DD</th>
                  <th className="th text-right">In-sample</th>
                  <th className="th text-right">Out-sample</th>
                  <th className="th text-right">SPY CAGR</th>
                  <th className="th" />
                </tr>
              </thead>
              <tbody>
                {runs.map((r) => (
                  <tr key={r.run_id} className="border-b border-line last:border-0 hover:bg-canvas">
                    <td className="td">
                      <input
                        type="checkbox"
                        checked={selected.includes(r.run_id)}
                        onChange={() => toggle(r.run_id)}
                        className="h-4 w-4 accent-brand"
                      />
                    </td>
                    <td className="td">
                      <Link
                        href={`/backtest/${r.run_id}`}
                        className="font-semibold text-ink hover:text-brand"
                      >
                        {r.run_name}
                      </Link>
                      <div className="text-xs text-muted">{fmtDate(r.created_at)}</div>
                      {r.status === "failed" && (
                        <span className="pill bg-red-50 text-neg">failed</span>
                      )}
                    </td>
                    <td className="td whitespace-nowrap text-xs text-muted">
                      {fmtDate(r.start_date)} – {fmtDate(r.end_date)}
                    </td>
                    <td className="td text-right tabular-nums">{fmtMoney(r.initial_capital)}</td>
                    <td className={`td text-right font-semibold tabular-nums ${signClass(r.cagr)}`}>{fmtPct(r.cagr)}</td>
                    <td className="td text-right tabular-nums">{fmtNum(r.sharpe)}</td>
                    <td className={`td text-right tabular-nums ${signClass(r.max_drawdown)}`}>{fmtPct(r.max_drawdown)}</td>
                    <td className="td text-right tabular-nums">{fmtPct(r.in_sample_cagr)}</td>
                    <td className="td text-right tabular-nums">{fmtPct(r.out_of_sample_cagr)}</td>
                    <td className="td text-right tabular-nums text-muted">{fmtPct(r.spy_cagr)}</td>
                    <td className="td">
                      <div className="flex justify-end gap-1">
                        <button onClick={() => rename(r)} className="btn-ghost !px-2 !py-1 text-xs">Rename</button>
                        <button onClick={() => duplicate(r)} disabled={busyId === r.run_id} className="btn-ghost !px-2 !py-1 text-xs">Duplicate</button>
                        <button onClick={() => remove(r)} className="btn-ghost !px-2 !py-1 text-xs text-neg">Delete</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
