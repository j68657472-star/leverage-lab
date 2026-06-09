"use client";
import { use, useEffect, useState } from "react";
import { api, exportUrl } from "@/lib/api";
import { fmtDate, fmtNum, fmtPct } from "@/lib/format";
import { Card, EmptyState, ErrorBanner, Spinner } from "@/components/ui";
import RunTabs from "@/components/RunTabs";

export default function SignalsPage({
  params,
}: {
  params: Promise<{ run_id: string }>;
}) {
  const { run_id } = use(params);
  const [rows, setRows] = useState<any[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.signals(run_id).then(setRows).catch((e) => setError(e.message));
  }, [run_id]);

  if (error) return <ErrorBanner message={error} />;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink">
          Daily signals
        </h1>
        <p className="text-sm text-muted">
          The exact conditions the strategy evaluated each day, and the target
          weights it produced.
        </p>
      </div>
      <RunTabs runId={run_id} />

      {rows == null ? (
        <Card><Spinner label="Loading signals…" /></Card>
      ) : rows.length === 0 ? (
        <EmptyState title="No signals" body="No signal records for this run." />
      ) : (
        <>
          <div className="flex justify-end">
            <a href={exportUrl(run_id, "signals")} className="btn-secondary">
              Export CSV
            </a>
          </div>
          <Card className="!p-0">
            <div className="scroll-area max-h-[640px] overflow-auto">
              <table className="w-full min-w-[920px] border-collapse">
                <thead className="sticky top-0 border-b border-line bg-canvas">
                  <tr>
                    {[
                      "Date",
                      "TQQQ",
                      "SOXL",
                      "QQQ RSI",
                      "QQQ>SPY",
                      "OBV20",
                      "OBV50",
                      "SMH mom",
                      "QQQ slope",
                      "Targets (T/S/G/V/Cash)",
                    ].map((h) => (
                      <th key={h} className="th">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.slice(-1500).reverse().map((r, i) => (
                    <tr key={i} className="border-b border-line last:border-0">
                      <td className="td whitespace-nowrap">{fmtDate(r.date)}</td>
                      <td className="td"><Dot on={r.tqqq_signal} /></td>
                      <td className="td"><Dot on={r.soxl_signal} /></td>
                      <td className="td text-right tabular-nums">{fmtNum(r.qqq_rsi, 1)}</td>
                      <td className="td"><Dot on={r.qqq_leading_spy} /></td>
                      <td className="td"><Dot on={r.obv_above_sma20} /></td>
                      <td className="td"><Dot on={r.obv_above_sma50} /></td>
                      <td className="td"><Dot on={r.smh_momentum_positive} /></td>
                      <td className="td"><Dot on={r.qqq_sma_slope_positive} /></td>
                      <td className="td whitespace-nowrap text-xs text-muted tabular-nums">
                        {fmtPct(r.target_weight_tqqq, 0)} / {fmtPct(r.target_weight_soxl, 0)} /{" "}
                        {fmtPct(r.target_weight_gld, 0)} / {fmtPct(r.target_weight_svxy, 0)} /{" "}
                        {fmtPct(r.target_weight_cash, 0)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}

function Dot({ on }: { on: boolean }) {
  return (
    <span
      className={`inline-block h-2.5 w-2.5 rounded-full ${
        on ? "bg-pos" : "bg-slate-300"
      }`}
      title={on ? "Yes" : "No"}
    />
  );
}
