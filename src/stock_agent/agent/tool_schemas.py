"""JSON tool schemas passed to the Claude API. These mirror the tools
exposed by the MCP servers in mcp_servers/ -- the orchestrator dispatches
these directly in-process for simplicity (see orchestrator.py), while the
MCP servers expose the same underlying functions for standalone/interop use
(e.g. Claude Desktop, other MCP clients). Keeping both is intentional: it
shows you understand MCP as a protocol while keeping the demo agent simple
to run and debug.
"""

TOOLS = [
    {
        "name": "get_income_statement",
        "description": "Fetch income statements for a ticker.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "period": {"type": "string", "enum": ["annual", "quarter"], "default": "annual"},
                "limit": {"type": "integer", "default": 5},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "get_balance_sheet",
        "description": "Fetch balance sheets for a ticker.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "period": {"type": "string", "enum": ["annual", "quarter"], "default": "annual"},
                "limit": {"type": "integer", "default": 5},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "get_cash_flow",
        "description": "Fetch cash flow statements for a ticker.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "period": {"type": "string", "enum": ["annual", "quarter"], "default": "annual"},
                "limit": {"type": "integer", "default": 5},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "get_quote",
        "description": "Current stock price, market cap, and shares outstanding.",
        "input_schema": {
            "type": "object",
            "properties": {"ticker": {"type": "string"}},
            "required": ["ticker"],
        },
    },
    {
        "name": "get_company_profile",
        "description": "Sector, industry, description, and other company metadata.",
        "input_schema": {
            "type": "object",
            "properties": {"ticker": {"type": "string"}},
            "required": ["ticker"],
        },
    },
    {
        "name": "get_analyst_estimates",
        "description": "Analyst price targets and buy/hold/sell recommendation trends.",
        "input_schema": {
            "type": "object",
            "properties": {"ticker": {"type": "string"}},
            "required": ["ticker"],
        },
    },
    {
        "name": "get_earnings_track_record",
        "description": "Historical EPS actual vs. estimate -- beat/miss track record.",
        "input_schema": {
            "type": "object",
            "properties": {"ticker": {"type": "string"}},
            "required": ["ticker"],
        },
    },
    {
        "name": "get_insider_activity",
        "description": "Recent insider buy/sell transactions with price.",
        "input_schema": {
            "type": "object",
            "properties": {"ticker": {"type": "string"}},
            "required": ["ticker"],
        },
    },
    {
        "name": "get_recent_filings",
        "description": "List recent 10-K/10-Q/8-K filings with dates and document URLs.",
        "input_schema": {
            "type": "object",
            "properties": {"ticker": {"type": "string"}},
            "required": ["ticker"],
        },
    },
    {
        "name": "search_filing_text",
        "description": "Full-text search across a company's SEC filings for a phrase (e.g. 'cyclical', 'goodwill impairment').",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "query": {"type": "string"},
                "forms": {"type": "string", "default": "10-K,10-Q"},
            },
            "required": ["ticker", "query"],
        },
    },
    {
        "name": "calculate_valuation",
        "description": (
            "Run the full deterministic valuation algorithm: adjusted EPS, "
            "multiples, net-liability adjustment, and the four price "
            "scenarios, plus callout flags. Call this exactly once per "
            "ticker with normalized inputs derived from the data tools."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "annual_income_statements": {"type": "array", "items": {"type": "object"}},
                "quarterly_income_statements": {"type": "array", "items": {"type": "object"}},
                "annual_cash_flows": {"type": "array", "items": {"type": "object"}},
                "latest_balance_sheet": {"type": "object"},
                "ttm_income_inputs": {
                    "type": "object",
                    "properties": {
                        "ttm_pretax_income": {"type": "number"},
                        "one_time_items": {"type": "number"},
                        "net_interest_income": {"type": "number"},
                        "ttm_tax_expense": {"type": "number"},
                        "reported_net_income": {"type": "number"},
                        "reported_diluted_eps": {"type": "number"},
                    },
                    "required": [
                        "ttm_pretax_income", "one_time_items", "net_interest_income",
                        "ttm_tax_expense", "reported_net_income", "reported_diluted_eps",
                    ],
                },
                "market_cap": {"type": "number"},
                "stock_price": {"type": "number"},
            },
            "required": [
                "annual_income_statements", "quarterly_income_statements",
                "annual_cash_flows", "latest_balance_sheet", "ttm_income_inputs",
                "market_cap", "stock_price",
            ],
        },
    },
]
