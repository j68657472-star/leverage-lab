"""Strategy parameters and configuration.

Centralizes every tunable knob of the strategy so that the UI, API and engine
all agree on names, defaults and validation. Keeping this separate from the
calculation logic keeps the engine deterministic and easy to test.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any

# Universe of tickers the strategy needs. Order matters only for display.
TICKERS: list[str] = ["TQQQ", "SOXL", "QQQ", "SPY", "SMH", "GLD", "SVXY"]

# Assets that can actually be *held* by the portfolio (plus implicit CASH).
TRADABLE_ASSETS: list[str] = ["TQQQ", "SOXL", "GLD", "SVXY"]

BENCHMARK = "SPY"


@dataclass
class StrategyParams:
    """All tunable strategy parameters with sane defaults.

    These defaults reproduce the originally specified strategy:
      max allocation 25% TQQQ / 25% SOXL / 50% CASH
    (because deleverage_factor=0.5 and fixed_cash_weight=0.5).
    """

    # --- signal parameters ---
    rsi_period: int = 14
    rsi_reentry: float = 30.0
    qqq_rsi_overbought: float = 75.0
    qqq_spy_ratio_period: int = 50
    obv_sma_short: int = 20
    obv_sma_long: int = 50
    smh_mom_period: int = 63
    qqq_sma150_period: int = 150
    qqq_sma150_slope_lookback: int = 10

    # --- portfolio construction ---
    deleverage_factor: float = 0.5
    fixed_cash_weight: float = 0.5

    # --- trading frictions ---
    transaction_cost_bps: float = 5.0
    slippage_bps: float = 0.0
    allow_fractional_shares: bool = True

    def validate(self) -> None:
        """Raise ValueError with a friendly message if anything is invalid."""
        errors: list[str] = []
        if self.rsi_period < 2:
            errors.append("RSI period must be at least 2.")
        if not (0 <= self.rsi_reentry <= 100):
            errors.append("RSI re-entry level must be between 0 and 100.")
        if not (0 <= self.qqq_rsi_overbought <= 100):
            errors.append("QQQ overbought level must be between 0 and 100.")
        for name in (
            "qqq_spy_ratio_period",
            "obv_sma_short",
            "obv_sma_long",
            "smh_mom_period",
            "qqq_sma150_period",
            "qqq_sma150_slope_lookback",
        ):
            if getattr(self, name) < 1:
                errors.append(f"{name} must be a positive whole number.")
        if not (0.0 <= self.deleverage_factor <= 1.0):
            errors.append("Deleverage factor must be between 0 and 1.")
        if not (0.0 <= self.fixed_cash_weight <= 1.0):
            errors.append("Fixed cash weight must be between 0 and 1.")
        if self.transaction_cost_bps < 0:
            errors.append("Transaction cost cannot be negative.")
        if self.slippage_bps < 0:
            errors.append("Slippage cannot be negative.")
        if errors:
            raise ValueError(" ".join(errors))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "StrategyParams":
        data = data or {}
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    @property
    def warmup_days(self) -> int:
        """Largest lookback any indicator needs, used to trim the warm-up window."""
        return max(
            self.rsi_period,
            self.qqq_spy_ratio_period,
            self.obv_sma_long,
            self.smh_mom_period,
            self.qqq_sma150_period + self.qqq_sma150_slope_lookback,
        )
