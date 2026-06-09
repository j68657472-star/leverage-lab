// Thin typed API client. All requests go through Next.js rewrites to FastAPI.

export type StrategyParams = {
  rsi_period: number;
  rsi_reentry: number;
  qqq_rsi_overbought: number;
  qqq_spy_ratio_period: number;
  obv_sma_short: number;
  obv_sma_long: number;
  smh_mom_period: number;
  qqq_sma150_period: number;
  qqq_sma150_slope_lookback: number;
  deleverage_factor: number;
  fixed_cash_weight: number;
  transaction_cost_bps: number;
  slippage_bps: number;
  allow_fractional_shares: boolean;
};

export type Metrics = {
  period_name: string;
  cagr: number;
  sharpe: number;
  max_drawdown: number;
  total_return: number;
  volatility: number;
  win_rate: number;
  best_day: number;
  worst_day: number;
  number_of_trades: number;
  turnover: number;
  avg_exposure: number;
  avg_cash_pct: number;
  final_value: number;
  spy_cagr: number;
  spy_total_return: number;
  spy_max_drawdown: number;
};

export type RunSummary = {
  run_id: string;
  run_name: string;
  created_at: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  status: string;
  error_message?: string | null;
  cagr?: number | null;
  sharpe?: number | null;
  max_drawdown?: number | null;
  total_return?: number | null;
  in_sample_cagr?: number | null;
  out_of_sample_cagr?: number | null;
  spy_cagr?: number | null;
  final_value?: number | null;
};

export type RunDetail = RunSummary & {
  in_sample_ratio: number;
  out_of_sample_ratio: number;
  params: StrategyParams;
  metrics: Metrics[];
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  strategyInfo: () =>
    req<{ tickers: string[]; defaults: StrategyParams; description: string }>(
      "/api/strategy-info"
    ),

  runBacktest: (body: any) =>
    req<RunDetail>("/api/backtests/run", { method: "POST", body: JSON.stringify(body) }),

  listRuns: (uid: string) =>
    req<RunSummary[]>(`/api/backtests?anonymous_user_id=${encodeURIComponent(uid)}`),

  getRun: (runId: string) => req<RunDetail>(`/api/backtests/${runId}`),
  equity: (runId: string) =>
    req<{ date: string; portfolio_value: number; spy_value: number; daily_return: number }[]>(
      `/api/backtests/${runId}/equity`
    ),
  drawdown: (runId: string) =>
    req<{ date: string; drawdown: number; spy_drawdown: number }[]>(
      `/api/backtests/${runId}/drawdown`
    ),
  trades: (runId: string, qs = "") => req<any[]>(`/api/backtests/${runId}/trades${qs}`),
  holdings: (runId: string, qs = "") => req<any[]>(`/api/backtests/${runId}/holdings${qs}`),
  signals: (runId: string) => req<any[]>(`/api/backtests/${runId}/signals`),
  rename: (runId: string, run_name: string) =>
    req<RunSummary>(`/api/backtests/${runId}/rename`, {
      method: "PATCH",
      body: JSON.stringify({ run_name }),
    }),
  duplicate: (runId: string) =>
    req<RunDetail>(`/api/backtests/${runId}/duplicate`, { method: "POST" }),
  deleteRun: (runId: string) =>
    req<{ ok: boolean }>(`/api/backtests/${runId}`, { method: "DELETE" }),
  compare: (run_ids: string[]) =>
    req<{ runs: any[] }>("/api/backtests/compare", {
      method: "POST",
      body: JSON.stringify({ run_ids }),
    }),

  // paper
  createPaper: (body: any) =>
    req<any>("/api/paper-portfolios", { method: "POST", body: JSON.stringify(body) }),
  listPaper: (uid: string) =>
    req<any[]>(`/api/paper-portfolios?anonymous_user_id=${encodeURIComponent(uid)}`),
  getPaper: (pid: string) => req<any>(`/api/paper-portfolios/${pid}`),
  updatePaper: (pid: string) =>
    req<any>(`/api/paper-portfolios/${pid}/update`, { method: "POST" }),
  paperTrades: (pid: string) => req<any[]>(`/api/paper-portfolios/${pid}/trades`),
  paperHoldings: (pid: string) => req<any>(`/api/paper-portfolios/${pid}/holdings`),
  paperSnapshots: (pid: string) => req<any[]>(`/api/paper-portfolios/${pid}/snapshots`),
  deletePaper: (pid: string) =>
    req<{ ok: boolean }>(`/api/paper-portfolios/${pid}`, { method: "DELETE" }),
};

export function exportUrl(runId: string, kind: "trades" | "holdings" | "signals") {
  return `/api/backtests/${runId}/export/${kind}.csv`;
}
