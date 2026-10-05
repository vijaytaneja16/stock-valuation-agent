"""FastMCP server exposing financial data tools. Runnable standalone
(e.g. via `python -m stock_agent.mcp_servers.financials_server` or hooked
into Claude Desktop / any MCP client) -- this is the piece that demonstrates
real MCP server authorship for your portfolio, independent of how the
in-process orchestrator calls these same functions directly (see agent/orchestrator.py).
"""
from fastmcp import FastMCP

from stock_agent.data.client_router import DataRouter

mcp = FastMCP("financials-tools")
router = DataRouter()


@mcp.tool()
def get_income_statement(ticker: str, period: str = "annual", limit: int = 5) -> list:
    """Fetch income statements for a ticker. period is 'annual' or 'quarter'."""
    return router.get_income_statement(ticker, period, limit)


@mcp.tool()
def get_balance_sheet(ticker: str, period: str = "annual", limit: int = 5) -> list:
    """Fetch balance sheets for a ticker. period is 'annual' or 'quarter'."""
    return router.get_balance_sheet(ticker, period, limit)


@mcp.tool()
def get_cash_flow(ticker: str, period: str = "annual", limit: int = 5) -> list:
    """Fetch cash flow statements for a ticker. period is 'annual' or 'quarter'."""
    return router.get_cash_flow(ticker, period, limit)


@mcp.tool()
def get_quote(ticker: str) -> dict:
    """Current stock price, market cap, and shares outstanding."""
    return router.get_quote(ticker)


@mcp.tool()
def get_company_profile(ticker: str) -> dict:
    """Sector, industry, description, and other company-level metadata."""
    return router.get_company_profile(ticker)


@mcp.tool()
def get_analyst_estimates(ticker: str) -> dict:
    """Analyst price targets and buy/hold/sell recommendation trends."""
    return router.get_analyst_estimates(ticker)


@mcp.tool()
def get_earnings_track_record(ticker: str) -> list:
    """Historical EPS actual vs. estimate -- beat/miss track record."""
    return router.get_earnings_track_record(ticker)


@mcp.tool()
def get_insider_activity(ticker: str) -> list:
    """Recent insider buy/sell transactions with price."""
    return router.get_insider_activity(ticker)


@mcp.tool()
def get_upcoming_earnings(ticker: str) -> dict:
    """Past and upcoming earnings announcement dates for this ticker. The
    caller is responsible for identifying which date is actually in the
    future relative to today -- this tool doesn't filter by date itself.
    """
    return router.get_upcoming_earnings(ticker)


if __name__ == "__main__":
    mcp.run()
