"""KPI and growth-rate calculations. Each function takes a list of
period dicts ordered MOST RECENT FIRST (this is how FMP returns data),
matching keys like 'revenue', 'grossProfit', 'operatingIncome', etc.
"""
from __future__ import annotations


def yoy_growth_series(values: list[float]) -> list[float | None]:
    """values ordered most-recent-first. Returns growth rates in the same
    order; the oldest period has no prior period so its growth is None.
    """
    growth = []
    for i in range(len(values)):
        if i + 1 >= len(values) or values[i + 1] in (0, None):
            growth.append(None)
        else:
            growth.append((values[i] - values[i + 1]) / abs(values[i + 1]))
    return growth


def cumulative_growth(values: list[float]) -> float | None:
    """Total growth from the oldest to the most recent period in the series."""
    if len(values) < 2 or values[-1] in (0, None):
        return None
    return (values[0] - values[-1]) / abs(values[-1])


def margin_series(numerator: list[float], denominator: list[float]) -> list[float | None]:
    return [
        (n / d) if d not in (0, None) else None
        for n, d in zip(numerator, denominator)
    ]


def build_annual_kpi_table(income_statements: list[dict]) -> dict:
    """income_statements: FMP-shaped list, most-recent-first, up to 5 years.
    Returns YOY growth + margins for revenue, gross profit, operating income,
    D&A -- everything the spec's "Module 3: Data Analysis" section asks for.
    """
    revenue = [s["revenue"] for s in income_statements]
    gross_profit = [s["grossProfit"] for s in income_statements]
    operating_income = [s["operatingIncome"] for s in income_statements]
    d_and_a = [s.get("depreciationAndAmortization", 0) for s in income_statements]

    return {
        "periods": [s.get("date") for s in income_statements],
        "revenue": revenue,
        "revenue_yoy_growth": yoy_growth_series(revenue),
        "revenue_cumulative_growth": cumulative_growth(revenue),
        "gross_margin": margin_series(gross_profit, revenue),
        "operating_margin": margin_series(operating_income, revenue),
        "operating_income_yoy_growth": yoy_growth_series(operating_income),
        "operating_income_cumulative_growth": cumulative_growth(operating_income),
        "d_and_a": d_and_a,
        "d_and_a_yoy_growth": yoy_growth_series(d_and_a),
        "d_and_a_pct_revenue": margin_series(d_and_a, revenue),
    }


def build_cash_flow_kpi_table(cash_flow_statements: list[dict]) -> dict:
    ocf = [s["operatingCashFlow"] for s in cash_flow_statements]
    capex = [abs(s.get("capitalExpenditure", 0)) for s in cash_flow_statements]
    return {
        "periods": [s.get("date") for s in cash_flow_statements],
        "operating_cash_flow": ocf,
        "ocf_yoy_growth": yoy_growth_series(ocf),
        "ocf_cumulative_growth": cumulative_growth(ocf),
        "capex": capex,
        "capex_yoy_growth": yoy_growth_series(capex),
        "capex_cumulative_growth": cumulative_growth(capex),
    }


def quarterly_yoy_comparison(quarterly_statements: list[dict], field: str) -> dict:
    """Compares the most recent quarter to the same quarter one year ago
    (4 quarters back in a most-recent-first list), per the spec's
    'Data analysis (Quarterly data)' section.
    """
    if len(quarterly_statements) < 5:
        return {"current": None, "year_ago": None, "growth": None}
    current = quarterly_statements[0].get(field)
    year_ago = quarterly_statements[4].get(field)
    growth = (current - year_ago) / abs(year_ago) if year_ago else None
    return {"current": current, "year_ago": year_ago, "growth": growth}
