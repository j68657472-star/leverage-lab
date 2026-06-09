"use client";
import { use, useEffect, useMemo, useState } from "react";
import { api, exportUrl } from "@/lib/api";
import { fmtDate, fmtMoney, fmtNum, fmtPct } from "@/lib/format";
import { Card, EmptyState, ErrorBanner, Pill, Spinner } from "@/components/ui";
import RunTabs from "@/components/RunTabs";
import { ASSET_COLORS } from "@/lib/assets";

export default function TradesPage({
  params,
}: {
  params: Promise<{ run_id: string }>;
}) {
  const { run_id } = use(params);
  const [trades, setTrades] = useState<any[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ticker, setTicker] = useState("");
  const [action, setAction] = useState("");
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState<number | null>(null);

  useEffect(() => {
    api.trades(run_id).then(setTrades).catch((e) => setError(e.message));
  }, [run_id]);

  const filtered = useMemo(() => {
    if (!trades) return [];
    return trades.filter((t) => {
      if (ticker && t.ticker !== ticker) return false;
      if (action && t.action !== action) return false;
      if (search && !t.signal_reason.toLowerCase().includes(search.toLowerCase()))
        return false;
      return true;
    });
  }, [trades, ticker, action, search]);

  if (error) return <ErrorBanner message={error} />;

  return (
    <div className="space-y-5">
      <Header runId={run_id} />
      <RunTabs runId={run_id} />

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
          <select
            value={action}
            onChange={(e) => setAction(e.target.value)}
            className="input max-w-[140px]"
          >
            <option value="">All actions</option>
            <option value="BUY">Buy</option>
            <option value="SELL">Sell</option>
          </select>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search reason…"
            className="input max-w-[220px]"
          />
          <div className="ml-auto flex items-center gap-3">
            <span className="text-sm text-muted">
              {trades ? `${filtered.length} of ${trades.length}` : ""}
            </span>
            <a href={exportUrl(run_id, "trades")} className="btn-secondary">
              Export CSV
            </a>
          </div>
        </div>
      </Card>

      {trades == null ? (
        <Card><Spinner label="Loading trades…" /></Card>
      ) : filtered.length === 0 ? (
        <EmptyState
          title="No trades match"
          body="Try clearing your filters to see all trades for this backtest."
        />
      ) : (
        <Card className="!p-0">
          <div className="scroll-area overflow-x-auto">
            <table className="w-full min-w-[820px] border-collapse">
              <thead className="border-b border-line bg-canvas">
                <tr>
                  {["Date", "Action", "Ticker", "Price", "Shares", "Notional", "Portfolio", "Why"].map(
                    (h) => (
                      <th key={h} className="th">{h}</th>
                    )
                  )}
                  <th className="th" />
                </tr>
              </thead>
              <tbody>
                {filtered.map((t, i) => (
                  <RowGroup
                    key={i}
                    t={t}
                    open={open === i}
                    onToggle={() => setOpen(open === i ? null : i)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}

function Header({ runId }: { runId: string }) {
  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight text-ink">Trade records</h1>
      <p className="text-sm text-muted">
        Every rebalance, with a plain-English reason. Click a row for the full
        technical detail.
      </p>
    </div>
  );
}

function RowGroup({
  t,
  open,
  onToggle,
}: {
  t: any;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <>
      <tr
        className="cursor-pointer border-b border-line hover:bg-canvas"
        onClick={onToggle}
      >
        <td className="td whitespace-nowrap">{fmtDate(t.date)}</td>
        <td className="td">
          <span
            className={`pill ${
              t.action === "BUY"
                ? "bg-emerald-50 text-pos"
                : "bg-red-50 text-neg"
            }`}
          >
            {t.action}
          </span>
        </td>
        <td className="td">
          <span className="inline-flex items-center gap-1.5 font-semibold">
            <span
              className="h-2.5 w-2.5 rounded-sm"
              style={{ background: ASSET_COLORS[t.ticker] }}
            />
            {t.ticker}
          </span>
        </td>
        <td className="td tabular-nums">{fmtMoney(t.price, 2)}</td>
        <td className="td tabular-nums">{fmtNum(t.shares, 2)}</td>
        <td className="td tabular-nums">{fmtMoney(t.notional)}</td>
        <td className="td tabular-nums">{fmtMoney(t.portfolio_value_after)}</td>
        <td className="td max-w-[260px] truncate text-muted" title={t.signal_reason}>
          {t.signal_reason}
        </td>
        <td className="td text-right text-muted">{open ? "▲" : "▼"}</td>
      </tr>
      {open && (
        <tr className="border-b border-line bg-canvas/60">
          <td colSpan={9} className="px-5 py-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <h4 className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">
                  Why this happened
                </h4>
                <p className="text-sm text-ink">{t.signal_reason}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <SignalChip label="TQQQ signal" on={t.tqqq_signal} />
                  <SignalChip label="SOXL signal" on={t.soxl_signal} />
                  <SignalChip label="QQQ leads SPY" on={t.qqq_spy_signal} />
                  <SignalChip label="OBV > SMA20" on={t.obv_sma20_signal} />
                  <SignalChip label="OBV > SMA50" on={t.obv_sma50_signal} />
                  <SignalChip label="SMH momentum" on={t.smh_momentum_signal} />
                  <SignalChip label="QQQ slope up" on={t.qqq_sma_slope_signal} />
                </div>
              </div>
              <div>
                <h4 className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">
                  Execution detail
                </h4>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
                  <Detail k="QQQ RSI" v={fmtNum(t.qqq_rsi, 1)} />
                  <Detail k="Transaction cost" v={fmtMoney(t.transaction_cost, 2)} />
                  <Detail k="Target weight" v={fmtPct(t.target_weight)} />
                  <Detail k="Actual weight" v={fmtPct(t.actual_weight)} />
                  <Detail k="Old weight" v={fmtPct(t.old_weight)} />
                  <Detail k="New weight" v={fmtPct(t.new_weight)} />
                  <Detail k="Value before" v={fmtMoney(t.portfolio_value_before)} />
                  <Detail k="Value after" v={fmtMoney(t.portfolio_value_after)} />
                  <Detail k="Cash before" v={fmtMoney(t.cash_before)} />
                  <Detail k="Cash after" v={fmtMoney(t.cash_after)} />
                </dl>
                <p className="mt-2 text-xs text-muted">
                  {t.technical_details?.execution_note}
                </p>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function SignalChip({ label, on }: { label: string; on: boolean }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-line bg-white px-2.5 py-1 text-xs">
      <span
        className={`h-2 w-2 rounded-full ${on ? "bg-pos" : "bg-slate-300"}`}
      />
      <span className="text-ink">{label}</span>
    </span>
  );
}

function Detail({ k, v }: { k: string; v: string }) {
  return (
    <>
      <dt className="text-muted">{k}</dt>
      <dd className="text-right font-medium text-ink tabular-nums">{v}</dd>
    </>
  );
}
