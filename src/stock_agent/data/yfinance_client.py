"""Fallback client using yfinance (no API key, but unofficial -- Yahoo can
change its page structure and break this library without notice). Use only
when FMP/Finnhub are rate-limited or missing a field.
"""
from __future__ import annotations

import yfinance as yf

from stock_agent.data.cache import cached_fetch


class YFinanceClient:
    def get_income_statement(self, ticker: str, period: str = "annual"):
        def fetch():
            t = yf.Ticker(ticker)
            df = t.financials if period == "annual" else t.quarterly_financials
            return df.to_dict()
        return cached_fetch(ticker, "yf_income_statement", period, fetch)

    def get_balance_sheet(self, ticker: str, period: str = "annual"):
        def fetch():
            t = yf.Ticker(ticker)
            df = t.balance_sheet if period == "annual" else t.quarterly_balance_sheet
            return df.to_dict()
        return cached_fetch(ticker, "yf_balance_sheet", period, fetch)

    def get_cash_flow(self, ticker: str, period: str = "annual"):
        def fetch():
            t = yf.Ticker(ticker)
            df = t.cashflow if period == "annual" else t.quarterly_cashflow
            return df.to_dict()
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
            df = t.recommendations
            return df.to_dict() if df is not None else {}
        return cached_fetch(ticker, "yf_recommendations", "current", fetch)
