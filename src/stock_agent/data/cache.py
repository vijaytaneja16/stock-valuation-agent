"""Simple disk cache keyed by ticker/dataset/period.

Why this exists: FMP's free tier is 250 requests/day, Alpha Vantage's is much
lower. While you're debugging the valuation math you'll re-run the same
ticker dozens of times in a day — caching means you hit the API once per
dataset and then work from disk.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

CACHE_ROOT = Path(__file__).resolve().parents[3] / "data" / "raw"

# How long a cached file is considered fresh, per dataset type.
# Fundamentals change quarterly; prices/quotes should be refetched more often.
DEFAULT_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days
TTL_OVERRIDES = {
    "quote": 60 * 60,  # 1 hour
    "price_target": 60 * 60 * 24,  # 1 day
}


def _cache_path(ticker: str, dataset: str, period: str) -> Path:
    d = CACHE_ROOT / ticker.upper()
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{dataset}_{period}.json"


def cached_fetch(
    ticker: str,
    dataset: str,
    period: str,
    fetch_fn: Callable[[], Any],
    force_refresh: bool = False,
) -> Any:
    """Return cached JSON if fresh, else call fetch_fn() and cache the result.

    fetch_fn takes no arguments -- wrap your API call in a lambda/closure.
    """
    path = _cache_path(ticker, dataset, period)
    ttl = TTL_OVERRIDES.get(dataset, DEFAULT_TTL_SECONDS)

    if not force_refresh and path.exists():
        age = time.time() - path.stat().st_mtime
        if age < ttl:
            with open(path, "r") as f:
                return json.load(f)

    data = fetch_fn()
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return data
