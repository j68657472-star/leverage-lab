"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { fmtMoney, fmtNum, fmtPct, signClass } from "@/lib/format";
import { Card, EmptyState, ErrorBanner, Spinner } from "@/components/ui";
import { CompareChart } from "@/components/Charts";

function CompareInner() {
  const sp = useSearchParams();
  const ids = (sp.get("runs") || "").split(",").filter(Boolean);
  const [data, setData] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (ids.length < 2) return;
    api.compare(ids).then(setData).catch((e) => setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sp]);

  if (ids.length < 2)
    return (
      <EmptyState
        title="Pick runs to compare"
        body="Go to Saved Runs and select 2–4 runs to compare side by side."
        action={
          <Link href="/saved-runs" className="btn-primary">
            Go to saved runs
          </Link>
        }
      />
    );
  if (error) return <ErrorBanner message={error} />;
  if (!data) return <Card><Spinner label="Loading comparison…" /></Card>;

  const runs = data.runs;
  const series = runs.map((r: any) => ({
    name: r.run_name,
    data: r.equity.map((e: any) => ({ date: e.date, value: e.portfolio_value })),
  }));

  // Parameter difference detection.
  const paramKeys = Object.keys(runs[0].params);
  const diffKeys = paramKeys.filter((k) =>
    runs.some((r: any) => r.params[k] !== runs[0].params[k])
  );

  const metricRows: { key: string; label: string; pct?: boolean; tone?: boolean }[] = [
    { key: "cagr", label: "CAGR", pct: true, tone: true },
    { key: "total_return", label: "Total return", pct: true, tone: true },
    { key: "max_drawdown", label: "Max drawdown", pct: true, tone: true },
    { key: "sharpe", label: "Sharpe" },
    { key: "in_sample_cagr", label: "In-sample CAGR", pct: true },
    { key: "out_of_sample_cagr", label: "Out-of-sample CAGR", pct: true },
    { key: "final_value", label: "Final value" },
  ];

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink">Compare runs</h1>
        <p className="text-sm text-muted">{runs.length} strategies overlaid.</p>
      </div>

      <Card>
        <h2 className="mb-3 text-base font-bold text-ink">Equity curves</h2>
        <CompareChart series={series} />
      </Card>

      <Card className="!p-0">
        <div className="scroll-area overflow-x-auto">
          <table className="w-full min-w-[640px] border-collapse">
            <thead className="border-b border-line bg-canvas">
              <tr>
                <th className="th">Metric</th>
                {runs.map((r: any) => (
                  <th key={r.run_id} className="th text-right">{r.run_name}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {metricRows.map((m) => (
                <tr key={m.key} className="border-b border-line last:border-0">
                  <td className="td font-semibold">{m.label}</td>
                  {runs.map((r: any) => {
                    const v = r.summary[m.key];
                    const text =
                      v == null
                        ? "—"
                        : m.pct
                        ? fmtPct(v)
                        : m.key === "final_value"
                        ? fmtMoney(v)
                        : fmtNum(v);
                    return (
                      <td
                        key={r.run_id}
                        className={`td text-right tabular-nums ${m.tone ? signClass(v) : ""}`}
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
      </Card>

      <Card>
        <h2 className="mb-3 text-base font-bold text-ink">Parameter differences</h2>
        {diffKeys.length === 0 ? (
          <p className="text-sm text-muted">
            These runs use identical parameters.
          </p>
        ) : (
          <div className="scroll-area overflow-x-auto">
            <table className="w-full min-w-[640px] border-collapse">
              <thead className="border-b border-line">
                <tr>
                  <th className="th">Parameter</th>
                  {runs.map((r: any) => (
                    <th key={r.run_id} className="th text-right">{r.run_name}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {diffKeys.map((k) => (
                  <tr key={k} className="border-b border-line last:border-0">
                    <td className="td font-mono text-xs">{k}</td>
                    {runs.map((r: any) => (
                      <td key={r.run_id} className="td text-right tabular-nums">
                        {String(r.params[k])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

export default function ComparePage() {
  return (
    <Suspense fallback={<Card><Spinner /></Card>}>
      <CompareInner />
    </Suspense>
  );
}
