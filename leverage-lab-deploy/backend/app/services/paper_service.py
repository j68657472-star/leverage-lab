"""Paper (simulated) trading.

A paper portfolio is updated on demand. Each update:
  1. Loads fresh daily close data (signals use DAILY CLOSE only).
  2. Computes the latest signal & target weights from the most recent
     *completed* trading day (no lookahead — same engine as backtest).
  3. Marks the portfolio to the latest available price (intraday/latest may be
     used ONLY to estimate current value, never to change the signal).
  4. If target weights differ from current weights, generates simulated trades.
  5. Stores trades, holdings snapshot, and a portfolio snapshot.

This is SIMULATED trading — not connected to a broker.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import pandas as pd
from sqlalchemy.orm import Session

from ..data.loader import DataError, get_prices
from ..engine.params import TICKERS, TRADABLE_ASSETS, StrategyParams
from ..engine.signals import compute_signal_frame
from .. import models


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def create_portfolio(
    db: Session, anon_id: str, name: str | None, initial_capital: float, params: dict
) -> models.PaperPortfolio:
    p = models.PaperPortfolio(
        portfolio_id=new_id("paper"),
        anonymous_user_id=anon_id,
        name=name or f"Paper portfolio {datetime.utcnow():%Y-%m-%d}",
        initial_capital=initial_capital,
        current_value=initial_capital,
        cash=initial_capital,
        params_json=StrategyParams.from_dict(params).to_dict(),
        status="active",
        holdings_json={t: 0.0 for t in TRADABLE_ASSETS},
        last_updated_at=datetime.utcnow(),
    )
    db.add(p)
    db.commit()
    return p


def update_portfolio(db: Session, portfolio: models.PaperPortfolio) -> dict:
    """Run one simulated update step. Returns a summary of what changed."""
    params = StrategyParams.from_dict(portfolio.params_json)

    prices = get_prices(TICKERS)  # may raise DataError
    sig = compute_signal_frame(prices, params)
    ready = sig[sig["ready"]]
    if len(ready) == 0:
        raise DataError("Not enough history to compute a signal yet.")

    latest = ready.iloc[-1]
    latest_date = ready.index[-1]

    # Latest available price per asset (used for valuation + execution price).
    px = {t: float(prices[t]["close"].reindex(ready.index).iloc[-1]) for t in TRADABLE_ASSETS}

    shares = dict(portfolio.holdings_json or {t: 0.0 for t in TRADABLE_ASSETS})
    shares = {t: float(shares.get(t, 0.0)) for t in TRADABLE_ASSETS}
    cash = float(portfolio.cash)

    holdings_value = sum(shares[t] * px[t] for t in TRADABLE_ASSETS)
    pv_before = cash + holdings_value

    targets = {
        "TQQQ": float(latest["target_weight_tqqq"]),
        "SOXL": float(latest["target_weight_soxl"]),
        "GLD": float(latest["target_weight_gld"]),
        "SVXY": float(latest["target_weight_svxy"]),
    }
    cash_target = float(latest["target_weight_cash"])

    tcost_rate = params.transaction_cost_bps / 10000.0
    new_trades: list[dict] = []

    old_weights = {t: (shares[t] * px[t] / pv_before if pv_before > 0 else 0.0) for t in TRADABLE_ASSETS}

    for t in TRADABLE_ASSETS:
        tgt_value = targets[t] * pv_before
        tgt_shares = tgt_value / px[t] if px[t] > 0 else 0.0
        if not params.allow_fractional_shares:
            tgt_shares = float(int(tgt_shares))
        delta = tgt_shares - shares[t]
        if abs(delta) * px[t] < 1.0:  # ignore sub-$1 drift
            continue
        action = "BUY" if delta > 0 else "SELL"
        notional = abs(delta) * px[t]
        tc = notional * tcost_rate
        cash_before = cash
        cash -= delta * px[t]
        cash -= tc
        shares[t] = tgt_shares
        pv_after = cash + sum(shares[a] * px[a] for a in TRADABLE_ASSETS)
        new_w = shares[t] * px[t] / pv_after if pv_after > 0 else 0.0
        trade = models.PaperTrade(
            portfolio_id=portfolio.portfolio_id,
            date=str(latest_date.date()),
            ticker=t,
            action=action,
            price=round(px[t], 6),
            shares=round(abs(delta), 6),
            notional=round(notional, 2),
            transaction_cost=round(tc, 4),
            old_weight=round(old_weights[t], 6),
            new_weight=round(new_w, 6),
            target_weight=round(targets[t], 6),
            actual_weight=round(new_w, 6),
            portfolio_value_before=round(pv_before, 2),
            portfolio_value_after=round(pv_after, 2),
            cash_before=round(cash_before, 2),
            cash_after=round(cash, 2),
            signal_reason=str(latest["signal_reason"]),
            technical_details_json={
                "qqq_rsi": float(latest["qqq_rsi"]),
                "execution_note": "Simulated fill at latest daily close.",
            },
        )
        db.add(trade)
        new_trades.append({"ticker": t, "action": action, "shares": round(abs(delta), 4)})

    pv = cash + sum(shares[t] * px[t] for t in TRADABLE_ASSETS)
    actual_weights = {t: (shares[t] * px[t] / pv if pv > 0 else 0.0) for t in TRADABLE_ASSETS}
    actual_weights["CASH"] = cash / pv if pv > 0 else 0.0

    # Daily return vs last snapshot.
    last_snap = (
        db.query(models.PaperSnapshot)
        .filter_by(portfolio_id=portfolio.portfolio_id)
        .order_by(models.PaperSnapshot.id.desc())
        .first()
    )
    prev_val = last_snap.portfolio_value if last_snap else portfolio.initial_capital
    daily_return = (pv / prev_val - 1.0) if prev_val else 0.0

    snap = models.PaperSnapshot(
        portfolio_id=portfolio.portfolio_id,
        date=str(latest_date.date()),
        portfolio_value=round(pv, 2),
        cash=round(cash, 2),
        daily_return=daily_return,
        drawdown=0.0,
        target_weights_json={**targets, "CASH": cash_target},
        actual_weights_json=actual_weights,
        signal_json={
            "tqqq_signal": bool(latest["tqqq_signal"]),
            "soxl_signal": bool(latest["soxl_signal"]),
            "qqq_rsi": float(latest["qqq_rsi"]),
            "signal_reason": str(latest["signal_reason"]),
        },
    )
    db.add(snap)

    portfolio.holdings_json = shares
    portfolio.cash = cash
    portfolio.current_value = pv
    portfolio.last_updated_at = datetime.utcnow()
    db.commit()

    return {
        "as_of": str(latest_date.date()),
        "portfolio_value": round(pv, 2),
        "cash": round(cash, 2),
        "trades": new_trades,
        "target_weights": {**targets, "CASH": cash_target},
        "actual_weights": actual_weights,
        "signal_reason": str(latest["signal_reason"]),
    }
