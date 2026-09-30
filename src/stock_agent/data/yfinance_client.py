"""Fallback client using yfinance (no API key, but unofficial -- Yahoo can
change its page structure and break this library without notice). Use only
when FMP/Finnhub are rate-limited or missing a field.
"""
from __future__ import annotations

import yfinance as yf

from stock_agent.data.cache import cached_fetch


def _dataframe_to_json_safe_dict(df) -> dict:
    """yfinance's financial-statement DataFrames use pandas.Timestamp
    objects as column headers (one column per period-end date). JSON
    requires dict keys to be str/int/float/bool/None -- Timestamp isn't
    allowed, and json.dump's default=str handler (set in cache.py) only
    rescues non-serializable VALUES, not keys, so this has to be handled
    explicitly before the dict ever reaches json.dump.
    """
    if df is None:
        return {}
    df = df.copy()
    df.columns = [str(c) for c in df.columns]
    return df.to_dict()


class YFinanceClient:
    def get_income_statement(self, ticker: str, period: str = "annual"):
        def fetch():
            t = yf.Ticker(ticker)
            df = t.financials if period == "annual" else t.quarterly_financials
            return _dataframe_to_json_safe_dict(df)
        return cached_fetch(ticker, "yf_income_statement", period, fetch)

    def get_balance_sheet(self, ticker: str, period: str = "annual"):
        def fetch():
            t = yf.Ticker(ticker)
            df = t.balance_sheet if period == "annual" else t.quarterly_balance_sheet
            return _dataframe_to_json_safe_dict(df)
        return cached_fetch(ticker, "yf_balance_sheet", period, fetch)

    def get_cash_flow(self, ticker: str, period: str = "annual"):
        def fetch():
            t = yf.Ticker(ticker)
            df = t.cashflow if period == "annual" else t.quarterly_cashflow
            return _dataframe_to_json_safe_dict(df)
        return cached_fetch(ticker, "yf_cash_flow", period, fetch)

    def get_quote(self, ticker: str):
        def fetch():
            t = yf.Ticker(ticker)
            info = t.info
            return {
                "price": info.get("currentPrice"),
                "marketCap": info.get("marketCap"),
                "sharesOutstanding": info.get("sharesOutstanding"),
            }
        return cached_fetch(ticker, "yf_quote", "current", fetch)

    def get_analyst_recommendations(self, ticker: str):
        def fetch():
            t = yf.Ticker(ticker)
            return _dataframe_to_json_safe_dict(t.recommendations)
        return cached_fetch(ticker, "yf_recommendations", "current", fetch)
