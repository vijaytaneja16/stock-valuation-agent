"""Client for Finnhub -- covers what FMP's free tier doesn't:
analyst estimates, price targets, insider trades, earnings surprise history.
Docs: https://finnhub.io/docs/api
"""
from __future__ import annotations

import os

import requests

from stock_agent.data.cache import cached_fetch

BASE_URL = "https://finnhub.io/api/v1"


class FinnhubClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ["FINNHUB_API_KEY"]

    def _get(self, path: str, params: dict | None = None):
        params = dict(params or {})
        params["token"] = self.api_key
        resp = requests.get(f"{BASE_URL}/{path}", params=params, timeout=20)
        resp.raise_for_status()
        return resp.json()

    def get_recommendation_trends(self, ticker: str):
        """Buy/hold/sell counts over recent months."""
        return cached_fetch(
            ticker, "recommendation_trends", "current",
            lambda: self._get("stock/recommendation", {"symbol": ticker}),
        )

    def get_price_target(self, ticker: str):
        """Average/high/low analyst price targets."""
        return cached_fetch(
            ticker, "price_target", "current",
            lambda: self._get("stock/price-target", {"symbol": ticker}),
        )

    def get_earnings_surprises(self, ticker: str, limit: int = 8):
        """Historical EPS actual vs. estimate -- beat/miss track record."""
        return cached_fetch(
            ticker, "earnings_surprises", "current",
            lambda: self._get("stock/earnings", {"symbol": ticker, "limit": limit}),
        )

    def get_insider_transactions(self, ticker: str):
        """Insider buys/sells with price -- free tier covers recent history."""
        return cached_fetch(
            ticker, "insider_transactions", "current",
            lambda: self._get("stock/insider-transactions", {"symbol": ticker}),
        )

    def get_company_news(self, ticker: str, from_date: str, to_date: str):
        """from_date/to_date as 'YYYY-MM-DD'. Useful for recent-event callouts."""
        return cached_fetch(
            ticker, "company_news", f"{from_date}_{to_date}",
            lambda: self._get("company-news", {"symbol": ticker, "from": from_date, "to": to_date}),
        )
