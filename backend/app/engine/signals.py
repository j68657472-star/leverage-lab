"""Signal generation and target-weight construction.

Given a dict of per-ticker OHLCV DataFrames, produce a daily DataFrame of:
  - raw indicator values
  - boolean component signals
  - the two sleeve signals (TQQQ / SOXL)
  - target weights (TQQQ, SOXL, GLD, SVXY, CASH)
  - a human-readable reason string

NO-LOOKAHEAD: every column is causal (uses only data up to and including that
day's close). The decision of *when to execute* a rebalance (next bar) lives in
the backtest engine, not here.
"""
from __future__ import annotations

import pandas as pd

from . import indicators as ind
from .params import StrategyParams


def _aligned_close(prices: dict[str, pd.DataFrame], ticker: str) -> pd.Series:
    return prices[ticker]["close"]


def compute_signal_frame(
    prices: dict[str, pd.DataFrame], params: StrategyParams
) -> pd.DataFrame:
    """Build the full daily signal/weights DataFrame.

    `prices[ticker]` must be a DataFrame with at least columns:
    ['open','high','low','close','volume'] indexed by date (ascending).
    All tickers in params universe must be present and aligned to a common index.
    """
    # Common trading calendar = intersection of all needed tickers' indices.
    needed = ["TQQQ", "SOXL", "QQQ", "SPY", "SMH", "GLD", "SVXY"]
    idx = None
    for t in needed:
        if t not in prices:
            raise ValueError(f"Missing price data for required ticker: {t}")
        idx = prices[t].index if idx is None else idx.intersection(prices[t].index)
    idx = idx.sort_values()

    qqq = _aligned_close(prices, "QQQ").reindex(idx)
    spy = _aligned_close(prices, "SPY").reindex(idx)
    smh = _aligned_close(prices, "SMH").reindex(idx)
    tqqq_close = _aligned_close(prices, "TQQQ").reindex(idx)
    tqqq_vol = prices["TQQQ"]["volume"].reindex(idx)

    df = pd.DataFrame(index=idx)

    # --- QQQ RSI ---
    df["qqq_rsi"] = ind.rsi(qqq, params.rsi_period)

    # --- QQQ / SPY relative strength ---
    ratio = qqq / spy
    ratio_sma = ind.sma(ratio, params.qqq_spy_ratio_period)
    df["qqq_spy_ratio"] = ratio
    df["qqq_spy_ratio_sma"] = ratio_sma
    df["qqq_leading_spy"] = ratio > ratio_sma

    # --- TQQQ OBV ---
    obv_series = ind.obv(tqqq_close, tqqq_vol)
    obv_s = ind.sma(obv_series, params.obv_sma_short)
    obv_l = ind.sma(obv_series, params.obv_sma_long)
    df["tqqq_obv"] = obv_series
    df["tqqq_obv_sma20"] = obv_s
    df["tqqq_obv_sma50"] = obv_l
    df["obv_above_sma20"] = obv_series > obv_s
    df["obv_above_sma50"] = obv_series > obv_l

    # --- SMH momentum ---
    smh_mom = ind.momentum(smh, params.smh_mom_period)
    df["smh_momentum"] = smh_mom
    df["smh_momentum_positive"] = smh_mom > 0

    # --- QQQ 150 SMA slope ---
    qqq_sma150 = ind.sma(qqq, params.qqq_sma150_period)
    df["qqq_sma150"] = qqq_sma150
    df["qqq_sma_slope_positive"] = ind.slope_positive(
        qqq_sma150, params.qqq_sma150_slope_lookback
    )

    # ---------------- TQQQ sleeve signal ----------------
    # stay-in = OBV>SMA20 AND QQQ leading SPY AND OBV>SMA50
    stay_in = (
        df["obv_above_sma20"] & df["qqq_leading_spy"] & df["obv_above_sma50"]
    )
    # RSI override (oversold re-entry) = QQQ RSI < RSI_REENTRY
    rsi_override = df["qqq_rsi"] < params.rsi_reentry
    df["tqqq_signal"] = stay_in | rsi_override

    # ---------------- SOXL sleeve signal ----------------
    df["soxl_signal"] = (
        df["qqq_leading_spy"]
        & (df["qqq_rsi"] < params.qqq_rsi_overbought)
        & df["smh_momentum_positive"]
        & df["qqq_sma_slope_positive"]
    )

    # Rows where any required indicator is still warming up -> signals undefined.
    warm = (
        df["qqq_rsi"].notna()
        & df["qqq_spy_ratio_sma"].notna()
        & df["tqqq_obv_sma50"].notna()
        & df["smh_momentum"].notna()
        & df["qqq_sma150"].notna()
        & ind.sma(qqq, params.qqq_sma150_period)
        .shift(params.qqq_sma150_slope_lookback)
        .notna()
    )
    df["ready"] = warm

    # Before warmup completes the signals are treated as False (stay in cash).
    df.loc[~df["ready"], ["tqqq_signal", "soxl_signal"]] = False

    # ---------------- Target weights ----------------
    weights = _build_weights(df, params)
    df = pd.concat([df, weights], axis=1)

    df["signal_reason"] = _build_reasons(df)
    return df


