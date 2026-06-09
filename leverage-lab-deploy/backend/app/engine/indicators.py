"""Technical indicators used by the strategy.

Every function here is a pure function of its inputs (no I/O, no global state),
which makes them deterministic and trivial to unit-test. They operate on pandas
Series indexed by date.

IMPORTANT (no-lookahead): all indicators are causal. A value at index t is
computed using only data at or before t. Rebalance execution timing (t+1) is
handled by the backtest engine, not here.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Simple RSI using rolling average gain / average loss.

    Uses a simple moving average of gains and losses (not Wilder's smoothing),
    matching the specified "rolling average gain and rolling average loss".
    """
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    rs = avg_gain / avg_loss
    out = 100.0 - (100.0 / (1.0 + rs))
    # If avg_loss == 0 and avg_gain > 0 -> RSI 100. If both 0 -> 50 (flat).
    out = out.where(avg_loss != 0, other=100.0)
    out = out.where(~((avg_loss == 0) & (avg_gain == 0)), other=50.0)
    out[avg_gain.isna() | avg_loss.isna()] = np.nan
    return out


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On-Balance Volume.

    +volume when price rises, -volume when it falls, 0 when unchanged.
    The first bar has no prior price, so OBV starts at 0.
    """
    direction = np.sign(close.diff().fillna(0.0))
    signed_volume = direction * volume
    out = signed_volume.cumsum()
    return out


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple moving average."""
    return series.rolling(window=period, min_periods=period).mean()


def momentum(close: pd.Series, period: int) -> pd.Series:
    """Momentum as a simple return over `period` bars: close / close[-period] - 1."""
    return close / close.shift(period) - 1.0


def slope_positive(series: pd.Series, lookback: int) -> pd.Series:
    """Boolean: is the series higher than it was `lookback` bars ago?"""
    return series > series.shift(lookback)
