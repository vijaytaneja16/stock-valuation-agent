#!/usr/bin/env python3
"""Run the valuation agent from the command line.

Usage:
    python cli.py AAPL
    python cli.py AAPL --out report_aapl.md
"""
import argparse
import sys

from dotenv import load_dotenv

from stock_agent.agent.orchestrator import run_valuation_agent

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Run the AI stock valuation agent.")
    parser.add_argument("ticker", help="Stock ticker, e.g. AAPL")
    parser.add_argument("--out", help="Optional path to save the report as markdown")
    args = parser.parse_args()

    def on_step(msg):
        print(f"  -> {msg}", file=sys.stderr)

    print(f"Running valuation agent for {args.ticker.upper()}...", file=sys.stderr)
    report = run_valuation_agent(args.ticker.upper(), on_step=on_step)

    print("\n" + report)

    if args.out:
        with open(args.out, "w") as f:
            f.write(report)
        print(f"\nSaved to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
