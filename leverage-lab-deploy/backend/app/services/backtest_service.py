"""Orchestrates: load data -> run engine -> persist everything to the DB."""
from __future__ import annotations

import uuid
from datetime import date, datetime

import pandas as pd
from sqlalchemy.orm import Session

from ..data.loader import DataError, get_prices, validate_prices
from ..engine.backtest import BacktestResult, run_backtest
from ..engine.params import TICKERS, StrategyParams
from .. import models


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def ensure_user(db: Session, anon_id: str) -> None:
    user = db.query(models.AnonymousUser).filter_by(anonymous_user_id=anon_id).first()
    now = datetime.utcnow()
    if user is None:
        db.add(models.AnonymousUser(anonymous_user_id=anon_id, created_at=now, last_seen_at=now))
    else:
        user.last_seen_at = now
    db.commit()


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    return datetime.fromisoformat(s).date()


def run_and_store(
    db: Session,
    anon_id: str,
    run_name: str | None,
    initial_capital: float,
    start_date: str | None,
    end_date: str | None,
    in_sample_ratio: float,
    params_dict: dict,
) -> models.BacktestRun:
    """Run a backtest and persist all outputs. Returns the BacktestRun row.

    On data failure, stores a run row with status='failed' + friendly message so
    the user still sees a record, and re-raises DataError for the API to surface.
    """
    ensure_user(db, anon_id)
    params = StrategyParams.from_dict(params_dict)
    params.validate()

    rid = new_id("run")
    run = models.BacktestRun(
        run_id=rid,
        anonymous_user_id=anon_id,
        run_name=run_name or f"Backtest {datetime.utcnow():%Y-%m-%d %H:%M}",
        start_date=start_date or "",
        end_date=end_date or "",
        initial_capital=initial_capital,
        in_sample_ratio=in_sample_ratio,
        out_of_sample_ratio=round(1 - in_sample_ratio, 4),
        params_json=params.to_dict(),
        status="running",
    )
    db.add(run)
    db.commit()

    try:
        prices = get_prices(TICKERS)
        validate_prices(prices, TICKERS)
        result = run_backtest(
            prices,
            params,
            initial_capital=initial_capital,
            start=_parse_date(start_date),
            end=_parse_date(end_date),
            in_sample_ratio=in_sample_ratio,
        )
    except (DataError, ValueError) as e:
        run.status = "failed"
        run.error_message = str(e)
        db.commit()
        raise

    # Persist results.
    _persist_result(db, run, result, initial_capital)
    # Fill in actual start/end if they were blank.
    run.start_date = run.start_date or str(result.daily.index[0].date())
    run.end_date = run.end_date or str(result.daily.index[-1].date())
    run.status = "complete"
    db.commit()
    return run


