"""SQLAlchemy ORM models mapping the spec's database tables.

JSON blobs are stored as TEXT-serialized JSON via the `JSONText` type so the
schema works identically on SQLite (local dev) and PostgreSQL (production).
"""
from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from .db import Base


class JSONText(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return json.dumps(value) if value is not None else None

    def process_result_value(self, value, dialect):
        return json.loads(value) if value else None


def _utcnow() -> datetime:
    return datetime.utcnow()


class AnonymousUser(Base):
    __tablename__ = "anonymous_users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    anonymous_user_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class BacktestRun(Base):
    __tablename__ = "backtest_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    anonymous_user_id: Mapped[str] = mapped_column(String(64), index=True)
    run_name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    start_date: Mapped[str] = mapped_column(String(20))
    end_date: Mapped[str] = mapped_column(String(20))
    initial_capital: Mapped[float] = mapped_column(Float)
    in_sample_ratio: Mapped[float] = mapped_column(Float, default=0.70)
    out_of_sample_ratio: Mapped[float] = mapped_column(Float, default=0.30)
    params_json: Mapped[dict] = mapped_column(JSONText)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    metrics = relationship("BacktestMetric", cascade="all, delete-orphan", backref="run")
    daily_values = relationship("DailyPortfolioValue", cascade="all, delete-orphan", backref="run")
    holdings = relationship("DailyHolding", cascade="all, delete-orphan", backref="run")
    trades = relationship("TradeRecordRow", cascade="all, delete-orphan", backref="run")
    signals = relationship("StrategySignal", cascade="all, delete-orphan", backref="run")


class BacktestMetric(Base):
    __tablename__ = "backtest_metrics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("backtest_runs.run_id"), index=True)
    period_name: Mapped[str] = mapped_column(String(20))  # full / in_sample / out_of_sample
    cagr: Mapped[float] = mapped_column(Float, default=0.0)
    sharpe: Mapped[float] = mapped_column(Float, default=0.0)
    max_drawdown: Mapped[float] = mapped_column(Float, default=0.0)
    total_return: Mapped[float] = mapped_column(Float, default=0.0)
    volatility: Mapped[float] = mapped_column(Float, default=0.0)
    win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    best_day: Mapped[float] = mapped_column(Float, default=0.0)
    worst_day: Mapped[float] = mapped_column(Float, default=0.0)
    number_of_trades: Mapped[int] = mapped_column(Integer, default=0)
    turnover: Mapped[float] = mapped_column(Float, default=0.0)
    avg_exposure: Mapped[float] = mapped_column(Float, default=0.0)
    avg_cash_pct: Mapped[float] = mapped_column(Float, default=0.0)
    final_value: Mapped[float] = mapped_column(Float, default=0.0)
    spy_cagr: Mapped[float] = mapped_column(Float, default=0.0)
    spy_total_return: Mapped[float] = mapped_column(Float, default=0.0)
    spy_max_drawdown: Mapped[float] = mapped_column(Float, default=0.0)


class DailyPortfolioValue(Base):
    __tablename__ = "daily_portfolio_values"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("backtest_runs.run_id"), index=True)
    date: Mapped[str] = mapped_column(String(20))
    portfolio_value: Mapped[float] = mapped_column(Float)
    cash: Mapped[float] = mapped_column(Float)
    daily_return: Mapped[float] = mapped_column(Float)
    drawdown: Mapped[float] = mapped_column(Float)
    spy_value: Mapped[float] = mapped_column(Float)
    spy_return: Mapped[float] = mapped_column(Float)
    spy_drawdown: Mapped[float] = mapped_column(Float)


class DailyHolding(Base):
    __tablename__ = "daily_holdings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("backtest_runs.run_id"), index=True)
    date: Mapped[str] = mapped_column(String(20))
    ticker: Mapped[str] = mapped_column(String(10))
    shares: Mapped[float] = mapped_column(Float)
    close_price: Mapped[float] = mapped_column(Float)
    market_value: Mapped[float] = mapped_column(Float)
    target_weight: Mapped[float] = mapped_column(Float)
    actual_weight: Mapped[float] = mapped_column(Float)
    cash: Mapped[float] = mapped_column(Float)
    portfolio_value: Mapped[float] = mapped_column(Float)
    daily_return: Mapped[float] = mapped_column(Float)
    drawdown: Mapped[float] = mapped_column(Float)


