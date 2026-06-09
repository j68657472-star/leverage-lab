"use client";
import { use, useEffect, useMemo, useState } from "react";
import { api, exportUrl } from "@/lib/api";
import { fmtDate, fmtMoney, fmtNum, fmtPct, signClass } from "@/lib/format";
import { Card, EmptyState, ErrorBanner, Spinner } from "@/components/ui";
import { AllocationBar } from "@/components/Charts";
import RunTabs from "@/components/RunTabs";
import { ASSET_COLORS } from "@/lib/assets";

export default function HoldingsPage({
  params,
}: {
  params: Promise<{ run_id: string }>;
}) {
  const { run_id } = use(params);
  const [rows, setRows] = useState<any[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ticker, setTicker] = useState("");
  const [date, setDate] = useState("");

  useEffect(() => {
    api.holdings(run_id).then(setRows).catch((e) => setError(e.message));
  }, [run_id]);

  // Group by date for the day-by-day inspector.
  const dates = useMemo(() => {
    if (!rows) return [];
    return Array.from(new Set(rows.map((r) => r.date)));
  }, [rows]);

  const [selectedDate, setSelectedDate] = useState<string>("");
  useEffect(() => {
    if (dates.length && !selectedDate) setSelectedDate(dates[dates.length - 1]);
  }, [dates, selectedDate]);

  const daySnapshot = useMemo(
    () => (rows ? rows.filter((r) => r.date === selectedDate) : []),
    [rows, selectedDate]
  );

  const filtered = useMemo(() => {
    if (!rows) return [];
    return rows.filter((r) => {
      if (ticker && r.ticker !== ticker) return false;
      if (date && r.date !== date) return false;
      return true;
    });
  }, [rows, ticker, date]);

  if (error) return <ErrorBanner message={error} />;

  const pv = daySnapshot[0]?.portfolio_value;
  const cash = daySnapshot[0]?.cash;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink">Holdings</h1>
        <p className="text-sm text-muted">
          Inspect what the portfolio held on any day — shares, value, weights and
          cash.
        </p>
      </div>
      <RunTabs runId={run_id} />

      {rows == null ? (
        <Card><Spinner label="Loading holdings…" /></Card>
      ) : rows.length === 0 ? (
        <EmptyState title="No holdings" body="This backtest has no holdings records." />
      ) : (
        <>
          {/* Day inspector */}
          <Card>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-base font-bold text-ink">Allocation on a day</h2>
              <select
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="input max-w-[200px]"
              >
                {dates
                  .slice()
                  .reverse()
                  .map((d) => (
                    <option key={d} value={d}>
                      {fmtDate(d)}
                    </option>
                  ))}
              </select>
            </div>
            <div className="grid gap-5 md:grid-cols-[1fr_1.4fr]">
              <div className="space-y-3">
                <div className="rounded-xl border border-line bg-canvas p-4">
                  <div className="text-xs text-muted">Portfolio value</div>
                  <div className="text-2xl font-bold text-ink">{fmtMoney(pv)}</div>
                  <div className="mt-1 text-xs text-muted">
                    Cash {fmtMoney(cash)} ({fmtPct(pv ? cash / pv : 0)})
                  </div>
                </div>
              </div>
              <div>
                <AllocationBar
                  weights={[
                    ...daySnapshot.map((h) => ({
                      label: h.ticker,
                      value: h.actual_weight,
                      color: ASSET_COLORS[h.ticker] || "#94a3b8",
                    })),
                    {
                      label: "CASH",
                      value: pv ? cash / pv : 0,
                      color: ASSET_COLORS.CASH,
                    },
                  ]}
                />
                <table className="mt-4 w-full">
                  <thead>
                    <tr className="border-b border-line">
                      <th className="th">Ticker</th>
                      <th className="th text-right">Shares</th>
                      <th className="th text-right">Value</th>
                      <th className="th text-right">Target</th>
                      <th className="th text-right">Actual</th>
                    </tr>
                  </thead>
                  <tbody>
                    {daySnapshot.map((h) => (
                      <tr key={h.ticker} className="border-b border-line last:border-0">
                        <td className="td font-semibold">{h.ticker}</td>
                        <td className="td text-right tabular-nums">{fmtNum(h.shares, 2)}</td>
                        <td className="td text-right tabular-nums">{fmtMoney(h.market_value)}</td>
                        <td className="td text-right tabular-nums">{fmtPct(h.target_weight)}</td>
                        <td className="td text-right tabular-nums">{fmtPct(h.actual_weight)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </Card>

          {/* Full table */}
          <Card className="!p-4">
            <div className="flex flex-wrap items-center gap-3">
              <select
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                className="input max-w-[140px]"
              >
                <option value="">All tickers</option>
                {["TQQQ", "SOXL", "GLD", "SVXY"].map((t) => (
                  <option key={t}>{t}</option>
                ))}
              </select>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="input max-w-[180px]"
              />
              <div className="ml-auto flex items-center gap-3">
                <span className="text-sm text-muted">{filtered.length} rows</span>
                <a href={exportUrl(run_id, "holdings")} className="btn-secondary">
                  Export CSV
                </a>
              </div>
            </div>
          </Card>

          <Card className="!p-0">
            <div className="scroll-area max-h-[560px] overflow-auto">
              <table className="w-full min-w-[860px] border-collapse">
                <thead className="sticky top-0 border-b border-line bg-canvas">
                  <tr>
                    {["Date", "Ticker", "Shares", "Close", "Value", "Target", "Actual", "Cash", "Portfolio", "Day"].map(
                      (h) => (
                        <th key={h} className="th">{h}</th>
                      )
                    )}
                  </tr>
                </thead>
                <tbody>
                  {filtered.slice(0, 2000).map((r, i) => (
                    <tr key={i} className="border-b border-line last:border-0">
                      <td className="td whitespace-nowrap">{fmtDate(r.date)}</td>
                      <td className="td font-semibold">{r.ticker}</td>
                      <td className="td text-right tabular-nums">{fmtNum(r.shares, 2)}</td>
                      <td className="td text-right tabular-nums">{fmtMoney(r.close_price, 2)}</td>
                      <td className="td text-right tabular-nums">{fmtMoney(r.market_value)}</td>
                      <td className="td text-right tabular-nums">{fmtPct(r.target_weight)}</td>
                      <td className="td text-right tabular-nums">{fmtPct(r.actual_weight)}</td>
                      <td className="td text-right tabular-nums">{fmtMoney(r.cash)}</td>
                      <td className="td text-right tabular-nums">{fmtMoney(r.portfolio_value)}</td>
                      <td className={`td text-right tabular-nums ${signClass(r.daily_return)}`}>
                        {fmtPct(r.daily_return, 2)}
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
