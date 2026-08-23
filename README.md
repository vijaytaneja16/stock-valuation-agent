# AI Stock Valuation Agent

An agentic financial analyst: **Claude (tool-use loop) + MCP-style tool
servers + a deterministic Python valuation engine**, applied to a custom
multi-factor stock valuation methodology.

## Why this design

The LLM plans which tools to call and in what order, and writes the
narrative/qualitative sections. It **never computes a valuation number
itself** — every calculation (adjusted EPS, growth-adjusted multiples,
net-liability adjustment, the four price scenarios) runs in tested,
deterministic Python. This split is the core design decision: it makes the
numbers reproducible and auditable, and it's the difference between "calling
an LLM API" and building an agent with a real tool boundary.

## Architecture

```
Claude (orchestrator, tool-use loop)
   |
   |-- data tools -----> FMP / Finnhub / yfinance (financial statements, estimates)
   |-- valuation tool -> pure Python engine (your custom algorithm)
   |-- qualitative tools -> SEC EDGAR full-text search
   |
   v
Final report (fixed section order: price estimate, valuation components,
KPIs, callouts, qualitative analysis, analyst/market data)
```

MCP servers in `src/stock_agent/mcp_servers/` expose the same tool functions
for use with any MCP client (e.g. Claude Desktop); the in-process
orchestrator (`agent/orchestrator.py`) dispatches them directly for
simplicity in this demo.

## Setup

```bash
git clone <your-repo-url>
cd stock-valuation-agent
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env           # then fill in your API keys
```

Get free API keys:
- Anthropic: https://console.anthropic.com/
- FMP: https://site.financialmodelingprep.com/register (250 requests/day free)
- Finnhub: https://finnhub.io/register (free tier)
- SEC EDGAR: no key needed, just set your email in `SEC_EDGAR_USER_AGENT` in `.env`

## Run it

CLI:
```bash
python cli.py AAPL
python cli.py AAPL --out report_aapl.md
```

Web UI:
```bash
streamlit run app_streamlit.py
```

## Test the valuation math (no API keys needed)

```bash
pytest tests/test_metrics.py tests/test_adjusted_earnings.py tests/test_multiples.py tests/test_engine.py -v
```

## Project structure

```
src/stock_agent/
├── data/            # API clients + disk cache + fallback router
├── valuation/        # pure-Python valuation engine (the actual algorithm)
├── mcp_servers/       # FastMCP servers exposing tools for any MCP client
├── agent/             # Claude tool-use loop + prompts + tool schemas
└── report/            # markdown table rendering helpers
tests/                 # unit + end-to-end tests for the valuation math
```

## Known limitations

- Free-tier rate limits (FMP: 250 req/day) — the disk cache in `data/cache.py`
  keeps re-runs from burning quota, but a cold run across many tickers in one
  day can hit limits.
- Earnings call transcript text isn't wired up in the free-tier data layer —
  qualitative call-transcript callouts currently come from SEC filing text
  and general knowledge rather than verbatim transcripts.
- `yfinance` is an unofficial library and can break without notice if Yahoo
  changes its page structure; it's used only as a fallback.

## Example output

See `examples/` for a sample rendered report.
