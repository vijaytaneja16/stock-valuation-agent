"""FastMCP server exposing the deterministic valuation engine as a tool.
The LLM never computes these numbers itself -- it calls this tool with data
it already fetched, and narrates the result.
"""
from fastmcp import FastMCP

from stock_agent.valuation.engine import run_valuation

mcp = FastMCP("valuation-tools")


@mcp.tool()
def calculate_valuation(
    annual_income_statements: list,
    quarterly_income_statements: list,
    annual_cash_flows: list,
    latest_quarter_balance_sheet: dict,
    ttm_income_inputs: dict,
    market_cap: float,
    stock_price: float,
    ttm_operating_cash_flow: float | None = None,
    ttm_capital_expenditure: float | None = None,
) -> dict:
    """Run the full custom valuation algorithm: adjusted EPS, multiples
    (annual/quarterly/blended x aggressive/conservative), the balance-sheet
    adjustment, and the resulting price scenarios, plus callout flags.

    All inputs should already be normalized numbers pulled from the
    financials tools -- this function does not fetch data itself.
    latest_quarter_balance_sheet must be the most recent QUARTER's balance
    sheet, not the most recent fiscal year's. ttm_operating_cash_flow and
    ttm_capital_expenditure are optional (sum of the last 4 quarters) and
    enable a trailing-twelve-month free-cash-flow/net-income callout in
    addition to the most-recent-fiscal-year check the tool always runs.
    """
    return run_valuation(
        annual_income_statements=annual_income_statements,
        quarterly_income_statements=quarterly_income_statements,
        annual_cash_flows=annual_cash_flows,
        latest_quarter_balance_sheet=latest_quarter_balance_sheet,
        ttm_income_inputs=ttm_income_inputs,
        market_cap=market_cap,
        stock_price=stock_price,
        ttm_operating_cash_flow=ttm_operating_cash_flow,
        ttm_capital_expenditure=ttm_capital_expenditure,
    )


if __name__ == "__main__":
    mcp.run()
