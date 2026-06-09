"""No-lookahead portfolio backtest engine.

Execution model (conservative, no lookahead):
  - Signal for day D is computed from data through D's close (in signals.py).
  - We *execute* that signal on the NEXT trading day D+1, at D+1's close price.
  - Returns are therefore earned only after execution.

Concretely, on each day t we:
  1. Mark the portfolio to market using day t's close prices.
  2. Look at the *previous* day's target weights (decided at t-1 close) and
     rebalance toward them using day t's close as the execution price.
This guarantees we never trade on information from the same bar's close that we
are also using to execute, and never use future data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from . import metrics as M
from .params import StrategyParams, TRADABLE_ASSETS
from .signals import compute_signal_frame


@dataclass
class TradeRecord:
    date: date
    ticker: str
    action: str  # BUY / SELL
    price: float
    shares: float
    notional: float
    transaction_cost: float
    old_weight: float
    new_weight: float
    target_weight: float
    actual_weight: float
    portfolio_value_before: float
    portfolio_value_after: float
    cash_before: float
    cash_after: float
    signal_reason: str
    tqqq_signal: bool
    soxl_signal: bool
    qqq_rsi: float
    qqq_spy_signal: bool
    obv_sma20_signal: bool
    obv_sma50_signal: bool
    smh_momentum_signal: bool
    qqq_sma_slope_signal: bool
    technical_details: dict[str, Any] = field(default_factory=dict)


@dataclass
class BacktestResult:
    signals: pd.DataFrame
    daily: pd.DataFrame            # portfolio-level daily snapshot
    holdings: pd.DataFrame         # long-format per-ticker daily holdings
    trades: list[TradeRecord]
    metrics_full: dict[str, float]
    metrics_in: dict[str, float]
    metrics_out: dict[str, float]
    split_date: date
    spy_metrics_full: dict[str, float]
    extra: dict[str, float]


def _round_shares(shares: float, allow_fractional: bool) -> float:
    if allow_fractional:
        return float(shares)
    return float(np.floor(shares + 1e-9)) if shares >= 0 else float(np.ceil(shares - 1e-9))


def run_backtest(
    prices: dict[str, pd.DataFrame],
    params: StrategyParams,
    initial_capital: float,
    start: date | None = None,
    end: date | None = None,
    in_sample_ratio: float = 0.70,
) -> BacktestResult:
    params.validate()
    if initial_capital <= 0:
        raise ValueError("Initial capital must be greater than zero.")

    sig = compute_signal_frame(prices, params)

    # Trim to the requested window but keep warmup before `start` for indicators.
    full_index = sig.index
    if start is not None:
        full_index = full_index[full_index >= pd.Timestamp(start)]
    if end is not None:
        full_index = full_index[full_index <= pd.Timestamp(end)]
    # Only keep rows where indicators are ready (real trading window).
    full_index = full_index[sig.loc[full_index, "ready"].values]
    if len(full_index) < 2:
        raise ValueError(
            "Not enough price history in the selected date range to run a backtest. "
            "Try an earlier start date or a longer range."
        )

    # Close-price matrix for tradable assets, aligned to the trading window.
    close = pd.DataFrame(
        {t: prices[t]["close"].reindex(full_index) for t in TRADABLE_ASSETS}
    )
    if close.isna().any().any():
        missing = close.columns[close.isna().any()].tolist()
        raise ValueError(
            "Missing price data for "
            + ", ".join(missing)
            + " inside the selected range. Backtest aborted to avoid using bad data."
        )

    tcost_rate = params.transaction_cost_bps / 10000.0
    slip_rate = params.slippage_bps / 10000.0

    # Portfolio state
    cash = float(initial_capital)
    shares = {t: 0.0 for t in TRADABLE_ASSETS}

    daily_rows: list[dict[str, Any]] = []
    holding_rows: list[dict[str, Any]] = []
    trades: list[TradeRecord] = []

    target_cols = {
        "TQQQ": "target_weight_tqqq",
        "SOXL": "target_weight_soxl",
        "GLD": "target_weight_gld",
        "SVXY": "target_weight_svxy",
    }

    prev_targets: dict[str, float] | None = None      # decided at t-1 close
    last_executed: dict[str, float] | None = None     # last target we traded to

    for i, ts in enumerate(full_index):
        px = {t: float(close.loc[ts, t]) for t in TRADABLE_ASSETS}

        # 1) Mark to market at today's close (pre-rebalance value).
        holdings_value = sum(shares[t] * px[t] for t in TRADABLE_ASSETS)
        pv_before = cash + holdings_value

        # Decide whether a rebalance is warranted today. We only rebalance when
        # the target weights CHANGED versus the last executed target (i.e. a
        # signal flip). This keeps turnover realistic and makes every trade map
        # to an explainable change in the strategy's view.
        targets_changed = prev_targets is not None and (
            last_executed is None
            or any(
                abs(prev_targets[t] - last_executed[t]) > 1e-9 for t in TRADABLE_ASSETS
            )
        )

        # 2) Execute *yesterday's* targets today (no lookahead), if changed.
        if prev_targets is not None and targets_changed:
            old_weights = {
                t: (shares[t] * px[t] / pv_before if pv_before > 0 else 0.0)
                for t in TRADABLE_ASSETS
            }
            for t in TRADABLE_ASSETS:
                tgt_w = prev_targets[t]
                tgt_value = tgt_w * pv_before
                exec_price = px[t] * (1.0 + slip_rate)  # buy slips up; simplification
                tgt_shares = _round_shares(
                    tgt_value / exec_price if exec_price > 0 else 0.0,
                    params.allow_fractional_shares,
                )
                delta = tgt_shares - shares[t]
                if abs(delta) < 1e-9:
                    continue
                action = "BUY" if delta > 0 else "SELL"
                exec_px = px[t] * (1.0 + slip_rate if delta > 0 else 1.0 - slip_rate)
                notional = abs(delta) * exec_px
                tc = notional * tcost_rate
                cash_before = cash
                # Apply trade
                cash -= delta * exec_px  # buying reduces cash
                cash -= tc
                shares[t] = tgt_shares

                new_holdings_value = sum(shares[a] * px[a] for a in TRADABLE_ASSETS)
                pv_after = cash + new_holdings_value
                new_w = shares[t] * px[t] / pv_after if pv_after > 0 else 0.0

                srow = sig.loc[ts]
                trades.append(
                    TradeRecord(
                        date=ts.date(),
                        ticker=t,
                        action=action,
                        price=round(exec_px, 6),
                        shares=round(abs(delta), 6),
                        notional=round(notional, 2),
                        transaction_cost=round(tc, 4),
                        old_weight=round(old_weights[t], 6),
                        new_weight=round(new_w, 6),
                        target_weight=round(tgt_w, 6),
                        actual_weight=round(new_w, 6),
                        portfolio_value_before=round(pv_before, 2),
                        portfolio_value_after=round(pv_after, 2),
                        cash_before=round(cash_before, 2),
                        cash_after=round(cash, 2),
                        signal_reason=str(srow["signal_reason"]),
                        tqqq_signal=bool(srow["tqqq_signal"]),
                        soxl_signal=bool(srow["soxl_signal"]),
                        qqq_rsi=float(srow["qqq_rsi"]),
                        qqq_spy_signal=bool(srow["qqq_leading_spy"]),
                        obv_sma20_signal=bool(srow["obv_above_sma20"]),
                        obv_sma50_signal=bool(srow["obv_above_sma50"]),
                        smh_momentum_signal=bool(srow["smh_momentum_positive"]),
                        qqq_sma_slope_signal=bool(srow["qqq_sma_slope_positive"]),
                        technical_details={
                            "qqq_spy_ratio": float(srow["qqq_spy_ratio"]),
                            "qqq_spy_ratio_sma": float(srow["qqq_spy_ratio_sma"]),
                            "tqqq_obv": float(srow["tqqq_obv"]),
                            "smh_momentum": float(srow["smh_momentum"]),
                            "execution_note": "Executed at next-bar close (no lookahead).",
                        },
                    )
                )

            last_executed = dict(prev_targets)

        # 3) Recompute post-rebalance portfolio value at today's close.
        holdings_value = sum(shares[t] * px[t] for t in TRADABLE_ASSETS)
        pv = cash + holdings_value

        # Record daily holdings (per ticker) and portfolio snapshot.
        srow = sig.loc[ts]
        targets_today = {a: float(srow[target_cols[a]]) for a in TRADABLE_ASSETS}
        for t in TRADABLE_ASSETS:
            mv = shares[t] * px[t]
            holding_rows.append(
                {
                    "date": ts.date(),
                    "ticker": t,
                    "shares": shares[t],
                    "close_price": px[t],
                    "market_value": mv,
                    "target_weight": targets_today[t],
                    "actual_weight": mv / pv if pv > 0 else 0.0,
                    "cash": cash,
                    "portfolio_value": pv,
                }
            )

        daily_rows.append(
            {
                "date": ts.date(),
                "portfolio_value": pv,
                "cash": cash,
                "exposure": holdings_value / pv if pv > 0 else 0.0,
                "cash_pct": cash / pv if pv > 0 else 0.0,
                "target_weight_cash": float(srow["target_weight_cash"]),
            }
        )

        # 4) Today's signal becomes tomorrow's execution target.
        prev_targets = targets_today

    daily = pd.DataFrame(daily_rows).set_index("date")
    daily.index = pd.to_datetime(daily.index)
    equity = daily["portfolio_value"]
    daily["daily_return"] = equity.pct_change().fillna(0.0)
    daily["drawdown"] = M.drawdown_series(equity)

    # SPY benchmark, scaled to same initial capital, over the same window.
    spy_close = prices["SPY"]["close"].reindex(full_index)
    spy_equity = spy_close / spy_close.iloc[0] * initial_capital
    spy_equity.index = pd.to_datetime(full_index)
    daily["spy_value"] = spy_equity.values
    daily["spy_return"] = spy_equity.pct_change().fillna(0.0).values
    daily["spy_drawdown"] = M.drawdown_series(spy_equity).values

    holdings = pd.DataFrame(holding_rows)
    holdings["date"] = pd.to_datetime(holdings["date"])
    # attach daily return & drawdown (portfolio-level) onto holdings rows
    dmap_ret = daily["daily_return"]
    dmap_dd = daily["drawdown"]
    holdings["daily_return"] = holdings["date"].map(dmap_ret)
    holdings["drawdown"] = holdings["date"].map(dmap_dd)

    # In-sample / out-of-sample split (by time, chronological).
    n = len(equity)
    split_i = max(1, min(n - 1, int(round(n * in_sample_ratio))))
    split_ts = equity.index[split_i]
    eq_in = equity.iloc[: split_i + 1]
    eq_out = equity.iloc[split_i:]

    result = BacktestResult(
        signals=sig.loc[full_index].copy(),
        daily=daily,
        holdings=holdings,
        trades=trades,
        metrics_full=_with_trade_stats(M.summarize(equity), daily, trades, initial_capital),
        metrics_in=_with_trade_stats(M.summarize(eq_in), daily.loc[eq_in.index], trades, initial_capital, eq_in.index),
        metrics_out=_with_trade_stats(M.summarize(eq_out), daily.loc[eq_out.index], trades, initial_capital, eq_out.index),
        split_date=split_ts.date(),
        spy_metrics_full={
            "cagr": M.cagr(spy_equity),
            "total_return": M.total_return(spy_equity),
            "max_drawdown": M.max_drawdown(spy_equity),
        },
        extra={},
    )
    return result


def _with_trade_stats(
    base: dict[str, float],
    daily: pd.DataFrame,
    trades: list[TradeRecord],
    initial_capital: float,
    index: pd.Index | None = None,
) -> dict[str, float]:
    """Augment a metrics dict with trade-count / turnover / exposure stats."""
    out = dict(base)
    if index is not None:
        dates = set(pd.to_datetime(index).date)
        period_trades = [t for t in trades if t.date in dates]
    else:
        period_trades = trades
    out["number_of_trades"] = len(period_trades)
    pv_mean = daily["portfolio_value"].mean() if len(daily) else initial_capital
    traded_notional = sum(t.notional for t in period_trades)
    out["turnover"] = float(traded_notional / pv_mean) if pv_mean else 0.0
    out["avg_exposure"] = float(daily["exposure"].mean()) if len(daily) else 0.0
    out["avg_cash_pct"] = float(daily["cash_pct"].mean()) if len(daily) else 0.0
    return out
