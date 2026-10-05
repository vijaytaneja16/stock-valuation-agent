"""The actual agent: a Claude tool-use loop that plans which tools to call,
in what order, based on the system prompt's workflow -- as opposed to a
fixed script that calls the LLM once. This is the piece to highlight when
explaining "I built an AI agent" vs. "I called an LLM API".
"""
from __future__ import annotations

import json
import logging

import anthropic

from stock_agent.agent.prompts import SYSTEM_PROMPT
from stock_agent.agent.tool_schemas import TOOLS
from stock_agent.data.client_router import DataRouter
from stock_agent.valuation.engine import run_valuation

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_TOOL_ITERATIONS = 12  # safety valve against infinite tool-call loops


class ToolDispatcher:
    """Executes the tools Claude asks for. Delegates data fetching to
    DataRouter and valuation math to the engine -- same functions the MCP
    servers expose, called in-process here for simplicity.
    """

    def __init__(self):
        self.router = DataRouter()

    def execute(self, tool_name: str, tool_input: dict):
        try:
            if tool_name == "get_income_statement":
                return self.router.get_income_statement(**tool_input)
            if tool_name == "get_balance_sheet":
                return self.router.get_balance_sheet(**tool_input)
            if tool_name == "get_cash_flow":
                return self.router.get_cash_flow(**tool_input)
            if tool_name == "get_quote":
                return self.router.get_quote(**tool_input)
            if tool_name == "get_company_profile":
                return self.router.get_company_profile(**tool_input)
            if tool_name == "get_analyst_estimates":
                return self.router.get_analyst_estimates(**tool_input)
            if tool_name == "get_earnings_track_record":
                return self.router.get_earnings_track_record(**tool_input)
            if tool_name == "get_insider_activity":
                return self.router.get_insider_activity(**tool_input)
            if tool_name == "get_recent_filings":
                return self.router.get_recent_filings(**tool_input)
            if tool_name == "search_filing_text":
                return self.router.search_filing_text(
                    ticker=tool_input["ticker"],
                    query=tool_input["query"],
                    forms=tool_input.get("forms", "10-K,10-Q"),
                )
            if tool_name == "get_upcoming_earnings":
                return self.router.get_upcoming_earnings(**tool_input)
            if tool_name == "get_recent_news":
                return self.router.get_recent_news(**tool_input)
            if tool_name == "calculate_valuation":
                return run_valuation(**tool_input)
            return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            logger.exception(f"Tool {tool_name} failed")
            return {"error": str(e)}


def run_valuation_agent(ticker: str, on_step=None) -> str:
    """Runs the full agent loop for a ticker and returns the final report text.

    on_step: optional callback(step_description: str) for streaming progress
    to a UI (see report/render.py and the Streamlit app).
    """
    client = anthropic.Anthropic()
    dispatcher = ToolDispatcher()

    messages = [
        {"role": "user", "content": f"Run the full valuation workflow for {ticker}."}
    ]

    for iteration in range(MAX_TOOL_ITERATIONS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            return "".join(b.text for b in response.content if b.type == "text")

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                if on_step:
                    on_step(f"Calling {block.name}({json.dumps(block.input)[:120]}...)")
                result = dispatcher.execute(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, default=str)[:50000],  # guard context size
                })
        messages.append({"role": "user", "content": tool_results})

    return (
        "Agent stopped after reaching the maximum tool-call iterations "
        f"({MAX_TOOL_ITERATIONS}) without producing a final report. "
        "This usually means a data source is failing repeatedly -- check logs."
    )
