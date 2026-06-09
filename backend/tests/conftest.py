"""Shared test fixtures: deterministic synthetic price data."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.engine.params import TICKERS


def make_prices(n_days: int = 600, seed: int = 42) -> dict[str, pd.DataFrame]:
    """Generate deterministic synthetic OHLCV for all required tickers."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2018-01-01", periods=n_days)
    prices: dict[str, pd.DataFrame] = {}
    for i, t in enumerate(TICKERS):
        drift = 0.0003 + i * 0.00005
        vol = 0.01 + (i % 3) * 0.004
        rets = rng.normal(drift, vol, n_days)
        close = 100.0 * np.exp(np.cumsum(rets))
        high = close * (1 + rng.uniform(0, 0.01, n_days))
        low = close * (1 - rng.uniform(0, 0.01, n_days))
        open_ = close * (1 + rng.uniform(-0.005, 0.005, n_days))
        volume = rng.integers(1_000_000, 5_000_000, n_days).astype(float)
        prices[t] = pd.DataFrame(
            {
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            },
            index=dates,
        )
    return prices


@pytest.fixture
def prices() -> dict[str, pd.DataFrame]:
    return make_prices()
