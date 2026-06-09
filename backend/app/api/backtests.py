"""Backtest API routes."""
from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..data.loader import DataError
from ..db import get_db
from .. import models, schemas
from ..services import backtest_service as svc

router = APIRouter(prefix="/api/backtests", tags=["backtests"])


def _summary_from_run(run: models.BacktestRun, db: Session) -> schemas.RunSummary:
    metrics = {m.period_name: m for m in run.metrics}
    full = metrics.get("full")
    return schemas.RunSummary(
        run_id=run.run_id,
        run_name=run.run_name,
        created_at=run.created_at.isoformat(),
        start_date=run.start_date,
        end_date=run.end_date,
        initial_capital=run.initial_capital,
        status=run.status,
        error_message=run.error_message,
        cagr=full.cagr if full else None,
        sharpe=full.sharpe if full else None,
        max_drawdown=full.max_drawdown if full else None,
        total_return=full.total_return if full else None,
        in_sample_cagr=metrics["in_sample"].cagr if "in_sample" in metrics else None,
        out_of_sample_cagr=metrics["out_of_sample"].cagr if "out_of_sample" in metrics else None,
        spy_cagr=full.spy_cagr if full else None,
        final_value=full.final_value if full else None,
    )


@router.post("/run", response_model=schemas.RunDetail)
def run_backtest(req: schemas.RunBacktestRequest, db: Session = Depends(get_db)):
    try:
        run = svc.run_and_store(
            db,
            anon_id=req.anonymous_user_id,
            run_name=req.run_name,
            initial_capital=req.initial_capital,
            start_date=req.start_date,
            end_date=req.end_date,
            in_sample_ratio=req.in_sample_ratio,
            params_dict=req.params.model_dump(),
        )
    except DataError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _detail_from_run(run)


def _detail_from_run(run: models.BacktestRun) -> schemas.RunDetail:
    s = _summary_from_run(run, None)  # type: ignore[arg-type]
    metrics = [
        schemas.MetricsOut(
            period_name=m.period_name,
            cagr=m.cagr, sharpe=m.sharpe, max_drawdown=m.max_drawdown,
            total_return=m.total_return, volatility=m.volatility, win_rate=m.win_rate,
            best_day=m.best_day, worst_day=m.worst_day, number_of_trades=m.number_of_trades,
            turnover=m.turnover, avg_exposure=m.avg_exposure, avg_cash_pct=m.avg_cash_pct,
            final_value=m.final_value, spy_cagr=m.spy_cagr, spy_total_return=m.spy_total_return,
            spy_max_drawdown=m.spy_max_drawdown,
        )
        for m in sorted(run.metrics, key=lambda x: x.period_name)
    ]
    return schemas.RunDetail(
        **s.model_dump(),
        in_sample_ratio=run.in_sample_ratio,
        out_of_sample_ratio=run.out_of_sample_ratio,
        params=run.params_json,
        metrics=metrics,
    )


@router.get("", response_model=list[schemas.RunSummary])
def list_runs(anonymous_user_id: str = Query(...), db: Session = Depends(get_db)):
    runs = (
        db.query(models.BacktestRun)
        .filter_by(anonymous_user_id=anonymous_user_id)
        .order_by(models.BacktestRun.created_at.desc())
        .all()
    )
    return [_summary_from_run(r, db) for r in runs]


