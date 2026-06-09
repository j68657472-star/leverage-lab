"""Performance metrics. Pure functions over a daily equity / returns series."""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def daily_returns(equity: pd.Series) -> pd.Series:
    return equity.pct_change().fillna(0.0)


def total_return(equity: pd.Series) -> float:
    if len(equity) < 2 or equity.iloc[0] == 0:
        return 0.0
    return float(equity.iloc[-1] / equity.iloc[0] - 1.0)


def cagr(equity: pd.Series) -> float:
    if len(equity) < 2 or equity.iloc[0] <= 0:
        return 0.0
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    if years <= 0:
        return 0.0
    growth = equity.iloc[-1] / equity.iloc[0]
    if growth <= 0:
        return -1.0
    return float(growth ** (1.0 / years) - 1.0)


def volatility(returns: pd.Series) -> float:
    if len(returns) < 2:
        return 0.0
    return float(returns.std(ddof=1) * np.sqrt(TRADING_DAYS))


def sharpe(returns: pd.Series, risk_free: float = 0.0) -> float:
    if len(returns) < 2:
        return 0.0
    excess = returns - risk_free / TRADING_DAYS
    sd = excess.std(ddof=1)
    if sd == 0 or np.isnan(sd):
        return 0.0
    return float(excess.mean() / sd * np.sqrt(TRADING_DAYS))


def drawdown_series(equity: pd.Series) -> pd.Series:
    running_max = equity.cummax()
    return equity / running_max - 1.0


def max_drawdown(equity: pd.Series) -> float:
    if len(equity) < 2:
        return 0.0
    return float(drawdown_series(equity).min())


def win_rate(returns: pd.Series) -> float:
    nonzero = returns[returns != 0.0]
    if len(nonzero) == 0:
        return 0.0
    return float((nonzero > 0).mean())


def best_day(returns: pd.Series) -> float:
    return float(returns.max()) if len(returns) else 0.0


def worst_day(returns: pd.Series) -> float:
    return float(returns.min()) if len(returns) else 0.0


def summarize(equity: pd.Series) -> dict[str, float]:
    """Return the core scalar metrics for an equity curve."""
    rets = daily_returns(equity)
    return {
        "cagr": cagr(equity),
        "sharpe": sharpe(rets),
        "max_drawdown": max_drawdown(equity),
        "total_return": total_return(equity),
        "volatility": volatility(rets),
        "win_rate": win_rate(rets),
        "best_day": best_day(rets),
        "worst_day": worst_day(rets),
        "final_value": float(equity.iloc[-1]) if len(equity) else 0.0,
    }
