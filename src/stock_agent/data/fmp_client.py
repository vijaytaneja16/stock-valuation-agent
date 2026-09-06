"""Client for Financial Modeling Prep (FMP).

Free tier: 250 requests/day, 5 years of annual statements for US companies.
Docs: https://site.financialmodelingprep.com/developer/docs

NOTE: FMP migrated from the legacy /api/v3/ endpoints (ticker in the URL
path, e.g. /api/v3/income-statement/AAPL) to a new /stable/ API (ticker as
a `symbol` query parameter, e.g. /stable/income-statement?symbol=AAPL).
The old /api/v3/ endpoints now return 403 "Legacy Endpoint" errors. This
client targets /stable/ throughout.
"""
from __future__ import annotations

import os

import requests

from stock_agent.data.cache import cached_fetch

BASE_URL = "https://financialmodelingprep.com/stable"


class FMPRateLimitError(Exception):
    pass


class FMPClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ["FMP_API_KEY"]

    def _get(self, path: str, params: dict | None = None) -> dict | list:
        params = dict(params or {})
        params["apikey"] = self.api_key
        resp = requests.get(f"{BASE_URL}/{path}", params=params, timeout=20)
        if resp.status_code == 429:
            raise FMPRateLimitError(f"FMP rate limit hit on {path}")
        resp.raise_for_status()
        data = resp.json()
        # FMP returns {"Error Message": "..."} on bad tickers/plan restrictions
        if isinstance(data, dict) and "Error Message" in data:
            raise ValueError(f"FMP error for {path}: {data['Error Message']}")
        return data

    def get_income_statement(self, ticker: str, period: str = "annual", limit: int = 5):
        """period: 'annual' or 'quarter'"""
        return cached_fetch(
            ticker, "income_statement", period,
            lambda: self._get("income-statement", {"symbol": ticker, "period": period, "limit": limit}),
        )

    def get_balance_sheet(self, ticker: str, period: str = "annual", limit: int = 5):
        return cached_fetch(
            ticker, "balance_sheet", period,
            lambda: self._get("balance-sheet-statement", {"symbol": ticker, "period": period, "limit": limit}),
        )

    def get_cash_flow(self, ticker: str, period: str = "annual", limit: int = 5):
        return cached_fetch(
            ticker, "cash_flow", period,
            lambda: self._get("cash-flow-statement", {"symbol": ticker, "period": period, "limit": limit}),
        )

    def get_key_metrics(self, ticker: str, period: str = "annual", limit: int = 5):
        return cached_fetch(
            ticker, "key_metrics", period,
            lambda: self._get("key-metrics", {"symbol": ticker, "period": period, "limit": limit}),
        )

    def get_company_profile(self, ticker: str):
        return cached_fetch(
            ticker, "profile", "current",
            lambda: self._get("profile", {"symbol": ticker}),
        )

    def get_quote(self, ticker: str):
        """Current price, market cap, shares outstanding. Refreshed hourly (see cache.py)."""
        return cached_fetch(
            ticker, "quote", "current",
            lambda: self._get("quote", {"symbol": ticker}),
        )

    def get_price_target_consensus(self, ticker: str):
        """High/low/median/consensus analyst price targets. Confirmed
        working on the free tier as of this writing (unlike Finnhub's
        equivalent endpoint, which now requires a paid plan).
        """
        return cached_fetch(
            ticker, "price_target_consensus", "current",
            lambda: self._get("price-target-consensus", {"symbol": ticker}),
        )
