"""Typed request/response models (Pydantic v2)."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class StrategyParamsIn(BaseModel):
    rsi_period: int = 14
    rsi_reentry: float = 30.0
    qqq_rsi_overbought: float = 75.0
    qqq_spy_ratio_period: int = 50
    obv_sma_short: int = 20
    obv_sma_long: int = 50
    smh_mom_period: int = 63
    qqq_sma150_period: int = 150
    qqq_sma150_slope_lookback: int = 10
    deleverage_factor: float = 0.5
    fixed_cash_weight: float = 0.5
    transaction_cost_bps: float = 5.0
    slippage_bps: float = 0.0
    allow_fractional_shares: bool = True


class RunBacktestRequest(BaseModel):
    anonymous_user_id: str
    run_name: Optional[str] = None
    initial_capital: float = Field(default=100_000, gt=0)
    start_date: Optional[str] = None  # ISO date
    end_date: Optional[str] = None
    in_sample_ratio: float = Field(default=0.70, ge=0.1, le=0.95)
    params: StrategyParamsIn = StrategyParamsIn()


class MetricsOut(BaseModel):
    period_name: str
    cagr: float
    sharpe: float
    max_drawdown: float
    total_return: float
    volatility: float
    win_rate: float
    best_day: float
    worst_day: float
    number_of_trades: int
    turnover: float
    avg_exposure: float
    avg_cash_pct: float
    final_value: float
    spy_cagr: float
    spy_total_return: float
    spy_max_drawdown: float


class RunSummary(BaseModel):
    run_id: str
    run_name: str
    created_at: str
    start_date: str
    end_date: str
    initial_capital: float
    status: str
    error_message: Optional[str] = None
    cagr: Optional[float] = None
    sharpe: Optional[float] = None
    max_drawdown: Optional[float] = None
    total_return: Optional[float] = None
    in_sample_cagr: Optional[float] = None
    out_of_sample_cagr: Optional[float] = None
    spy_cagr: Optional[float] = None
    final_value: Optional[float] = None


class RunDetail(RunSummary):
    in_sample_ratio: float
    out_of_sample_ratio: float
    params: dict[str, Any]
    metrics: list[MetricsOut]


class RenameRequest(BaseModel):
    run_name: str


class CompareRequest(BaseModel):
    run_ids: list[str] = Field(min_length=2, max_length=4)


class CreatePaperRequest(BaseModel):
    anonymous_user_id: str
    name: Optional[str] = None
    initial_capital: float = Field(default=100_000, gt=0)
    params: StrategyParamsIn = StrategyParamsIn()
