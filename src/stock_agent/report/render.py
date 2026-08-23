"""The agent writes most of the final report as free text (see prompts.py),
but this module provides a markdown table renderer for the valuation
engine's raw output -- useful if you want a guaranteed-consistent numbers
table independent of what the LLM chooses to include in prose, or if you
want to render a report without calling the LLM at all (e.g. for a quick
numbers-only check).
"""
from __future__ import annotations


def render_price_scenarios_table(valuation_result: dict) -> str:
    prices = valuation_result["final_price_scenarios"]
    lines = [
        "| Scenario | Price |",
        "|---|---|",
        f"| Annual - Aggressive | ${prices['annual_aggressive']:.2f} |",
        f"| Annual - Conservative | ${prices['annual_conservative']:.2f} |",
        f"| Quarterly - Aggressive | ${prices['quarter_aggressive']:.2f} |",
        f"| Quarterly - Conservative | ${prices['quarter_conservative']:.2f} |",
    ]
    return "\n".join(lines)


def render_kpi_table(valuation_result: dict) -> str:
    kpis = valuation_result["annual_kpis"]
    periods = kpis["periods"]
    lines = ["| Metric | " + " | ".join(periods) + " |", "|---" * (len(periods) + 1) + "|"]

    def fmt_row(label, values, as_pct=False):
        cells = []
        for v in values:
            if v is None:
                cells.append("n/a")
            elif as_pct:
                cells.append(f"{v:.1%}")
            else:
                cells.append(f"{v:,.0f}")
        return f"| {label} | " + " | ".join(cells) + " |"

    lines.append(fmt_row("Revenue", kpis["revenue"]))
    lines.append(fmt_row("Revenue YoY Growth", kpis["revenue_yoy_growth"], as_pct=True))
    lines.append(fmt_row("Gross Margin", kpis["gross_margin"], as_pct=True))
    lines.append(fmt_row("Operating Margin", kpis["operating_margin"], as_pct=True))
    lines.append(fmt_row("D&A", kpis["d_and_a"]))
    lines.append(fmt_row("D&A YoY Growth", kpis["d_and_a_yoy_growth"], as_pct=True))
    return "\n".join(lines)


def render_callouts(valuation_result: dict) -> str:
    callouts = valuation_result.get("callouts", [])
    if not callouts:
        return "No automated callouts triggered."
    return "\n".join(f"- {c}" for c in callouts)
