"""Client for Financial Modeling Prep (FMP).

Free tier: 250 requests/day, 5 years of annual statements for US companies.
Docs: https://site.financialmodelingprep.com/developer/docs
"""
from __future__ import annotations

import os

import requests

from stock_agent.data.cache import cached_fetch

BASE_URL = "https://financialmodelingprep.com/api/v3"


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
            lambda: self._get(f"income-statement/{ticker}", {"period": period, "limit": limit}),
        )

    def get_balance_sheet(self, ticker: str, period: str = "annual", limit: int = 5):
        return cached_fetch(
            ticker, "balance_sheet", period,
            lambda: self._get(f"balance-sheet-statement/{ticker}", {"period": period, "limit": limit}),
        )

    def get_cash_flow(self, ticker: str, period: str = "annual", limit: int = 5):
        return cached_fetch(
            ticker, "cash_flow", period,
            lambda: self._get(f"cash-flow-statement/{ticker}", {"period": period, "limit": limit}),
        )

    def get_key_metrics(self, ticker: str, period: str = "annual", limit: int = 5):
        return cached_fetch(
            ticker, "key_metrics", period,
            lambda: self._get(f"key-metrics/{ticker}", {"period": period, "limit": limit}),
        )

    def get_company_profile(self, ticker: str):
        return cached_fetch(
            ticker, "profile", "current",
            lambda: self._get(f"profile/{ticker}"),
        )

    def get_quote(self, ticker: str):
        """Current price, market cap, shares outstanding. Refreshed hourly (see cache.py)."""
        return cached_fetch(
            ticker, "quote", "current",
            lambda: self._get(f"quote/{ticker}"),
        )