def _get_run_or_404(db: Session, run_id: str) -> models.BacktestRun:
    run = db.query(models.BacktestRun).filter_by(run_id=run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Backtest not found.")
    return run


@router.get("/{run_id}", response_model=schemas.RunDetail)
def get_run(run_id: str, db: Session = Depends(get_db)):
    return _detail_from_run(_get_run_or_404(db, run_id))


@router.get("/{run_id}/metrics", response_model=list[schemas.MetricsOut])
def get_metrics(run_id: str, db: Session = Depends(get_db)):
    return _detail_from_run(_get_run_or_404(db, run_id)).metrics


@router.get("/{run_id}/equity")
def get_equity(run_id: str, db: Session = Depends(get_db)):
    _get_run_or_404(db, run_id)
    rows = (
        db.query(models.DailyPortfolioValue)
        .filter_by(run_id=run_id)
        .order_by(models.DailyPortfolioValue.date)
        .all()
    )
    return [
        {"date": r.date, "portfolio_value": r.portfolio_value, "spy_value": r.spy_value,
         "daily_return": r.daily_return}
        for r in rows
    ]


@router.get("/{run_id}/drawdown")
def get_drawdown(run_id: str, db: Session = Depends(get_db)):
    _get_run_or_404(db, run_id)
    rows = (
        db.query(models.DailyPortfolioValue)
        .filter_by(run_id=run_id)
        .order_by(models.DailyPortfolioValue.date)
        .all()
    )
    return [{"date": r.date, "drawdown": r.drawdown, "spy_drawdown": r.spy_drawdown} for r in rows]


@router.get("/{run_id}/trades")
def get_trades(
    run_id: str,
    ticker: str | None = None,
    action: str | None = None,
    start: str | None = None,
    end: str | None = None,
    db: Session = Depends(get_db),
):
    _get_run_or_404(db, run_id)
    q = db.query(models.TradeRecordRow).filter_by(run_id=run_id)
    if ticker:
        q = q.filter(models.TradeRecordRow.ticker == ticker.upper())
    if action:
        q = q.filter(models.TradeRecordRow.action == action.upper())
    if start:
        q = q.filter(models.TradeRecordRow.date >= start)
    if end:
        q = q.filter(models.TradeRecordRow.date <= end)
    rows = q.order_by(models.TradeRecordRow.date, models.TradeRecordRow.id).all()
    return [_trade_dict(t) for t in rows]


def _trade_dict(t: models.TradeRecordRow) -> dict:
    return {
        "date": t.date, "ticker": t.ticker, "action": t.action, "price": t.price,
        "shares": t.shares, "notional": t.notional, "transaction_cost": t.transaction_cost,
        "old_weight": t.old_weight, "new_weight": t.new_weight, "target_weight": t.target_weight,
        "actual_weight": t.actual_weight, "portfolio_value_before": t.portfolio_value_before,
        "portfolio_value_after": t.portfolio_value_after, "cash_before": t.cash_before,
        "cash_after": t.cash_after, "signal_reason": t.signal_reason,
        "tqqq_signal": t.tqqq_signal, "soxl_signal": t.soxl_signal, "qqq_rsi": t.qqq_rsi,
        "qqq_spy_signal": t.qqq_spy_signal, "obv_sma20_signal": t.obv_sma20_signal,
        "obv_sma50_signal": t.obv_sma50_signal, "smh_momentum_signal": t.smh_momentum_signal,
        "qqq_sma_slope_signal": t.qqq_sma_slope_signal,
        "technical_details": t.technical_details_json,
    }


@router.get("/{run_id}/holdings")
def get_holdings(
    run_id: str,
    ticker: str | None = None,
    date: str | None = None,
    db: Session = Depends(get_db),
):
    _get_run_or_404(db, run_id)
    q = db.query(models.DailyHolding).filter_by(run_id=run_id)
    if ticker:
        q = q.filter(models.DailyHolding.ticker == ticker.upper())
    if date:
        q = q.filter(models.DailyHolding.date == date)
    rows = q.order_by(models.DailyHolding.date, models.DailyHolding.ticker).all()
    return [
        {"date": r.date, "ticker": r.ticker, "shares": r.shares, "close_price": r.close_price,
         "market_value": r.market_value, "target_weight": r.target_weight,
         "actual_weight": r.actual_weight, "cash": r.cash, "portfolio_value": r.portfolio_value,
         "daily_return": r.daily_return, "drawdown": r.drawdown}
        for r in rows
    ]


@router.get("/{run_id}/signals")
def get_signals(run_id: str, db: Session = Depends(get_db)):
    _get_run_or_404(db, run_id)
    rows = (
        db.query(models.StrategySignal)
        .filter_by(run_id=run_id)
        .order_by(models.StrategySignal.date)
        .all()
    )
    return [
        {
            "date": r.date, "tqqq_signal": r.tqqq_signal, "soxl_signal": r.soxl_signal,
            "qqq_rsi": r.qqq_rsi, "qqq_leading_spy": r.qqq_leading_spy,
            "obv_above_sma20": r.obv_above_sma20, "obv_above_sma50": r.obv_above_sma50,
            "smh_momentum_positive": r.smh_momentum_positive,
            "qqq_sma_slope_positive": r.qqq_sma_slope_positive,
            "target_weight_tqqq": r.target_weight_tqqq, "target_weight_soxl": r.target_weight_soxl,
            "target_weight_gld": r.target_weight_gld, "target_weight_svxy": r.target_weight_svxy,
            "target_weight_cash": r.target_weight_cash, "signal_reason": r.signal_reason,
        }
        for r in rows
    ]


@router.post("/{run_id}/duplicate", response_model=schemas.RunDetail)
def duplicate_run(run_id: str, db: Session = Depends(get_db)):
    run = _get_run_or_404(db, run_id)
    try:
        new = svc.run_and_store(
            db, anon_id=run.anonymous_user_id, run_name=f"{run.run_name} (copy)",
            initial_capital=run.initial_capital, start_date=run.start_date or None,
            end_date=run.end_date or None, in_sample_ratio=run.in_sample_ratio,
            params_dict=run.params_json,
        )
    except DataError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return _detail_from_run(new)


@router.patch("/{run_id}/rename", response_model=schemas.RunSummary)
def rename_run(run_id: str, req: schemas.RenameRequest, db: Session = Depends(get_db)):
    run = _get_run_or_404(db, run_id)
    run.run_name = req.run_name
    db.commit()
    return _summary_from_run(run, db)


@router.delete("/{run_id}")
def delete_run(run_id: str, db: Session = Depends(get_db)):
    run = _get_run_or_404(db, run_id)
    db.delete(run)
    db.commit()
    return {"ok": True}


def _csv_response(rows: list[dict], filename: str) -> StreamingResponse:
    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{run_id}/export/trades.csv")
def export_trades(run_id: str, db: Session = Depends(get_db)):
    _get_run_or_404(db, run_id)
    rows = db.query(models.TradeRecordRow).filter_by(run_id=run_id).order_by(models.TradeRecordRow.date).all()
    data = [{k: v for k, v in _trade_dict(t).items() if k != "technical_details"} for t in rows]
    return _csv_response(data, f"{run_id}_trades.csv")


@router.get("/{run_id}/export/holdings.csv")
def export_holdings(run_id: str, db: Session = Depends(get_db)):
    rows = get_holdings(run_id, db=db)
    return _csv_response(rows, f"{run_id}_holdings.csv")


@router.get("/{run_id}/export/signals.csv")
def export_signals(run_id: str, db: Session = Depends(get_db)):
    rows = get_signals(run_id, db=db)
    return _csv_response(rows, f"{run_id}_signals.csv")


@router.post("/compare")
def compare(req: schemas.CompareRequest, db: Session = Depends(get_db)):
    out = []
    for rid in req.run_ids:
        run = db.query(models.BacktestRun).filter_by(run_id=rid).first()
        if run is None:
            continue
        equity = get_equity(rid, db=db)
        out.append({
            "run_id": rid,
            "run_name": run.run_name,
            "params": run.params_json,
            "summary": _summary_from_run(run, db).model_dump(),
            "equity": equity,
        })
    if len(out) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 valid runs to compare.")
    return {"runs": out}