class TradeRecordRow(Base):
    __tablename__ = "trade_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("backtest_runs.run_id"), index=True)
    date: Mapped[str] = mapped_column(String(20))
    ticker: Mapped[str] = mapped_column(String(10))
    action: Mapped[str] = mapped_column(String(8))
    price: Mapped[float] = mapped_column(Float)
    shares: Mapped[float] = mapped_column(Float)
    notional: Mapped[float] = mapped_column(Float)
    transaction_cost: Mapped[float] = mapped_column(Float)
    old_weight: Mapped[float] = mapped_column(Float)
    new_weight: Mapped[float] = mapped_column(Float)
    target_weight: Mapped[float] = mapped_column(Float)
    actual_weight: Mapped[float] = mapped_column(Float)
    portfolio_value_before: Mapped[float] = mapped_column(Float)
    portfolio_value_after: Mapped[float] = mapped_column(Float)
    cash_before: Mapped[float] = mapped_column(Float)
    cash_after: Mapped[float] = mapped_column(Float)
    signal_reason: Mapped[str] = mapped_column(Text)
    tqqq_signal: Mapped[bool] = mapped_column(Boolean)
    soxl_signal: Mapped[bool] = mapped_column(Boolean)
    qqq_rsi: Mapped[float] = mapped_column(Float)
    qqq_spy_signal: Mapped[bool] = mapped_column(Boolean)
    obv_sma20_signal: Mapped[bool] = mapped_column(Boolean)
    obv_sma50_signal: Mapped[bool] = mapped_column(Boolean)
    smh_momentum_signal: Mapped[bool] = mapped_column(Boolean)
    qqq_sma_slope_signal: Mapped[bool] = mapped_column(Boolean)
    technical_details_json: Mapped[dict] = mapped_column(JSONText)


class StrategySignal(Base):
    __tablename__ = "strategy_signals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("backtest_runs.run_id"), index=True)
    date: Mapped[str] = mapped_column(String(20))
    tqqq_signal: Mapped[bool] = mapped_column(Boolean)
    soxl_signal: Mapped[bool] = mapped_column(Boolean)
    qqq_rsi: Mapped[float] = mapped_column(Float)
    qqq_spy_ratio: Mapped[float] = mapped_column(Float)
    qqq_spy_ratio_sma: Mapped[float] = mapped_column(Float)
    qqq_leading_spy: Mapped[bool] = mapped_column(Boolean)
    tqqq_obv: Mapped[float] = mapped_column(Float)
    tqqq_obv_sma20: Mapped[float] = mapped_column(Float)
    tqqq_obv_sma50: Mapped[float] = mapped_column(Float)
    obv_above_sma20: Mapped[bool] = mapped_column(Boolean)
    obv_above_sma50: Mapped[bool] = mapped_column(Boolean)
    smh_momentum: Mapped[float] = mapped_column(Float)
    smh_momentum_positive: Mapped[bool] = mapped_column(Boolean)
    qqq_sma150: Mapped[float] = mapped_column(Float)
    qqq_sma_slope_positive: Mapped[bool] = mapped_column(Boolean)
    target_weight_tqqq: Mapped[float] = mapped_column(Float)
    target_weight_soxl: Mapped[float] = mapped_column(Float)
    target_weight_gld: Mapped[float] = mapped_column(Float)
    target_weight_svxy: Mapped[float] = mapped_column(Float)
    target_weight_cash: Mapped[float] = mapped_column(Float)
    signal_reason: Mapped[str] = mapped_column(Text)


class PaperPortfolio(Base):
    __tablename__ = "paper_portfolios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    anonymous_user_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    initial_capital: Mapped[float] = mapped_column(Float)
    current_value: Mapped[float] = mapped_column(Float)
    cash: Mapped[float] = mapped_column(Float)
    params_json: Mapped[dict] = mapped_column(JSONText)
    status: Mapped[str] = mapped_column(String(20), default="active")
    last_updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    holdings_json: Mapped[dict] = mapped_column(JSONText, default=dict)

    snapshots = relationship("PaperSnapshot", cascade="all, delete-orphan", backref="portfolio")
    trades = relationship("PaperTrade", cascade="all, delete-orphan", backref="portfolio")


class PaperSnapshot(Base):
    __tablename__ = "paper_portfolio_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(String(64), ForeignKey("paper_portfolios.portfolio_id"), index=True)
    date: Mapped[str] = mapped_column(String(20))
    portfolio_value: Mapped[float] = mapped_column(Float)
    cash: Mapped[float] = mapped_column(Float)
    daily_return: Mapped[float] = mapped_column(Float)
    drawdown: Mapped[float] = mapped_column(Float)
    target_weights_json: Mapped[dict] = mapped_column(JSONText)
    actual_weights_json: Mapped[dict] = mapped_column(JSONText)
    signal_json: Mapped[dict] = mapped_column(JSONText)


class PaperTrade(Base):
    __tablename__ = "paper_trades"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(String(64), ForeignKey("paper_portfolios.portfolio_id"), index=True)
    date: Mapped[str] = mapped_column(String(20))
    ticker: Mapped[str] = mapped_column(String(10))
    action: Mapped[str] = mapped_column(String(8))
    price: Mapped[float] = mapped_column(Float)
    shares: Mapped[float] = mapped_column(Float)
    notional: Mapped[float] = mapped_column(Float)
    transaction_cost: Mapped[float] = mapped_column(Float)
    old_weight: Mapped[float] = mapped_column(Float)
    new_weight: Mapped[float] = mapped_column(Float)
    target_weight: Mapped[float] = mapped_column(Float)
    actual_weight: Mapped[float] = mapped_column(Float)
    portfolio_value_before: Mapped[float] = mapped_column(Float)
    portfolio_value_after: Mapped[float] = mapped_column(Float)
    cash_before: Mapped[float] = mapped_column(Float)
    cash_after: Mapped[float] = mapped_column(Float)
    signal_reason: Mapped[str] = mapped_column(Text)
    technical_details_json: Mapped[dict] = mapped_column(JSONText)
