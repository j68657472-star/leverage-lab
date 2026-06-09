import numpy as np
import pandas as pd

from app.engine import indicators as ind


def test_rsi_all_gains_is_100():
    s = pd.Series(np.arange(1, 30, dtype=float))
    r = ind.rsi(s, 14)
    assert r.dropna().iloc[-1] == 100.0


def test_rsi_all_losses_is_zero():
    s = pd.Series(np.arange(30, 1, -1, dtype=float))
    r = ind.rsi(s, 14)
    assert r.dropna().iloc[-1] == 0.0


def test_rsi_known_value():
    # Alternating up/down by equal amounts -> avg gain == avg loss -> RSI 50.
    vals = []
    p = 100.0
    for i in range(40):
        p = p + 1 if i % 2 == 0 else p - 1
        vals.append(p)
    s = pd.Series(vals, dtype=float)
    r = ind.rsi(s, 14)
    assert abs(r.dropna().iloc[-1] - 50.0) < 5.0


def test_rsi_warmup_nan():
    s = pd.Series(np.arange(1, 30, dtype=float))
    r = ind.rsi(s, 14)
    assert r.iloc[:14].isna().all()


def test_obv_direction():
    close = pd.Series([10, 11, 10, 10, 12], dtype=float)
    vol = pd.Series([100, 200, 300, 400, 500], dtype=float)
    o = ind.obv(close, vol)
    # day0: 0; day1 up +200 ->200; day2 down -300 ->-100; day3 flat +0 ->-100; day4 up +500 ->400
    assert list(o.values) == [0.0, 200.0, -100.0, -100.0, 400.0]


def test_sma():
    s = pd.Series([1, 2, 3, 4, 5], dtype=float)
    m = ind.sma(s, 2)
    assert m.iloc[1] == 1.5 and m.iloc[-1] == 4.5
    assert np.isnan(m.iloc[0])


def test_momentum():
    s = pd.Series([100, 110, 121], dtype=float)
    m = ind.momentum(s, 1)
    assert abs(m.iloc[1] - 0.10) < 1e-9


def test_slope_positive():
    s = pd.Series([1, 2, 3, 2, 1], dtype=float)
    sp = ind.slope_positive(s, 1)
    assert sp.iloc[2] and not sp.iloc[3]
