"""Single entry point for all data fetching. Tries the best free source
first for each dataset, falls back on rate-limit/error, and normalizes
just enough to hand consistent shapes to the valuation engine.
"""
from __future__ import annotations

import logging

from stock_agent.data.fmp_client import FMPClient, FMPRateLimitError
from stock_agent.data.finnhub_client import FinnhubClient
from stock_agent.data.yfinance_client import YFinanceClient
from stock_agent.data.edgar_client import EdgarClient

logger = logging.getLogger(__name__)


class DataRouter:
    def __init__(self):
        self.fmp = FMPClient()
        self.finnhub = FinnhubClient()
        self.yfinance = YFinanceClient()
        self.edgar = EdgarClient()

    # --- Financial statements (FMP primary, yfinance fallback) ---

    def get_income_statement(self, ticker: str, period: str = "annual", limit: int = 5):
        try:
            return self.fmp.get_income_statement(ticker, period, limit)
        except (FMPRateLimitError, Exception) as e:
            logger.warning(f"FMP income statement failed for {ticker} ({e}); falling back to yfinance")
            return self.yfinance.get_income_statement(ticker, period)

    def get_balance_sheet(self, ticker: str, period: str = "annual", limit: int = 5):
        try:
            return self.fmp.get_balance_sheet(ticker, period, limit)
        except (FMPRateLimitError, Exception) as e:
            logger.warning(f"FMP balance sheet failed for {ticker} ({e}); falling back to yfinance")
            return self.yfinance.get_balance_sheet(ticker, period)

    def get_cash_flow(self, ticker: str, period: str = "annual", limit: int = 5):
        try:
            return self.fmp.get_cash_flow(ticker, period, limit)
        except (FMPRateLimitError, Exception) as e:
            logger.warning(f"FMP cash flow failed for {ticker} ({e}); falling back to yfinance")
            return self.yfinance.get_cash_flow(ticker, period)

    def get_quote(self, ticker: str):
        try:
            return self.fmp.get_quote(ticker)
        except (FMPRateLimitError, Exception) as e:
            logger.warning(f"FMP quote failed for {ticker} ({e}); falling back to yfinance")
            return self.yfinance.get_quote(ticker)

    def get_company_profile(self, ticker: str):
        return self.fmp.get_company_profile(ticker)

    # --- Analyst / market data (Finnhub only -- FMP free tier doesn't have these) ---

    def get_analyst_estimates(self, ticker: str):
        return {
            "price_target": self.finnhub.get_price_target(ticker),
            "recommendation_trends": self.finnhub.get_recommendation_trends(ticker),
        }

    def get_earnings_track_record(self, ticker: str):
        return self.finnhub.get_earnings_surprises(ticker)

    def get_insider_activity(self, ticker: str):
        return self.finnhub.get_insider_transactions(ticker)

    # --- Qualitative (EDGAR) ---

    def get_recent_filings(self, ticker: str):
        return self.edgar.get_filings_list(ticker)

    def search_filing_text(self, query: str, ticker: str, forms: str | None = None):
        return self.edgar.full_text_search(query, ticker=ticker, forms=forms)
