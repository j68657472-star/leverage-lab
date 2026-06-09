"""Paper (simulated) trading API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..data.loader import DataError
from ..db import get_db
from .. import models, schemas
from ..services import paper_service as svc

router = APIRouter(prefix="/api/paper-portfolios", tags=["paper"])


def _portfolio_dict(p: models.PaperPortfolio) -> dict:
    return {
        "portfolio_id": p.portfolio_id,
        "name": p.name,
        "created_at": p.created_at.isoformat(),
        "initial_capital": p.initial_capital,
        "current_value": p.current_value,
        "cash": p.cash,
        "params": p.params_json,
        "status": p.status,
        "last_updated_at": p.last_updated_at.isoformat() if p.last_updated_at else None,
        "holdings": p.holdings_json,
    }


@router.post("")
def create_portfolio(req: schemas.CreatePaperRequest, db: Session = Depends(get_db)):
    from ..services.backtest_service import ensure_user

    ensure_user(db, req.anonymous_user_id)
    p = svc.create_portfolio(
        db, req.anonymous_user_id, req.name, req.initial_capital, req.params.model_dump()
    )
    return _portfolio_dict(p)


@router.get("")
def list_portfolios(anonymous_user_id: str = Query(...), db: Session = Depends(get_db)):
    rows = (
        db.query(models.PaperPortfolio)
        .filter_by(anonymous_user_id=anonymous_user_id)
        .order_by(models.PaperPortfolio.created_at.desc())
        .all()
    )
    return [_portfolio_dict(p) for p in rows]


def _get_or_404(db: Session, pid: str) -> models.PaperPortfolio:
    p = db.query(models.PaperPortfolio).filter_by(portfolio_id=pid).first()
    if p is None:
        raise HTTPException(status_code=404, detail="Paper portfolio not found.")
    return p


@router.get("/{portfolio_id}")
def get_portfolio(portfolio_id: str, db: Session = Depends(get_db)):
    return _portfolio_dict(_get_or_404(db, portfolio_id))


@router.post("/{portfolio_id}/update")
def update_portfolio(portfolio_id: str, db: Session = Depends(get_db)):
    p = _get_or_404(db, portfolio_id)
    try:
        result = svc.update_portfolio(db, p)
    except DataError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return result


@router.get("/{portfolio_id}/trades")
def get_trades(portfolio_id: str, db: Session = Depends(get_db)):
    _get_or_404(db, portfolio_id)
    rows = (
        db.query(models.PaperTrade)
        .filter_by(portfolio_id=portfolio_id)
        .order_by(models.PaperTrade.date, models.PaperTrade.id)
        .all()
    )
    return [
        {
            "date": t.date, "ticker": t.ticker, "action": t.action, "price": t.price,
            "shares": t.shares, "notional": t.notional, "transaction_cost": t.transaction_cost,
            "target_weight": t.target_weight, "actual_weight": t.actual_weight,
            "portfolio_value_before": t.portfolio_value_before,
            "portfolio_value_after": t.portfolio_value_after,
            "signal_reason": t.signal_reason, "technical_details": t.technical_details_json,
        }
        for t in rows
    ]


@router.get("/{portfolio_id}/holdings")
def get_holdings(portfolio_id: str, db: Session = Depends(get_db)):
    p = _get_or_404(db, portfolio_id)
    snap = (
        db.query(models.PaperSnapshot)
        .filter_by(portfolio_id=portfolio_id)
        .order_by(models.PaperSnapshot.id.desc())
        .first()
    )
    return {
        "holdings": p.holdings_json,
        "cash": p.cash,
        "current_value": p.current_value,
        "latest_target_weights": snap.target_weights_json if snap else None,
        "latest_actual_weights": snap.actual_weights_json if snap else None,
        "latest_signal": snap.signal_json if snap else None,
    }


@router.get("/{portfolio_id}/snapshots")
def get_snapshots(portfolio_id: str, db: Session = Depends(get_db)):
    _get_or_404(db, portfolio_id)
    rows = (
        db.query(models.PaperSnapshot)
        .filter_by(portfolio_id=portfolio_id)
        .order_by(models.PaperSnapshot.date)
        .all()
    )
    return [
        {
            "date": s.date, "portfolio_value": s.portfolio_value, "cash": s.cash,
            "daily_return": s.daily_return, "target_weights": s.target_weights_json,
            "actual_weights": s.actual_weights_json, "signal": s.signal_json,
        }
        for s in rows
    ]


@router.delete("/{portfolio_id}")
def delete_portfolio(portfolio_id: str, db: Session = Depends(get_db)):
    p = _get_or_404(db, portfolio_id)
    db.delete(p)
    db.commit()
    return {"ok": True}
