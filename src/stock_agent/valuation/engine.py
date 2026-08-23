"""Orchestrates the full valuation algorithm end-to-end from normalized
statement inputs. This is the single function the agent calls after it has
fetched raw data -- everything here is deterministic Python, no LLM.
"""
from __future__ import annotations

from stock_agent.valuation.adjusted_earnings import (
    AdjustedEarningsInputs,
    calculate_adjusted_earnings,
)
from stock_agent.valuation.metrics import (
    build_annual_kpi_table,
    build_cash_flow_kpi_table,
    quarterly_yoy_comparison,
)
from stock_agent.valuation.multiples import (
    calculate_multiples,
    calculate_net_real_assets_adjustment,
    calculate_price_scenarios,
    calculate_real_assets,
    calculate_real_liabilities_per_share,
)


def run_valuation(
    annual_income_statements: list[dict],
    quarterly_income_statements: list[dict],
    annual_cash_flows: list[dict],
    latest_balance_sheet: dict,
    ttm_income_inputs: dict,
    market_cap: float,
    stock_price: float,
) -> dict:
    """
    annual_income_statements / annual_cash_flows: most-recent-first, up to 5 years
    quarterly_income_statements: most-recent-first, at least 5 quarters (for YOY)
    latest_balance_sheet: single most-recent period dict with keys:
        totalAssets, goodwillAndIntangibleAssets, propertyPlantEquipmentNet, totalLiabilities
    ttm_income_inputs: dict with keys matching AdjustedEarningsInputs fields
    """
    annual_kpis = build_annual_kpi_table(annual_income_statements)
    cash_flow_kpis = build_cash_flow_kpi_table(annual_cash_flows)

    quarterly_revenue_yoy = quarterly_yoy_comparison(quarterly_income_statements, "revenue")
    quarterly_operating_income_yoy = quarterly_yoy_comparison(quarterly_income_statements, "operatingIncome")
    quarterly_d_and_a_yoy = quarterly_yoy_comparison(
        quarterly_income_statements, "depreciationAndAmortization"
    )

    # "Annual growth rate" = most recent year's operating income YOY growth
    annual_growth_rate = annual_kpis["operating_income_yoy_growth"][0]
    # "Last quarter growth" = most recent quarter's operating income YOY growth
    quarterly_growth_rate = quarterly_operating_income_yoy["growth"]

    adjusted = calculate_adjusted_earnings(AdjustedEarningsInputs(**ttm_income_inputs))

    real_assets = calculate_real_assets(
        latest_balance_sheet["totalAssets"],
        latest_balance_sheet["goodwillAndIntangibleAssets"],
        latest_balance_sheet["propertyPlantEquipmentNet"],
    )
    net_liabilities = real_assets - latest_balance_sheet["totalLiabilities"]
    real_liabilities_per_share = calculate_real_liabilities_per_share(
        net_liabilities, market_cap, stock_price
    )

    # Express growth rates as whole-number percentages for the +8/+10 multiple math
    annual_growth_pct = (annual_growth_rate or 0) * 100
    quarterly_growth_pct = (quarterly_growth_rate or 0) * 100

    multiples = calculate_multiples(annual_growth_pct, quarterly_growth_pct)
    price_scenarios = calculate_price_scenarios(
        multiples, adjusted.adjusted_eps, real_liabilities_per_share
    )

    net_real_assets_adj = calculate_net_real_assets_adjustment(
        latest_balance_sheet["totalAssets"],
        latest_balance_sheet["goodwillAndIntangibleAssets"],
        latest_balance_sheet["propertyPlantEquipmentNet"],
        latest_balance_sheet["totalLiabilities"],
        market_cap,
        stock_price,
    )

    final_prices = {
        "annual_aggressive": price_scenarios.annual_aggressive + net_real_assets_adj["per_share_value"],
        "annual_conservative": price_scenarios.annual_conservative + net_real_assets_adj["per_share_value"],
        "quarter_aggressive": price_scenarios.quarter_aggressive + net_real_assets_adj["per_share_value"],
        "quarter_conservative": price_scenarios.quarter_conservative + net_real_assets_adj["per_share_value"],
    }

    callouts = _build_callouts(
        annual_growth_rate, quarterly_growth_rate, annual_kpis, quarterly_d_and_a_yoy
    )

    return {
        "annual_kpis": annual_kpis,
        "cash_flow_kpis": cash_flow_kpis,
        "quarterly_yoy": {
            "revenue": quarterly_revenue_yoy,
            "operating_income": quarterly_operating_income_yoy,
            "d_and_a": quarterly_d_and_a_yoy,
        },
        "adjusted_earnings": adjusted.__dict__,
        "multiples": multiples,
        "real_liabilities_per_share": real_liabilities_per_share,
        "net_real_assets_adjustment": net_real_assets_adj,
        "price_scenarios_before_asset_adjustment": price_scenarios.__dict__,
        "final_price_scenarios": final_prices,
        "callouts": callouts,
    }


def _build_callouts(
    annual_growth_rate: float | None,
    quarterly_growth_rate: float | None,
    annual_kpis: dict,
    quarterly_d_and_a_yoy: dict,
) -> list[str]:
    """Flags per the spec's 'Call outs' section."""
    callouts = []

    if annual_growth_rate is not None and quarterly_growth_rate is not None:
        if abs(annual_growth_rate - quarterly_growth_rate) > 0.20:
            callouts.append(
                f"Annual growth rate ({annual_growth_rate:.1%}) and quarterly growth rate "
                f"({quarterly_growth_rate:.1%}) diverge by more than 20 percentage points -- "
                "investigate whether the latest quarter is a one-time surge or deceleration."
            )

    d_and_a_growth = quarterly_d_and_a_yoy.get("growth")
    if d_and_a_growth is not None and abs(d_and_a_growth) > 0.20:
        callouts.append(
            f"D&A grew {d_and_a_growth:.1%} YoY in the most recent quarter vs. the prior year -- "
            "check for a capex step-up, acquisition-related amortization, or impairment."
        )

    # Compare TTM D&A/revenue mix vs. last fiscal year (uses annual series as proxy)
    d_and_a_pct_rev = annual_kpis.get("d_and_a_pct_revenue", [])
    if len(d_and_a_pct_rev) >= 2 and d_and_a_pct_rev[0] and d_and_a_pct_rev[1]:
        change = (d_and_a_pct_rev[0] - d_and_a_pct_rev[1]) / abs(d_and_a_pct_rev[1])
        if abs(change) > 0.20:
            callouts.append(
                f"D&A as % of revenue shifted {change:.1%} vs. the prior fiscal year -- "
                "worth checking against management commentary on capex or amortization schedules."
            )

    return callouts
