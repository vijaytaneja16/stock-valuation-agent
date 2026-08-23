"""Streamlit UI for the stock valuation agent.

Run with: streamlit run app_streamlit.py

Why Streamlit for this project: it's the fastest path from "working Python
agent" to "something an employer can click through in 30 seconds" -- no
frontend code, live progress display while the agent calls tools, and it
screenshots/GIFs well for a README. A CLI is enough to prove the agent
works; Streamlit is what makes the repo demo-able.
"""
import streamlit as st
from dotenv import load_dotenv

from stock_agent.agent.orchestrator import run_valuation_agent

load_dotenv()

st.set_page_config(page_title="AI Stock Valuation Agent", layout="wide")

st.title("AI Stock Valuation Agent")
st.caption(
    "Claude + MCP-style tool servers + a deterministic Python valuation engine. "
    "The LLM plans and narrates; Python computes every number."
)

ticker = st.text_input("Ticker", value="AAPL").strip().upper()
run_button = st.button("Run valuation", type="primary")

if run_button and ticker:
    progress_box = st.status("Running agent...", expanded=True)
    steps: list[str] = []

    def on_step(msg: str):
        steps.append(msg)
        progress_box.write(msg)

    with st.spinner(f"Analyzing {ticker}..."):
        try:
            report = run_valuation_agent(ticker, on_step=on_step)
            progress_box.update(label="Done", state="complete")
        except Exception as e:
            progress_box.update(label="Failed", state="error")
            st.error(f"Agent run failed: {e}")
            st.stop()

    st.markdown("---")
    st.markdown(report)

    st.download_button(
        "Download report as markdown",
        data=report,
        file_name=f"{ticker}_valuation_report.md",
        mime="text/markdown",
    )
elif run_button:
    st.warning("Enter a ticker first.")

with st.sidebar:
    st.subheader("How this works")
    st.markdown(
        "1. Claude decides which data tools to call\n"
        "2. Raw financials are fetched from FMP/Finnhub/yfinance (cached to disk)\n"
        "3. Claude normalizes inputs and calls the valuation tool **once** -- "
        "all math happens in Python, not the LLM\n"
        "4. Claude gathers qualitative context from SEC filings\n"
        "5. The final report is assembled in a fixed section order"
    )
    st.subheader("Data sources")
    st.markdown(
        "- Financial Modeling Prep (statements)\n"
        "- Finnhub (estimates, insider activity)\n"
        "- yfinance (fallback)\n"
        "- SEC EDGAR (qualitative text)"
    )
