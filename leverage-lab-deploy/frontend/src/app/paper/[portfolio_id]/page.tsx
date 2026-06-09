"use client";
import { useRouter } from "next/navigation";
import { use, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { fmtDate, fmtMoney, fmtNum, fmtPct, signClass } from "@/lib/format";
import {
  Card,
  ErrorBanner,
  InfoBanner,
  MetricTile,
  Spinner,
} from "@/components/ui";
import { AllocationBar } from "@/components/Charts";
import { ASSET_COLORS } from "@/lib/assets";

export default function PaperDetail({
  params,
}: {
  params: Promise<{ portfolio_id: string }>;
}) {
  const { portfolio_id } = use(params);
  const router = useRouter();

  const [pf, setPf] = useState<any | null>(null);
  const [holdings, setHoldings] = useState<any | null>(null);
  const [trades, setTrades] = useState<any[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);
  const [lastChange, setLastChange] = useState<any | null>(null);

  const load = () => {
    api.getPaper(portfolio_id).then(setPf).catch((e) => setError(e.message));
    api.paperHoldings(portfolio_id).then(setHoldings).catch(() => {});
    api.paperTrades(portfolio_id).then(setTrades).catch(() => {});
  };
  useEffect(load, [portfolio_id]);

  async function update() {
    setUpdating(true);
    setError(null);
    try {
      const res = await api.updatePaper(portfolio_id);
      setLastChange(res);
      load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setUpdating(false);
    }
  }

  async function remove() {
    if (!confirm("Delete this paper portfolio?")) return;
    await api.deletePaper(portfolio_id);
    router.push("/paper");
  }

  if (error && !pf) return <ErrorBanner message={error} />;
  if (!pf) return <Card><Spinner /></Card>;

  const pnl = pf.current_value - pf.initial_capital;
  const tw = holdings?.latest_target_weights;
  const aw = holdings?.latest_actual_weights;
  const sig = holdings?.latest_signal;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">{pf.name}</h1>
          <p className="text-sm text-muted">
            Started {fmtMoney(pf.initial_capital)} ·{" "}
            {pf.last_updated_at ? `updated ${fmtDate(pf.last_updated_at)}` : "not updated yet"}
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={update} disabled={updating} className="btn-primary">
            {updating ? "Updating…" : "Update now"}
          </button>
          <button onClick={remove} className="btn-ghost text-neg">
            Delete
          </button>
        </div>
      </div>

      <InfoBanner>
        <strong>Simulated.</strong> Signals use daily closing prices. The latest
        price is only used to estimate value — it never changes the signal. No
        real orders are placed.
      </InfoBanner>

      {error && <ErrorBanner message={error} />}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricTile label="Current value" value={fmtMoney(pf.current_value)} />
        <MetricTile
          label="Profit / loss"
          value={`${pnl >= 0 ? "+" : ""}${fmtMoney(pnl)}`}
          tone={pnl}
          sub={fmtPct(pf.initial_capital ? pnl / pf.initial_capital : 0)}
        />
        <MetricTile label="Cash" value={fmtMoney(pf.cash)} sub={fmtPct(pf.current_value ? pf.cash / pf.current_value : 0)} />
        <MetricTile
          label="Latest signal"
          value={
            sig
              ? `${sig.tqqq_signal ? "TQQQ on" : "TQQQ off"} · ${sig.soxl_signal ? "SOXL on" : "SOXL off"}`
              : "—"
          }
          sub={sig ? `QQQ RSI ${fmtNum(sig.qqq_rsi, 1)}` : "Press Update"}
        />
      </div>

      {lastChange && (
        <Card>
          <h2 className="mb-2 text-base font-bold text-ink">
            What changed in this update
          </h2>
          {lastChange.trades.length === 0 ? (
            <p className="text-sm text-muted">
              No rebalance needed — your holdings already match the target as of{" "}
              {fmtDate(lastChange.as_of)}.
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {lastChange.trades.map((t: any, i: number) => (
                <span
                  key={i}
                  className={`pill ${
                    t.action === "BUY" ? "bg-emerald-50 text-pos" : "bg-red-50 text-neg"
                  }`}
                >
                  {t.action} {fmtNum(t.shares, 2)} {t.ticker}
                </span>
              ))}
            </div>
          )}
          <p className="mt-3 text-xs text-muted">{lastChange.signal_reason}</p>
        </Card>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        {/* Current vs target */}
        <Card>
          <h2 className="mb-3 text-base font-bold text-ink">
            Current vs target allocation
          </h2>
          {aw ? (
            <div className="space-y-4">
              <div>
                <div className="mb-1.5 text-xs font-medium text-muted">Current</div>
                <AllocationBar
                  weights={["TQQQ", "SOXL", "GLD", "SVXY", "CASH"].map((t) => ({
                    label: t,
                    value: aw[t] || 0,
                    color: ASSET_COLORS[t],
                  }))}
                />
              </div>
              {tw && (
                <div>
                  <div className="mb-1.5 text-xs font-medium text-muted">Target</div>
                  <AllocationBar
                    weights={["TQQQ", "SOXL", "GLD", "SVXY", "CASH"].map((t) => ({
                      label: t,
                      value: tw[t] || 0,
                      color: ASSET_COLORS[t],
                    }))}
                  />
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted">
              Press <strong>Update now</strong> to compute the latest signal and
              allocation.
            </p>
          )}
        </Card>

        {/* Holdings */}
        <Card>
          <h2 className="mb-3 text-base font-bold text-ink">Holdings</h2>
          {pf.holdings && Object.values(pf.holdings).some((v: any) => v > 0) ? (
            <table className="w-full">
              <thead>
                <tr className="border-b border-line">
                  <th className="th">Ticker</th>
                  <th className="th text-right">Shares</th>
                  <th className="th text-right">Weight</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(pf.holdings)
                  .filter(([, v]: any) => v > 0)
                  .map(([t, v]: any) => (
                    <tr key={t} className="border-b border-line last:border-0">
                      <td className="td font-semibold">{t}</td>
                      <td className="td text-right tabular-nums">{fmtNum(v, 3)}</td>
                      <td className="td text-right tabular-nums">
                        {aw ? fmtPct(aw[t] || 0) : "—"}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          ) : (
            <p className="text-sm text-muted">
              No positions yet. Update to take the first simulated positions.
            </p>
          )}
        </Card>
      </div>

      {/* Trade history */}
      <Card className="!p-0">
        <div className="border-b border-line px-5 py-3">
          <h2 className="text-base font-bold text-ink">Simulated trade history</h2>
        </div>
        {trades == null ? (
          <Spinner />
        ) : trades.length === 0 ? (
          <p className="p-5 text-sm text-muted">No simulated trades yet.</p>
        ) : (
          <div className="scroll-area overflow-x-auto">
            <table className="w-full min-w-[640px] border-collapse">
              <thead className="border-b border-line bg-canvas">
                <tr>
                  {["Date", "Action", "Ticker", "Price", "Shares", "Notional", "Why"].map((h) => (
                    <th key={h} className="th">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {trades.slice().reverse().map((t, i) => (
                  <tr key={i} className="border-b border-line last:border-0">
                    <td className="td whitespace-nowrap">{fmtDate(t.date)}</td>
                    <td className="td">
                      <span className={`pill ${t.action === "BUY" ? "bg-emerald-50 text-pos" : "bg-red-50 text-neg"}`}>
                        {t.action}
                      </span>
                    </td>
                    <td className="td font-semibold">{t.ticker}</td>
                    <td className="td text-right tabular-nums">{fmtMoney(t.price, 2)}</td>
                    <td className="td text-right tabular-nums">{fmtNum(t.shares, 2)}</td>
                    <td className="td text-right tabular-nums">{fmtMoney(t.notional)}</td>
                    <td className="td max-w-[260px] truncate text-muted" title={t.signal_reason}>
                      {t.signal_reason}
                    </td>
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
