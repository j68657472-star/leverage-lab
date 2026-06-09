"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, StrategyParams } from "@/lib/api";
import { useAnonId } from "@/lib/user";
import { Card, ErrorBanner, InfoBanner, Spinner } from "@/components/ui";

type Preset = "5y" | "10y" | "custom";

const DEFAULT_PARAMS: StrategyParams = {
  rsi_period: 14,
  rsi_reentry: 30,
  qqq_rsi_overbought: 75,
  qqq_spy_ratio_period: 50,
  obv_sma_short: 20,
  obv_sma_long: 50,
  smh_mom_period: 63,
  qqq_sma150_period: 150,
  qqq_sma150_slope_lookback: 10,
  deleverage_factor: 0.5,
  fixed_cash_weight: 0.5,
  transaction_cost_bps: 5,
  slippage_bps: 0,
  allow_fractional_shares: true,
};

function isoYearsAgo(years: number) {
  const d = new Date();
  d.setFullYear(d.getFullYear() - years);
  return d.toISOString().slice(0, 10);
}

const PARAM_FIELDS: { key: keyof StrategyParams; label: string; step?: number }[] = [
  { key: "rsi_reentry", label: "RSI re-entry (oversold)" },
  { key: "qqq_rsi_overbought", label: "QQQ overbought level" },
  { key: "qqq_spy_ratio_period", label: "QQQ/SPY ratio period" },
  { key: "obv_sma_short", label: "OBV short SMA" },
  { key: "obv_sma_long", label: "OBV long SMA" },
  { key: "smh_mom_period", label: "SMH momentum period" },
  { key: "qqq_sma150_period", label: "QQQ trend SMA period" },
  { key: "qqq_sma150_slope_lookback", label: "QQQ slope lookback" },
  { key: "transaction_cost_bps", label: "Transaction cost (bps)" },
  { key: "deleverage_factor", label: "Deleverage factor", step: 0.05 },
  { key: "fixed_cash_weight", label: "Fixed cash weight", step: 0.05 },
];

