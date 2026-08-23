"""Multiples (growth rate + 8/+10) and the four resulting price scenarios,
plus the net-real-assets / real-liabilities-per-share calculation from the
balance sheet, per the spec's 'Calculate net liabilities' and 'Calculate
valuations based on multiples' sections.
"""
from __future__ import annotations

from dataclasses import dataclass


def calculate_multiples(annual_growth_rate: float, quarterly_growth_rate: float) -> dict:
    """Growth rates as decimals (e.g. 0.15 for 15%) or whole numbers -- be
    consistent with how you pass adjusted_eps's scale. The spec adds flat
    +8/+10 to the growth rate to form a P/E-like multiple, so growth rate
    here should be expressed as a whole number (e.g. 15, not 0.15) to
    produce a sane multiple like 23x or 25x.
    """
    return {
        "annual_aggressive": annual_growth_rate + 10,
        "annual_conservative": annual_growth_rate + 8,
        "quarter_aggressive": quarterly_growth_rate + 10,
        "quarter_conservative": quarterly_growth_rate + 8,
    }


def calculate_real_assets(total_assets: float, intangibles_and_goodwill: float, ppe: float) -> float:
    return total_assets - intangibles_and_goodwill - 0.5 * ppe


def calculate_net_liabilities(real_assets: float, total_liabilities: float) -> float:
    return real_assets - total_liabilities


def calculate_real_liabilities_per_share(
    net_liabilities: float, market_cap: float, stock_price: float
) -> float:
    """Per the spec: (Net Liabilities / Market Cap) * Stock Price."""
    return (net_liabilities / market_cap) * stock_price if market_cap else 0.0


@dataclass
class PriceScenarios:
    annual_aggressive: float
    annual_conservative: float
    quarter_aggressive: float
    quarter_conservative: float


def calculate_price_scenarios(
    multiples: dict, adjusted_eps: float, real_liabilities_per_share: float
) -> PriceScenarios:
    return PriceScenarios(
        annual_aggressive=multiples["annual_aggressive"] * adjusted_eps + real_liabilities_per_share,
        annual_conservative=multiples["annual_conservative"] * adjusted_eps + real_liabilities_per_share,
        quarter_aggressive=multiples["quarter_aggressive"] * adjusted_eps + real_liabilities_per_share,
        quarter_conservative=multiples["quarter_conservative"] * adjusted_eps + real_liabilities_per_share,
    )


def calculate_net_real_assets_adjustment(
    total_assets: float,
    intangibles_and_goodwill: float,
    ppe: float,
    total_liabilities: float,
    market_cap: float,
    stock_price: float,
) -> dict:
    """Per the spec's final adjustment step: net real assets as a % of
    market cap, converted to a per-share value to add/subtract from the
    scenario prices.
    """
    net_real_assets = total_assets - intangibles_and_goodwill - 0.5 * ppe - total_liabilities
    pct_of_market_cap = net_real_assets / market_cap if market_cap else 0.0
    per_share_value = pct_of_market_cap * stock_price
    return {
        "net_real_assets": net_real_assets,
        "pct_of_market_cap": pct_of_market_cap,
        "per_share_value": per_share_value,
    }
