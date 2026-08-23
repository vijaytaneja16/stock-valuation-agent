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
    latest_balance_sheet: dict,
    ttm_income_inputs: dict,
    market_cap: float,
    stock_price: float,
) -> dict:
    """Run the full custom valuation algorithm: adjusted EPS, multiples,
    net-liability adjustment, and the four price scenarios (annual/quarterly
    x aggressive/conservative), plus callout flags.

    All inputs should already be normalized numbers pulled from the
    financials tools -- this function does not fetch data itself.
    """
    return run_valuation(
        annual_income_statements=annual_income_statements,
        quarterly_income_statements=quarterly_income_statements,
        annual_cash_flows=annual_cash_flows,
        latest_balance_sheet=latest_balance_sheet,
        ttm_income_inputs=ttm_income_inputs,
        market_cap=market_cap,
        stock_price=stock_price,
    )


if __name__ == "__main__":
    mcp.run()
