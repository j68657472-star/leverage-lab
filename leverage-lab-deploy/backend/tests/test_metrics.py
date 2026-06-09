import numpy as np
import pandas as pd

from app.engine import metrics as M


def _equity(values):
    idx = pd.bdate_range("2020-01-01", periods=len(values))
    return pd.Series(values, index=idx, dtype=float)


def test_total_return():
    eq = _equity([100, 110, 121])
    assert abs(M.total_return(eq) - 0.21) < 1e-9


def test_cagr_one_year_doubling():
    idx = pd.to_datetime(["2020-01-01", "2021-01-01"])
    eq = pd.Series([100.0, 200.0], index=idx)
    assert abs(M.cagr(eq) - 1.0) < 0.01


def test_max_drawdown():
    eq = _equity([100, 120, 60, 80, 200])
    # peak 120 -> trough 60 = -50%
    assert abs(M.max_drawdown(eq) - (-0.5)) < 1e-9


def test_sharpe_zero_vol():
    eq = _equity([100, 100, 100, 100])
    assert M.sharpe(M.daily_returns(eq)) == 0.0


def test_sharpe_positive():
    rng = np.random.default_rng(0)
    rets = pd.Series(rng.normal(0.001, 0.01, 500))
    s = M.sharpe(rets)
    assert s > 0


def test_volatility():
    rets = pd.Series([0.01, -0.01, 0.01, -0.01] * 50)
    v = M.volatility(rets)
    assert v > 0


def test_win_rate():
    rets = pd.Series([0.01, -0.01, 0.0, 0.02, -0.03])
    # nonzero: +,-,+,- => 2 wins / 4 = 0.5
    assert abs(M.win_rate(rets) - 0.5) < 1e-9


def test_summarize_keys():
    eq = _equity(list(np.linspace(100, 150, 300)))
    s = M.summarize(eq)
    for k in ["cagr", "sharpe", "max_drawdown", "total_return", "volatility",
              "win_rate", "best_day", "worst_day", "final_value"]:
        assert k in s
