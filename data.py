"""
Data fetching helpers built on top of yfinance.
"""

from __future__ import annotations

import pandas as pd
import yfinance as yf


def fetch_data(symbol: str, period: str) -> pd.DataFrame:
    """
    Download daily OHLCV data for a given symbol and period.

    Parameters
    ----------
    symbol:
        Ticker symbol understood by yfinance.
    period:
        Lookback window, e.g. '3mo', '6mo', '1y', '2y'.
    """
    data = yf.download(symbol, period=period, interval="1d", progress=False)
    # Ensure we always work with clean data
    return data.dropna()


def get_latest_close(symbol: str) -> float:
    """
    Convenience helper to fetch the latest close price for a symbol.
    """
    data = fetch_data(symbol, "5d")
    last_close = data["Close"].iloc[-1]

    # yfinance can sometimes return a DataFrame with multiple columns
    # (e.g. multi-index columns) even for a single symbol. In that case
    # .iloc[-1] is a Series; take the first value.
    if isinstance(last_close, pd.Series):
        last_close = last_close.iloc[0]

    return float(last_close)

