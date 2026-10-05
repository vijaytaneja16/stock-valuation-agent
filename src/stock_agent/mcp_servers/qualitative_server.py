"""FastMCP server exposing qualitative-research tools -- SEC filing lookup
and full-text search. Used for the "what does the company do", "any
lawsuits", "cyclicality" parts of the spec.
"""
from fastmcp import FastMCP

from stock_agent.data.client_router import DataRouter

mcp = FastMCP("qualitative-tools")
router = DataRouter()


@mcp.tool()
def get_recent_filings(ticker: str) -> list:
    """List recent 10-K/10-Q/8-K filings with dates and document URLs."""
    return router.get_recent_filings(ticker)


@mcp.tool()
def search_filing_text(ticker: str, query: str, forms: str = "10-K,10-Q") -> dict:
    """Full-text search across a company's SEC filings for a phrase --
    e.g. 'cyclical', 'goodwill impairment', 'competitive pressure',
    'material weakness'. Useful for finding qualitative risk language
    without reading entire filings.
    """
    return router.search_filing_text(query, ticker=ticker, forms=forms)


@mcp.tool()
def get_recent_news(ticker: str, days_back: int = 30) -> list:
    """Recent news headlines for this company. Use this to spot mentions
    of catalysts that don't come from a structured calendar -- investor
    days, product launches, conference appearances, guidance updates.
    """
    return router.get_recent_news(ticker, days_back)


if __name__ == "__main__":
    mcp.run()
