"""FastAPI application entrypoint."""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db
from .api import backtests, paper

app = FastAPI(
    title="Leveraged ETF Strategy Lab",
    description="Backtesting and paper-trading simulator for a leveraged ETF strategy.",
    version="1.0.0",
)

origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins + ["*"] if os.environ.get("ALLOW_ALL_CORS") else origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(backtests.router)
app.include_router(paper.router)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "etf-lab"}


@app.get("/api/strategy-info")
def strategy_info() -> dict:
    """Plain-English description of the strategy + default params for the UI."""
    from .engine.params import StrategyParams, TICKERS

    return {
        "tickers": TICKERS,
        "defaults": StrategyParams().to_dict(),
        "description": (
            "Two equal sleeves. The TQQQ sleeve holds TQQQ when its trend is "
            "healthy, otherwise it goes defensive (GLD + SVXY). The SOXL sleeve "
            "holds SOXL when semiconductors and the Nasdaq are trending up, "
            "otherwise it holds GLD. All risk is then de-levered and combined "
            "with a fixed cash buffer."
        ),
    }
