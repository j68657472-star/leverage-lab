import numpy as np
import pandas as pd
import pytest

from app.engine.backtest import run_backtest
from app.engine.params import StrategyParams
from tests.conftest import make_prices


def test_backtest_runs(prices):
    res = run_backtest(prices, StrategyParams(), initial_capital=100_000)
    assert len(res.daily) > 100
    assert res.daily["portfolio_value"].iloc[0] > 0
    assert "cagr" in res.metrics_full


def test_no_lookahead_first_day_no_trade(prices):
    """On the very first trading day there is no prior signal, so no trade."""
    res = run_backtest(prices, StrategyParams(), initial_capital=100_000)
    first_date = res.daily.index[0].date()
    first_day_trades = [t for t in res.trades if t.date == first_date]
    assert first_day_trades == []


def test_no_lookahead_execution_uses_prior_signal():
    """Trade target weight on day t must equal signal target from day t-1."""
    prices = make_prices(400, seed=3)
    p = StrategyParams()
    res = run_backtest(prices, p, initial_capital=100_000)
    sig = res.signals
    tcol = {
        "TQQQ": "target_weight_tqqq",
        "SOXL": "target_weight_soxl",
        "GLD": "target_weight_gld",
        "SVXY": "target_weight_svxy",
    }
    idx = list(res.daily.index)
    for tr in res.trades[:50]:
        ts = pd.Timestamp(tr.date)
        pos = idx.index(ts)
        if pos == 0:
            continue
        prev_ts = idx[pos - 1]
        expected = float(sig.loc[prev_ts, tcol[tr.ticker]])
        assert abs(tr.target_weight - expected) < 1e-9


def test_cash_never_extremely_negative(prices):
    """With fractional shares and target weights <=1, cash should stay >= ~0."""
    res = run_backtest(prices, StrategyParams(), initial_capital=100_000)
    # Allow tiny negative from transaction costs rounding only.
    assert res.daily["cash"].min() > -1.0


def test_transaction_cost_reduces_value():
    prices = make_prices(400, seed=5)
    no_cost = run_backtest(
        prices, StrategyParams(transaction_cost_bps=0), initial_capital=100_000
    )
    with_cost = run_backtest(
        prices, StrategyParams(transaction_cost_bps=50), initial_capital=100_000
    )
    assert (
        with_cost.daily["portfolio_value"].iloc[-1]
        < no_cost.daily["portfolio_value"].iloc[-1]
    )


def test_trade_records_have_reasons(prices):
    res = run_backtest(prices, StrategyParams(), initial_capital=100_000)
    assert len(res.trades) > 0
    for tr in res.trades:
        assert isinstance(tr.signal_reason, str) and len(tr.signal_reason) > 0


def test_in_out_sample_split(prices):
    res = run_backtest(prices, StrategyParams(), initial_capital=100_000, in_sample_ratio=0.70)
    assert res.split_date > res.daily.index[0].date()
    assert res.split_date < res.daily.index[-1].date()
    assert "cagr" in res.metrics_in
    assert "cagr" in res.metrics_out


def test_holdings_generated(prices):
    res = run_backtest(prices, StrategyParams(), initial_capital=100_000)
    assert len(res.holdings) > 0
    assert set(["TQQQ", "SOXL", "GLD", "SVXY"]).issubset(set(res.holdings["ticker"]))


def test_missing_price_raises():
    prices = make_prices(400)
    # Poke a NaN into TQQQ inside the window.
    prices["TQQQ"].iloc[200, prices["TQQQ"].columns.get_loc("close")] = np.nan
    with pytest.raises(ValueError):
        run_backtest(prices, StrategyParams(), initial_capital=100_000,
                     start=prices["TQQQ"].index[180].date())


def test_initial_capital_validation(prices):
    with pytest.raises(ValueError):
        run_backtest(prices, StrategyParams(), initial_capital=0)