export default function BacktestForm() {
  const uid = useAnonId();
  const router = useRouter();

  const [preset, setPreset] = useState<Preset>("10y");
  const [capital, setCapital] = useState(100000);
  const [start, setStart] = useState(isoYearsAgo(10));
  const [end, setEnd] = useState(new Date().toISOString().slice(0, 10));
  const [inSample, setInSample] = useState(70);
  const [params, setParams] = useState<StrategyParams>(DEFAULT_PARAMS);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [name, setName] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (preset === "5y") setStart(isoYearsAgo(5));
    if (preset === "10y") setStart(isoYearsAgo(10));
  }, [preset]);

  const setParam = (k: keyof StrategyParams, v: number | boolean) =>
    setParams((p) => ({ ...p, [k]: v }));

  async function submit() {
    if (!uid) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await api.runBacktest({
        anonymous_user_id: uid,
        run_name: name || undefined,
        initial_capital: capital,
        start_date: start,
        end_date: end,
        in_sample_ratio: inSample / 100,
        params,
      });
      router.push(`/backtest/${res.run_id}`);
    } catch (e: any) {
      setError(e.message || "Something went wrong. Please try again.");
      setSubmitting(false);
    }
  }

  if (submitting) {
    return (
      <Card>
        <Spinner label="Running your backtest — downloading prices and simulating day by day…" />
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink">New backtest</h1>
        <p className="text-sm text-muted">
          Set your capital and time range, then run. Everything else has sensible
          defaults.
        </p>
      </div>

      {error && <ErrorBanner message={error} />}

      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <Card className="space-y-5">
          {/* Capital */}
          <div>
            <label className="label">Starting capital</label>
            <div className="relative">
              <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-muted">
                $
              </span>
              <input
                type="number"
                min={1000}
                step={1000}
                value={capital}
                onChange={(e) => setCapital(Number(e.target.value))}
                className="input pl-7"
              />
            </div>
          </div>

          {/* Range preset */}
          <div>
            <label className="label">Time range</label>
            <div className="grid grid-cols-3 gap-2">
              {(["5y", "10y", "custom"] as Preset[]).map((p) => (
                <button
                  key={p}
                  onClick={() => setPreset(p)}
                  className={`rounded-xl border px-3 py-2.5 text-sm font-semibold transition-colors ${
                    preset === p
                      ? "border-brand bg-blue-50 text-branddark"
                      : "border-line bg-white text-muted hover:bg-canvas"
                  }`}
                >
                  {p === "5y" ? "5 years" : p === "10y" ? "10 years" : "Custom"}
                </button>
              ))}
            </div>
          </div>

          {preset === "custom" && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Start date</label>
                <input
                  type="date"
                  value={start}
                  onChange={(e) => setStart(e.target.value)}
                  className="input"
                />
              </div>
              <div>
                <label className="label">End date</label>
                <input
                  type="date"
                  value={end}
                  onChange={(e) => setEnd(e.target.value)}
                  className="input"
                />
              </div>
            </div>
          )}

          {/* In/out sample */}
          <div>
            <div className="flex items-center justify-between">
              <label className="label mb-0">In-sample / out-of-sample split</label>
              <span className="text-sm font-semibold text-ink">
                {inSample}% / {100 - inSample}%
              </span>
            </div>
            <input
              type="range"
              min={50}
              max={90}
              step={5}
              value={inSample}
              onChange={(e) => setInSample(Number(e.target.value))}
              className="mt-2 w-full accent-brand"
            />
            <p className="mt-1 text-xs text-muted">
              The earliest {inSample}% is used to study the strategy. The last{" "}
              {100 - inSample}% is held out for an honest check — never used to
              tune parameters.
            </p>
          </div>

          {/* Name */}
          <div>
            <label className="label">Name this run (optional)</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Baseline 10-year"
              className="input"
            />
          </div>

          {/* Advanced */}
          <div className="rounded-xl border border-line">
            <button
              onClick={() => setShowAdvanced((s) => !s)}
              className="flex w-full items-center justify-between px-4 py-3 text-sm font-semibold text-ink"
            >
              Advanced strategy parameters
              <span className="text-muted">{showAdvanced ? "Hide" : "Show"}</span>
            </button>
            {showAdvanced && (
              <div className="space-y-4 border-t border-line p-4">
                <div className="grid grid-cols-2 gap-4">
                  {PARAM_FIELDS.map((f) => (
                    <div key={f.key}>
                      <label className="label">{f.label}</label>
                      <input
                        type="number"
                        step={f.step || 1}
                        value={params[f.key] as number}
                        onChange={(e) =>
                          setParam(f.key, Number(e.target.value))
                        }
                        className="input"
                      />
                    </div>
                  ))}
                </div>
                <label className="flex items-center gap-2 text-sm text-ink">
                  <input
                    type="checkbox"
                    checked={params.allow_fractional_shares}
                    onChange={(e) =>
                      setParam("allow_fractional_shares", e.target.checked)
                    }
                    className="h-4 w-4 accent-brand"
                  />
                  Allow fractional shares
                </label>
                <button
                  onClick={() => setParams(DEFAULT_PARAMS)}
                  className="text-xs font-medium text-brand"
                >
                  Reset to defaults
                </button>
              </div>
            )}
          </div>

          <button onClick={submit} className="btn-primary w-full text-base">
            Run backtest →
          </button>
        </Card>

        {/* Side explainer */}
        <div className="space-y-4">
          <Card>
            <h3 className="text-sm font-bold text-ink">The strategy in plain English</h3>
            <ul className="mt-3 space-y-2.5 text-sm text-muted">
              <li>
                <span className="font-semibold text-ink">TQQQ sleeve (50%).</span>{" "}
                Holds TQQQ when its trend is healthy; otherwise goes defensive
                with gold (GLD) and SVXY.
              </li>
              <li>
                <span className="font-semibold text-ink">SOXL sleeve (50%).</span>{" "}
                Holds SOXL when chips & the Nasdaq are trending up; otherwise
                holds gold.
              </li>
              <li>
                <span className="font-semibold text-ink">De-leverage + cash.</span>{" "}
                Risk is scaled by {Math.round(params.deleverage_factor * 100)}%
                and combined with a{" "}
                {Math.round(params.fixed_cash_weight * 100)}% cash buffer.
              </li>
            </ul>
          </Card>
          <InfoBanner>
            Signals only use data up to each day&apos;s close, and trades execute
            on the <strong>next</strong> day — so the backtest never peeks into
            the future.
          </InfoBanner>
        </div>
      </div>
    </div>
  );
}
