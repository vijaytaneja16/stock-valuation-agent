"""Client for Alpha Vantage. Currently used only as a fallback for analyst
price target data (FMP's price-target-consensus is the primary source; see
client_router.py) -- not wired in as a fallback for financial statements,
since its free tier is much tighter than FMP's (25 requests/day vs. 250).

Docs: https://www.alphavantage.co/documentation/
"""
from __future__ import annotations

import os

import requests

from stock_agent.data.cache import cached_fetch

BASE_URL = "https://www.alphavantage.co/query"


class AlphaVantageClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ["ALPHAVANTAGE_API_KEY"]

    def _get(self, params: dict) -> dict:
        params = dict(params)
        params["apikey"] = self.api_key
        resp = requests.get(BASE_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        # Alpha Vantage returns 200 OK with an error message in the body on
        # bad requests or rate-limit hits, rather than a non-200 status code.
        if "Note" in data or "Information" in data:
            raise ValueError(f"Alpha Vantage rate limit or notice: {data}")
        if "Error Message" in data:
            raise ValueError(f"Alpha Vantage error: {data['Error Message']}")
        return data

    def get_company_overview(self, ticker: str) -> dict:
        """Includes AnalystTargetPrice among many other fundamental fields
        -- a single mean target, not the high/low/median spread FMP/Finnhub
        provide.
        """
        return cached_fetch(
            ticker, "av_overview", "current",
            lambda: self._get({"function": "OVERVIEW", "symbol": ticker}),
        )
