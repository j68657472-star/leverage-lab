import numpy as np
import pandas as pd

from app.engine.params import StrategyParams
from app.engine.signals import compute_signal_frame
from tests.conftest import make_prices


def test_signal_frame_columns(prices):
    df = compute_signal_frame(prices, StrategyParams())
    for col in [
        "tqqq_signal",
        "soxl_signal",
        "qqq_rsi",
        "qqq_leading_spy",
        "obv_above_sma20",
        "obv_above_sma50",
        "smh_momentum_positive",
        "qqq_sma_slope_positive",
        "target_weight_tqqq",
        "target_weight_cash",
        "signal_reason",
    ]:
        assert col in df.columns


def test_weights_sum_to_one(prices):
    df = compute_signal_frame(prices, StrategyParams())
    ready = df[df["ready"]]
    wsum = (
        ready["target_weight_tqqq"]
        + ready["target_weight_soxl"]
        + ready["target_weight_gld"]
        + ready["target_weight_svxy"]
        + ready["target_weight_cash"]
    )
    assert np.allclose(wsum.values, 1.0)


def test_default_max_allocation_25_25_50():
    """When both sleeves are ON, default delever=0.5 => 25% TQQQ, 25% SOXL, 50% cash."""
    p = StrategyParams()
    df = pd.DataFrame(
        {
            "tqqq_signal": [True],
            "soxl_signal": [True],
        }
    )
    from app.engine.signals import _build_weights

    w = _build_weights(df, p)
    assert abs(w["target_weight_tqqq"].iloc[0] - 0.25) < 1e-9
    assert abs(w["target_weight_soxl"].iloc[0] - 0.25) < 1e-9
    assert abs(w["target_weight_cash"].iloc[0] - 0.50) < 1e-9


def test_tqqq_off_goes_defensive():
    """TQQQ off -> sleeve splits into GLD+SVXY (then delevered)."""
    p = StrategyParams()
    from app.engine.signals import _build_weights

    df = pd.DataFrame({"tqqq_signal": [False], "soxl_signal": [False]})
    w = _build_weights(df, p)
    # TQQQ sleeve off: 25% GLD + 25% SVXY (orig). SOXL off: 50% GLD (orig).
    # delever 0.5 -> GLD = (0.25+0.5)*0.5=0.375 ; SVXY = 0.25*0.5=0.125
    assert abs(w["target_weight_gld"].iloc[0] - 0.375) < 1e-9
    assert abs(w["target_weight_svxy"].iloc[0] - 0.125) < 1e-9
    assert abs(w["target_weight_tqqq"].iloc[0]) < 1e-9


def test_deleverage_factor_one_no_cash_added():
    p = StrategyParams(deleverage_factor=1.0, fixed_cash_weight=0.0)
    from app.engine.signals import _build_weights

    df = pd.DataFrame({"tqqq_signal": [True], "soxl_signal": [True]})
    w = _build_weights(df, p)
    assert abs(w["target_weight_tqqq"].iloc[0] - 0.50) < 1e-9
    assert abs(w["target_weight_soxl"].iloc[0] - 0.50) < 1e-9
    assert abs(w["target_weight_cash"].iloc[0]) < 1e-9


def test_soxl_signal_logic():
    """Directly verify SOXL AND-conditions via a crafted frame."""
    p = StrategyParams()
    prices = make_prices(400, seed=1)
    df = compute_signal_frame(prices, p)
    ready = df[df["ready"]]
    # SOXL on implies all four conditions true.
    on = ready[ready["soxl_signal"]]
    assert (on["qqq_leading_spy"]).all()
    assert (on["qqq_rsi"] < p.qqq_rsi_overbought).all()
    assert (on["smh_momentum_positive"]).all()
    assert (on["qqq_sma_slope_positive"]).all()


def test_tqqq_rsi_override():
    """If QQQ RSI < reentry, TQQQ signal must be true regardless of trend."""
    p = StrategyParams()
    prices = make_prices(400, seed=7)
    df = compute_signal_frame(prices, p)
    ready = df[df["ready"]]
    override = ready[ready["qqq_rsi"] < p.rsi_reentry]
    if len(override) > 0:
        assert override["tqqq_signal"].all()