def _persist_result(
    db: Session, run: models.BacktestRun, result: BacktestResult, initial_capital: float
) -> None:
    rid = run.run_id
    spy = result.spy_metrics_full

    def metric_row(period: str, m: dict) -> models.BacktestMetric:
        return models.BacktestMetric(
            run_id=rid,
            period_name=period,
            cagr=m.get("cagr", 0.0),
            sharpe=m.get("sharpe", 0.0),
            max_drawdown=m.get("max_drawdown", 0.0),
            total_return=m.get("total_return", 0.0),
            volatility=m.get("volatility", 0.0),
            win_rate=m.get("win_rate", 0.0),
            best_day=m.get("best_day", 0.0),
            worst_day=m.get("worst_day", 0.0),
            number_of_trades=int(m.get("number_of_trades", 0)),
            turnover=m.get("turnover", 0.0),
            avg_exposure=m.get("avg_exposure", 0.0),
            avg_cash_pct=m.get("avg_cash_pct", 0.0),
            final_value=m.get("final_value", 0.0),
            spy_cagr=spy["cagr"],
            spy_total_return=spy["total_return"],
            spy_max_drawdown=spy["max_drawdown"],
        )

    db.add_all([
        metric_row("full", result.metrics_full),
        metric_row("in_sample", result.metrics_in),
        metric_row("out_of_sample", result.metrics_out),
    ])

    # Daily portfolio values (bulk).
    daily = result.daily
    db.bulk_save_objects([
        models.DailyPortfolioValue(
            run_id=rid,
            date=str(idx.date()),
            portfolio_value=float(row.portfolio_value),
            cash=float(row.cash),
            daily_return=float(row.daily_return),
            drawdown=float(row.drawdown),
            spy_value=float(row.spy_value),
            spy_return=float(row.spy_return),
            spy_drawdown=float(row.spy_drawdown),
        )
        for idx, row in daily.iterrows()
    ])

    # Daily holdings (bulk).
    h = result.holdings
    db.bulk_save_objects([
        models.DailyHolding(
            run_id=rid,
            date=str(pd.Timestamp(r["date"]).date()),
            ticker=r["ticker"],
            shares=float(r["shares"]),
            close_price=float(r["close_price"]),
            market_value=float(r["market_value"]),
            target_weight=float(r["target_weight"]),
            actual_weight=float(r["actual_weight"]),
            cash=float(r["cash"]),
            portfolio_value=float(r["portfolio_value"]),
            daily_return=float(r["daily_return"]) if pd.notna(r["daily_return"]) else 0.0,
            drawdown=float(r["drawdown"]) if pd.notna(r["drawdown"]) else 0.0,
        )
        for _, r in h.iterrows()
    ])

    # Trades.
    db.bulk_save_objects([
        models.TradeRecordRow(
            run_id=rid,
            date=str(t.date),
            ticker=t.ticker,
            action=t.action,
            price=t.price,
            shares=t.shares,
            notional=t.notional,
            transaction_cost=t.transaction_cost,
            old_weight=t.old_weight,
            new_weight=t.new_weight,
            target_weight=t.target_weight,
            actual_weight=t.actual_weight,
            portfolio_value_before=t.portfolio_value_before,
            portfolio_value_after=t.portfolio_value_after,
            cash_before=t.cash_before,
            cash_after=t.cash_after,
            signal_reason=t.signal_reason,
            tqqq_signal=t.tqqq_signal,
            soxl_signal=t.soxl_signal,
            qqq_rsi=t.qqq_rsi,
            qqq_spy_signal=t.qqq_spy_signal,
            obv_sma20_signal=t.obv_sma20_signal,
            obv_sma50_signal=t.obv_sma50_signal,
            smh_momentum_signal=t.smh_momentum_signal,
            qqq_sma_slope_signal=t.qqq_sma_slope_signal,
            technical_details_json=t.technical_details,
        )
        for t in result.trades
    ])

    # Strategy signals (bulk) — only the real trading window.
    sig = result.signals
    db.bulk_save_objects([
        models.StrategySignal(
            run_id=rid,
            date=str(idx.date()),
            tqqq_signal=bool(row["tqqq_signal"]),
            soxl_signal=bool(row["soxl_signal"]),
            qqq_rsi=float(row["qqq_rsi"]),
            qqq_spy_ratio=float(row["qqq_spy_ratio"]),
            qqq_spy_ratio_sma=float(row["qqq_spy_ratio_sma"]),
            qqq_leading_spy=bool(row["qqq_leading_spy"]),
            tqqq_obv=float(row["tqqq_obv"]),
            tqqq_obv_sma20=float(row["tqqq_obv_sma20"]),
            tqqq_obv_sma50=float(row["tqqq_obv_sma50"]),
            obv_above_sma20=bool(row["obv_above_sma20"]),
            obv_above_sma50=bool(row["obv_above_sma50"]),
            smh_momentum=float(row["smh_momentum"]),
            smh_momentum_positive=bool(row["smh_momentum_positive"]),
            qqq_sma150=float(row["qqq_sma150"]),
            qqq_sma_slope_positive=bool(row["qqq_sma_slope_positive"]),
            target_weight_tqqq=float(row["target_weight_tqqq"]),
            target_weight_soxl=float(row["target_weight_soxl"]),
            target_weight_gld=float(row["target_weight_gld"]),
            target_weight_svxy=float(row["target_weight_svxy"]),
            target_weight_cash=float(row["target_weight_cash"]),
            signal_reason=str(row["signal_reason"]),
        )
        for idx, row in sig.iterrows()
    ])

    db.commit()
