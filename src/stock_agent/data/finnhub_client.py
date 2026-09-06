"""Client for Finnhub -- covers what FMP's free tier doesn't:
analyst estimates, price targets, insider trades, earnings surprise history.
Docs: https://finnhub.io/docs/api

NOTE: Finnhub has a track record of moving individual endpoints behind
premium access over time (their own docs currently mark price-target as
"Premium: Premium required", for example). A 403 here means "this endpoint
needs a paid plan," not "your key is invalid" -- FinnhubAccessError is
raised distinctly from other HTTP errors so callers (see client_router.py)
can catch it specifically and degrade gracefully instead of crashing the
whole request.
"""
from __future__ import annotations

import os

import requests

from stock_agent.data.cache import cached_fetch

BASE_URL = "https://finnhub.io/api/v1"


class FinnhubAccessError(Exception):
    """Raised on a 403 -- almost always means this endpoint requires a
    Finnhub plan above the free tier, not that the API key itself is bad.
    """
    pass


class FinnhubClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ["FINNHUB_API_KEY"]

    def _get(self, path: str, params: dict | None = None):
        params = dict(params or {})
        params["token"] = self.api_key
        resp = requests.get(f"{BASE_URL}/{path}", params=params, timeout=20)
        if resp.status_code == 403:
            raise FinnhubAccessError(
                f"Finnhub returned 403 for '{path}' -- this endpoint likely "
                "requires a paid Finnhub plan (not necessarily a bad API key). "
                f"Response: {resp.text[:200]}"
            )
        resp.raise_for_status()
        return resp.json()

    def get_recommendation_trends(self, ticker: str):
        """Buy/hold/sell counts over recent months."""
        return cached_fetch(
            ticker, "recommendation_trends", "current",
            lambda: self._get("stock/recommendation", {"symbol": ticker}),
        )

    def get_price_target(self, ticker: str):
        """Average/high/low analyst price targets. As of this writing,
        Finnhub's own docs mark this endpoint 'Premium required' -- expect
        a FinnhubAccessError on the free tier.
        """
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
        """Insider buys/sells with price."""
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
