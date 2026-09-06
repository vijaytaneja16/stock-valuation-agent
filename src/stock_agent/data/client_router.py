"""Single entry point for all data fetching. Tries the best free source
first for each dataset, falls back on rate-limit/error, and normalizes
just enough to hand consistent shapes to the valuation engine.
"""
from __future__ import annotations

import logging

from stock_agent.data.fmp_client import FMPClient, FMPRateLimitError
from stock_agent.data.finnhub_client import FinnhubAccessError, FinnhubClient
from stock_agent.data.alphavantage_client import AlphaVantageClient
from stock_agent.data.yfinance_client import YFinanceClient
from stock_agent.data.edgar_client import EdgarClient

logger = logging.getLogger(__name__)


class DataRouter:
    def __init__(self):
        self.fmp = FMPClient()
        self.finnhub = FinnhubClient()
        self.alphavantage = AlphaVantageClient()
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

    # --- Analyst / market data ---
    #
    # price_target cascades FMP -> Alpha Vantage -> Finnhub (see
    # get_price_target below). recommendation_trends, earnings surprises,
    # and insider activity are Finnhub-only for now since FMP's free tier
    # doesn't cover them -- each degrades to None on a FinnhubAccessError
    # (403 -- endpoint requires a paid plan) rather than crashing the whole
    # call. Finnhub has moved individual endpoints behind premium access
    # before with no advance notice, so treat any of these as liable to
    # need this same protection in the future.

    def _finnhub_field_or_none(self, label: str, ticker: str, fetch_fn):
        try:
            return fetch_fn()
        except FinnhubAccessError as e:
            logger.warning(f"Finnhub '{label}' unavailable for {ticker} (likely premium-only): {e}")
            return None

    def get_price_target(self, ticker: str):
        """Analyst price targets. FMP's price-target-consensus (high/low/
        median/consensus) is primary -- confirmed working on the free tier.
        Falls back to Alpha Vantage's OVERVIEW endpoint (a single mean
        target only, no high/low/median) if FMP fails, then to Finnhub
        (currently premium-gated, but harmless to try -- costs nothing on
        top of the two calls above and covers the case where Finnhub
        reopens this endpoint in the future).
        """
        try:
            data = self.fmp.get_price_target_consensus(ticker)
            return {"source": "fmp", "data": data}
        except Exception as e:
            logger.warning(f"FMP price target failed for {ticker} ({e}); trying Alpha Vantage")

        try:
            overview = self.alphavantage.get_company_overview(ticker)
            target = overview.get("AnalystTargetPrice")
            if target not in (None, "None", "-"):
                return {"source": "alphavantage", "data": {"mean_target": float(target)}}
        except Exception as e:
            logger.warning(f"Alpha Vantage price target failed for {ticker} ({e}); trying Finnhub")

        finnhub_result = self._finnhub_field_or_none(
            "price_target", ticker, lambda: self.finnhub.get_price_target(ticker)
        )
        if finnhub_result is not None:
            return {"source": "finnhub", "data": finnhub_result}

        return None

    def get_analyst_estimates(self, ticker: str):
        return {
            "price_target": self.get_price_target(ticker),
            "recommendation_trends": self._finnhub_field_or_none(
                "recommendation_trends", ticker, lambda: self.finnhub.get_recommendation_trends(ticker)
            ),
        }

    def get_earnings_track_record(self, ticker: str):
        return self._finnhub_field_or_none(
            "earnings_surprises", ticker, lambda: self.finnhub.get_earnings_surprises(ticker)
        )

    def get_insider_activity(self, ticker: str):
        return self._finnhub_field_or_none(
            "insider_transactions", ticker, lambda: self.finnhub.get_insider_transactions(ticker)
        )

    # --- Qualitative (EDGAR) ---

    def get_recent_filings(self, ticker: str):
        return self.edgar.get_filings_list(ticker)

    def search_filing_text(self, query: str, ticker: str, forms: str | None = None):
        return self.edgar.full_text_search(query, ticker=ticker, forms=forms)
