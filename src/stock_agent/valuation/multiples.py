"""Multiples (growth rate + 8/+10) and the resulting price scenarios,
plus the net-real-assets / real-liabilities-per-share calculation from the
balance sheet, per the spec's 'Calculate net liabilities' and 'Calculate
valuations based on multiples' sections.

All growth rates in this module are expressed as whole numbers (e.g. 15 for
15%, not 0.15), since the spec adds a flat +8/+10 to form a P/E-like
multiple -- using a decimal fraction would produce a nonsensical multiple
like 8.15x instead of 23x.
"""
from __future__ import annotations

from dataclasses import dataclass


def calculate_blended_growth_rate(
    annual_growth_rate: float,
    quarterly_growth_rate: float,
    quarterly_revenue_growth_rate: float,
) -> float:
    """Blend annual and quarterly operating income growth into a single
    rate that reflects recent momentum without overweighting a single
    unusually strong or weak quarter.

    - If the quarter is accelerating vs. the annual trend (quarterly >
      annual), blend them evenly: the average of the two.
    - If the quarter is decelerating vs. the annual trend (quarterly <=
      annual), extrapolate the deceleration forward rather than just
      averaging it away: quarterly - (annual - quarterly), which equals
      2*quarterly - annual. This lets a clearly slowing quarter pull the
      blended rate down further than a simple average would.
    - Cap: the blended rate can never exceed 3x the quarter's YoY revenue
      growth rate, since operating income growth detached from revenue
      growth by more than 3x is a sign of margin expansion (or an
      accounting item) rather than durable earnings growth -- capping it
      keeps the multiple grounded in the top line.
    """
    if quarterly_growth_rate > annual_growth_rate:
        blended = (quarterly_growth_rate + annual_growth_rate) / 2
    else:
        blended = quarterly_growth_rate - (annual_growth_rate - quarterly_growth_rate)

    cap = 3 * quarterly_revenue_growth_rate
    if blended > cap:
        blended = cap

    return blended


def calculate_multiples(
    annual_growth_rate: float,
    quarterly_growth_rate: float,
    quarterly_revenue_growth_rate: float,
) -> dict:
    """Uses the latest completed fiscal year's operating income growth rate
    (annual_growth_rate) and the latest completed quarter's YoY operating
    income growth rate (quarterly_growth_rate), plus the latest quarter's
    YoY revenue growth rate for the blended-rate cap.
    """
    blended_growth_rate = calculate_blended_growth_rate(
        annual_growth_rate, quarterly_growth_rate, quarterly_revenue_growth_rate
    )
    return {
        "annual_aggressive": annual_growth_rate + 10,
        "annual_conservative": annual_growth_rate + 8,
        "quarter_aggressive": quarterly_growth_rate + 10,
        "quarter_conservative": quarterly_growth_rate + 8,
        "blended_growth_rate": blended_growth_rate,
        "blended_aggressive": blended_growth_rate + 10,
        "blended_conservative": blended_growth_rate + 8,
    }


def calculate_real_assets(total_assets: float, intangibles_and_goodwill: float, ppe: float) -> float:
    return total_assets - intangibles_and_goodwill - 0.5 * ppe


def calculate_net_liabilities(real_assets: float, total_liabilities: float) -> float:
    return real_assets - total_liabilities


def calculate_real_liabilities_per_share(
    net_liabilities: float, market_cap: float, stock_price: float
) -> float:
    """Per the spec: (Net Liabilities / Market Cap) * Stock Price.

    This is the ONE balance-sheet adjustment applied to every price
    scenario -- it gets added inside calculate_price_scenarios() below and
    should not be added again anywhere else. (An earlier version of this
    module also had a separately-named 'net real assets' calculation that
    computed this exact same value a second way and added it a second
    time -- that was a double-count bug, now removed.)
    """
    return (net_liabilities / market_cap) * stock_price if market_cap else 0.0


@dataclass
class PriceScenarios:
    annual_aggressive: float
    annual_conservative: float
    quarter_aggressive: float
    quarter_conservative: float
    blended_aggressive: float
    blended_conservative: float


def calculate_price_scenarios(
    multiples: dict, adjusted_eps: float, real_liabilities_per_share: float
) -> PriceScenarios:
    return PriceScenarios(
        annual_aggressive=multiples["annual_aggressive"] * adjusted_eps + real_liabilities_per_share,
        annual_conservative=multiples["annual_conservative"] * adjusted_eps + real_liabilities_per_share,
        quarter_aggressive=multiples["quarter_aggressive"] * adjusted_eps + real_liabilities_per_share,
        quarter_conservative=multiples["quarter_conservative"] * adjusted_eps + real_liabilities_per_share,
        blended_aggressive=multiples["blended_aggressive"] * adjusted_eps + real_liabilities_per_share,
        blended_conservative=multiples["blended_conservative"] * adjusted_eps + real_liabilities_per_share,
    )
