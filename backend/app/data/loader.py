"""Price data loading with on-disk caching and provider fallback.

Design goals (from the spec):
  - Rely on FREE data.
  - Cache downloads to avoid hitting the network repeatedly.
  - If the live download fails, raise a FRIENDLY error (so the API can show a
    nice message) — but the caller is responsible for keeping already-saved
    backtest runs viewable.
  - NEVER silently invent missing prices. Validation is explicit.

Providers (pluggable):
  - yfinance  (primary; works reliably here, returns adjusted OHLCV)
  - stooq     (fallback; free EOD CSV — note: may be blocked from some
               datacenter IPs behind a JS challenge, hence it is the fallback)

The strategy engine does not know or care which provider was used; it only sees
a normalized OHLCV DataFrame.
"""
from __future__ import annotations

import json
import os
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

CACHE_DIR = Path(os.environ.get("PRICE_CACHE_DIR", "/home/user/leveraged-etf-lab/backend/.price_cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Treat cache as fresh for this many hours (EOD data updates once per day).
CACHE_TTL_HOURS = float(os.environ.get("PRICE_CACHE_TTL_HOURS", "12"))

NORMALIZED_COLS = ["open", "high", "low", "close", "volume"]


class DataError(Exception):
    """Raised with a user-friendly message when data cannot be obtained."""


def _cache_path(ticker: str) -> Path:
    return CACHE_DIR / f"{ticker.upper()}.parquet"


def _meta_path(ticker: str) -> Path:
    return CACHE_DIR / f"{ticker.upper()}.meta.json"


def _is_cache_fresh(ticker: str) -> bool:
    mp = _meta_path(ticker)
    if not mp.exists() or not _cache_path(ticker).exists():
        return False
    try:
        meta = json.loads(mp.read_text())
        fetched = datetime.fromisoformat(meta["fetched_at"])
    except Exception:
        return False
    return datetime.utcnow() - fetched < timedelta(hours=CACHE_TTL_HOURS)


def _read_cache(ticker: str) -> pd.DataFrame | None:
    p = _cache_path(ticker)
    if not p.exists():
        return None
    try:
        df = pd.read_parquet(p)
        df.index = pd.to_datetime(df.index)
        return df
    except Exception:
        return None


def _write_cache(ticker: str, df: pd.DataFrame) -> None:
    df.to_parquet(_cache_path(ticker))
    _meta_path(ticker).write_text(
        json.dumps({"fetched_at": datetime.utcnow().isoformat(), "rows": len(df)})
    )


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------
def _fetch_yfinance(ticker: str) -> pd.DataFrame:
    import yfinance as yf

    df = yf.download(
        ticker,
        period="max",
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    if df is None or len(df) == 0:
        raise DataError(f"No data returned from Yahoo Finance for {ticker}.")
    # yfinance may return a MultiIndex column frame for single tickers.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.lower)
    df = df[["open", "high", "low", "close", "volume"]]
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df


def _fetch_stooq(ticker: str) -> pd.DataFrame:
    import pandas_datareader.data as web

    df = web.DataReader(ticker, "stooq")
    if df is None or len(df) == 0:
        raise DataError(f"No data returned from Stooq for {ticker}.")
    df = df.sort_index()
    df = df.rename(columns=str.lower)
    df = df[["open", "high", "low", "close", "volume"]]
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df


PROVIDERS = {
    "yfinance": _fetch_yfinance,
    "stooq": _fetch_stooq,
}

# Order to try. yfinance first because Stooq is JS-challenged on many server IPs.
PROVIDER_ORDER = os.environ.get("PRICE_PROVIDERS", "yfinance,stooq").split(",")


def _download(ticker: str) -> pd.DataFrame:
    errors: list[str] = []
    for name in PROVIDER_ORDER:
        fn = PROVIDERS.get(name.strip())
        if not fn:
            continue
        try:
            df = fn(ticker)
            if len(df) > 0:
                return df
        except Exception as e:  # noqa: BLE001 - we want to try the next provider
            errors.append(f"{name}: {e}")
            time.sleep(0.2)
    raise DataError(
        f"Could not download price data for {ticker}. "
        "The free data provider may be temporarily unavailable — please try "
        "again in a few minutes. (" + " | ".join(errors) + ")"
    )


def get_prices(
    tickers: list[str], force_refresh: bool = False
) -> dict[str, pd.DataFrame]:
    """Return normalized OHLCV for each ticker, using cache when fresh.

    Raises DataError (friendly) if a ticker cannot be obtained from cache or net.
    """
    out: dict[str, pd.DataFrame] = {}
    failed: list[str] = []
    for t in tickers:
        t = t.upper()
        if not force_refresh and _is_cache_fresh(t):
            cached = _read_cache(t)
            if cached is not None and len(cached):
                out[t] = cached
                continue
        try:
            df = _download(t)
            _write_cache(t, df)
            out[t] = df
        except DataError:
            cached = _read_cache(t)  # fall back to stale cache if we have it
            if cached is not None and len(cached):
                out[t] = cached
            else:
                failed.append(t)

    if failed:
        raise DataError(
            "Could not load price data for: "
            + ", ".join(failed)
            + ". Free data may be temporarily unavailable. Saved backtests are "
            "still viewable; please retry new runs shortly."
        )
    return out


def validate_prices(prices: dict[str, pd.DataFrame], required: list[str]) -> None:
    """Explicitly validate completeness — never silently use missing prices."""
    for t in required:
        if t not in prices:
            raise DataError(f"Missing price data for required ticker {t}.")
        df = prices[t]
        if df[NORMALIZED_COLS].isna().all().any():
            raise DataError(f"Price data for {t} has empty columns.")