def _build_weights(df: pd.DataFrame, params: StrategyParams) -> pd.DataFrame:
    """Convert sleeve signals into deleveraged target weights + fixed cash."""
    k = params.deleverage_factor

    # --- Original (full-leverage) sleeve weights ---
    # TQQQ sleeve = 50%: TQQQ if signal else 25% GLD + 25% SVXY
    tqqq_on = df["tqqq_signal"]
    w_tqqq = tqqq_on.astype(float) * 0.50
    gld_from_tqqq = (~tqqq_on).astype(float) * 0.25
    svxy_from_tqqq = (~tqqq_on).astype(float) * 0.25

    # SOXL sleeve = 50%: SOXL if signal else 50% GLD
    soxl_on = df["soxl_signal"]
    w_soxl = soxl_on.astype(float) * 0.50
    gld_from_soxl = (~soxl_on).astype(float) * 0.50

    w_gld_orig = gld_from_tqqq + gld_from_soxl
    w_svxy_orig = svxy_from_tqqq

    # --- Delever: multiply all risk weights by k, then add fixed cash ---
    out = pd.DataFrame(index=df.index)
    out["target_weight_tqqq"] = w_tqqq * k
    out["target_weight_soxl"] = w_soxl * k
    out["target_weight_gld"] = w_gld_orig * k
    out["target_weight_svxy"] = w_svxy_orig * k

    risk_total = (
        out["target_weight_tqqq"]
        + out["target_weight_soxl"]
        + out["target_weight_gld"]
        + out["target_weight_svxy"]
    )
    # Cash = fixed cash weight + whatever leverage we removed.
    out["target_weight_cash"] = 1.0 - risk_total
    return out


def _build_reasons(df: pd.DataFrame) -> pd.Series:
    """Plain-English explanation of each day's allocation decision."""
    reasons = []
    for _, r in df.iterrows():
        if not r["ready"]:
            reasons.append("Warming up indicators — holding cash until enough history is available.")
            continue
        parts: list[str] = []
        if r["tqqq_signal"]:
            why = []
            if r["obv_above_sma20"] and r["obv_above_sma50"] and r["qqq_leading_spy"]:
                why.append("TQQQ trend healthy (OBV above its averages, QQQ leading SPY)")
            if r["qqq_rsi"] < 30:
                why.append("QQQ oversold re-entry")
            parts.append("Hold TQQQ: " + " / ".join(why) + ".")
        else:
            parts.append("Avoid TQQQ (trend weak) → defensive GLD + SVXY.")
        if r["soxl_signal"]:
            parts.append(
                "Hold SOXL: QQQ leading SPY, not overbought, SMH momentum positive, QQQ trend rising."
            )
        else:
            parts.append("Avoid SOXL (a condition failed) → defensive GLD.")
        reasons.append(" ".join(parts))
    return pd.Series(reasons, index=df.index)
