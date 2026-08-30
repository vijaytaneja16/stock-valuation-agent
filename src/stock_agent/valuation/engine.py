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
    calculate_fcf_to_net_income_ratio,
    calculate_free_cash_flow,
    quarterly_yoy_comparison,
)
from stock_agent.valuation.multiples import (
    calculate_multiples,
    calculate_price_scenarios,
    calculate_real_assets,
    calculate_real_liabilities_per_share,
)


def run_valuation(
    annual_income_statements: list[dict],
    quarterly_income_statements: list[dict],
    annual_cash_flows: list[dict],
    latest_quarter_balance_sheet: dict,
    ttm_income_inputs: dict,
    market_cap: float,
    stock_price: float,
    ttm_operating_cash_flow: float | None = None,
    ttm_capital_expenditure: float | None = None,
) -> dict:
    """
    annual_income_statements / annual_cash_flows: most-recent-first, up to 5 years
    quarterly_income_statements: most-recent-first, at least 5 quarters (for YOY)
    latest_quarter_balance_sheet: the MOST RECENT QUARTER's balance sheet
        (not the most recent fiscal year's) with keys:
        totalAssets, goodwillAndIntangibleAssets, propertyPlantEquipmentNet, totalLiabilities
    ttm_income_inputs: dict with keys matching AdjustedEarningsInputs fields --
        notably annual_one_time_items is a list of the "other income / gain
        on sale" line item for each of the last up to 5 years (most-recent-
        first), not a single TTM number.
    ttm_operating_cash_flow / ttm_capital_expenditure: trailing-twelve-month
        figures (typically the sum of the last 4 quarters' cash flow
        statements). Optional -- if omitted, the TTM free-cash-flow/net-
        income callout is simply skipped, but the annual-period version
        still runs.

    The balance-sheet adjustment (real assets minus liabilities, converted
    to a per-share value) is calculated exactly ONCE here and baked into
    every price scenario via calculate_price_scenarios() -- it must not be
    added again anywhere downstream.
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
        latest_quarter_balance_sheet["totalAssets"],
        latest_quarter_balance_sheet["goodwillAndIntangibleAssets"],
        latest_quarter_balance_sheet["propertyPlantEquipmentNet"],
    )
    net_liabilities = real_assets - latest_quarter_balance_sheet["totalLiabilities"]
    real_liabilities_per_share = calculate_real_liabilities_per_share(
        net_liabilities, market_cap, stock_price
    )

    # Express growth rates as whole-number percentages for the +8/+10 multiple math
    annual_growth_pct = (annual_growth_rate or 0) * 100
    quarterly_growth_pct = (quarterly_growth_rate or 0) * 100
    quarterly_revenue_growth_pct = (quarterly_revenue_yoy["growth"] or 0) * 100

    multiples = calculate_multiples(annual_growth_pct, quarterly_growth_pct, quarterly_revenue_growth_pct)

    # The balance-sheet adjustment (real_liabilities_per_share) is applied
    # exactly once, right here -- these ARE the final price scenarios.
    price_scenarios = calculate_price_scenarios(
        multiples, adjusted.adjusted_eps, real_liabilities_per_share
    )

    callouts = _build_callouts(
        annual_growth_rate, quarterly_growth_rate, annual_kpis, cash_flow_kpis,
        quarterly_d_and_a_yoy, adjusted, ttm_operating_cash_flow, ttm_capital_expenditure,
        ttm_income_inputs.get("reported_net_income"),
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
        "balance_sheet_adjustment": {
            "real_assets": real_assets,
            "net_liabilities": net_liabilities,
            "real_liabilities_per_share": real_liabilities_per_share,
        },
        "final_price_scenarios": price_scenarios.__dict__,
        "callouts": callouts,
    }


def _build_callouts(
    annual_growth_rate: float | None,
    quarterly_growth_rate: float | None,
    annual_kpis: dict,
    cash_flow_kpis: dict,
    quarterly_d_and_a_yoy: dict,
    adjusted,
    ttm_operating_cash_flow: float | None,
    ttm_capital_expenditure: float | None,
    ttm_reported_net_income: float | None,
) -> list[str]:
    """Flags per the spec's 'Call outs' section."""
    callouts = []

    ttm_value = getattr(adjusted, "one_time_item_ttm_value_stripped", 0)
    avg_value = getattr(adjusted, "one_time_item_average_added_back", 0)
    if ttm_value != 0 or avg_value != 0:
        callouts.append(
            f"One-time income/expense item: TTM actual value "
            f"({ttm_value:,.0f}) was stripped out of pretax income and the "
            f"5-year average ({avg_value:,.0f}) was added back instead, as a "
            "better estimate of this item's normal long-term contribution "
            "to earnings than the TTM figure alone. Review whether this "
            f"line item's TTM value materially differs from its historical "
            "average -- a large gap suggests either a genuine anomaly this "
            "year or a shift in a recurring source of income/expense worth "
            "understanding before relying on the adjusted EPS."
        )

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

    fcf_to_ni_series = cash_flow_kpis.get("fcf_to_net_income_ratio")
    if fcf_to_ni_series and fcf_to_ni_series[0] is not None and fcf_to_ni_series[0] < 0.8:
        callouts.append(
            f"Free cash flow / net income was {fcf_to_ni_series[0]:.2f} for the most "
            "recent fiscal year, below the 0.8 threshold -- earnings are converting to "
            "cash at a low rate. Check for aggressive revenue recognition, rising "
            "working capital needs, or capex running ahead of reported depreciation."
        )

    if ttm_operating_cash_flow is not None and ttm_capital_expenditure is not None:
        ttm_fcf = calculate_free_cash_flow(ttm_operating_cash_flow, ttm_capital_expenditure)
        ttm_fcf_to_ni_ratio = calculate_fcf_to_net_income_ratio(ttm_fcf, ttm_reported_net_income)
        if ttm_fcf_to_ni_ratio is not None and ttm_fcf_to_ni_ratio < 0.8:
            callouts.append(
                f"Free cash flow / net income was {ttm_fcf_to_ni_ratio:.2f} on a trailing-"
                "twelve-month basis, below the 0.8 threshold -- earnings are converting to "
                "cash at a low rate. Check for aggressive revenue recognition, rising "
                "working capital needs, or capex running ahead of reported depreciation."
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
