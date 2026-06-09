# Leverage Lab — Leveraged ETF Strategy Backtester & Paper Trader

A polished, multi-user (no-login) web app for **backtesting** and **paper-trading
a rules-based leveraged ETF strategy** (TQQQ / SOXL / GLD / SVXY / cash), with
SPY as the benchmark.

> ⚠️ **Research tool only.** This is not investment advice, not an options app,
> and not connected to any brokerage. All trading is simulated.

---

## What it does

- **Backtest** the strategy over 5y / 10y / custom ranges with your own capital,
  transaction costs, and strategy parameters.
- **No look-ahead**: signals use data only up to each day's close; trades execute
  on the *next* trading day's close.
- **In-sample / out-of-sample** split (default 70/30), kept strictly separate.
- **Metrics**: CAGR, Sharpe, Max Drawdown, Total Return, Volatility, Win Rate,
  Best/Worst Day, Trades, Turnover, Avg Exposure, Avg Cash %, Final Value — plus
  SPY benchmark.
- **Explainable trades**: every trade has a plain-English reason and full
  technical detail (which signals fired, RSI, weights, cash before/after…).
- **Saved runs**: every backtest is saved, reopenable by URL, renamable,
  duplicatable, comparable (2–4 overlaid), deletable, and exportable to CSV.
- **Paper trading**: create a simulated portfolio, update it on demand, see
  current vs target allocation, what changed, and full simulated trade history.

---

## Architecture

```
leveraged-etf-lab/
├── backend/                 FastAPI + Python strategy engine
│   ├── app/
│   │   ├── engine/          Pure strategy logic (no I/O) — fully unit-tested
│   │   │   ├── params.py        Strategy parameters + validation
│   │   │   ├── indicators.py    RSI, OBV, SMA, momentum, slope
│   │   │   ├── signals.py       Signals + target-weight construction
│   │   │   ├── metrics.py       CAGR / Sharpe / MaxDD / etc.
│   │   │   └── backtest.py      No-lookahead portfolio simulation
│   │   ├── data/loader.py   Price download + caching + provider fallback
│   │   ├── services/        Orchestration (run + persist, paper trading)
│   │   ├── api/             FastAPI routers (backtests, paper)
│   │   ├── models.py        SQLAlchemy ORM (all spec tables)
│   │   ├── schemas.py       Typed request/response models
│   │   ├── db.py            Postgres (prod) / SQLite (zero-config dev)
│   │   └── main.py          App entrypoint
│   └── tests/               33 unit + integration tests
└── frontend/                Next.js 14 + React + TS + Tailwind + Recharts
    └── src/
        ├── app/             App-router pages (dashboard, backtest, paper, …)
        ├── components/      Shell, charts, UI primitives
        └── lib/             API client, formatting, anon-id, asset colors
```

**Separation of concerns:** the strategy engine is a pure library (no network,
no DB, deterministic) so it's trivially testable. Data loading and persistence
are isolated layers around it.

---

## Data source

Uses **free** data via a pluggable provider interface:

1. **yfinance** (primary) — reliable adjusted daily OHLCV.
2. **Stooq** (fallback) — free EOD CSV.

> Order is configurable via `PRICE_PROVIDERS`. yfinance is primary because Stooq
> is frequently behind a JavaScript challenge from datacenter/server IPs, which
> makes it unreliable in production. Downloads are **cached on disk** (default 12h
> TTL) to avoid repeated calls. If a fresh download fails, the app falls back to
> stale cache where possible and otherwise shows a friendly error — **already-saved
> backtests always remain viewable.**

---

## Run locally

### Option A — Docker Compose (Postgres + backend + frontend)

```bash
cd leveraged-etf-lab
docker compose up --build
# Frontend: http://localhost:3000
# API:      http://localhost:8000  (docs at /docs)
```

### Option B — Manual (SQLite, zero config)

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
With no `DATABASE_URL`, it creates a local `etf_lab.db` SQLite file.

**Frontend**
```bash
cd frontend
npm install
npm run dev      # http://localhost:3000
```

---

## Tests

```bash
cd backend
pytest -q        # 33 tests: indicators, signals, weights, no-lookahead,
                 # backtest, cash tracking, costs, metrics, in/out split
```

---

## Strategy (default parameters)

Two equal **sleeves**, then de-levered + cash buffer:

- **TQQQ sleeve (50%)** — hold TQQQ if its signal is true; else 25% GLD + 25% SVXY.
  - TQQQ in-market = (OBV > SMA20 **and** OBV > SMA50 **and** QQQ leads SPY)
    **or** (QQQ RSI < 30 oversold re-entry).
- **SOXL sleeve (50%)** — hold SOXL if its signal is true; else 50% GLD.
  - SOXL in-market = QQQ leads SPY **and** QQQ RSI < 75 **and** SMH momentum > 0
    **and** QQQ 150-day SMA slope rising.
- **De-lever**: multiply all risk weights by `deleverage_factor` (0.5) and add
  `fixed_cash_weight` (0.5).
  → **Default max allocation: 25% TQQQ / 25% SOXL / 50% cash.**

All parameters are editable in the UI (RSI levels, lookbacks, costs, leverage,
cash, fractional shares, …).

---

## No-lookahead guarantee

1. The signal for day **D** is computed from data **through D's close**.
2. The rebalance executes on the **next** trading day **D+1**, at D+1's close.
3. Returns are earned only after execution.

This is enforced in `engine/backtest.py` and covered by dedicated tests
(`test_no_lookahead_*`).
