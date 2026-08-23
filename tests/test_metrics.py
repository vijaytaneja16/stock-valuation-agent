from stock_agent.valuation.metrics import (
    build_annual_kpi_table,
    cumulative_growth,
    margin_series,
    quarterly_yoy_comparison,
    yoy_growth_series,
)


def test_yoy_growth_series_most_recent_first():
    # 3 years, most recent first: 2024, 2023, 2022
    values = [120, 100, 80]
    growth = yoy_growth_series(values)
    assert round(growth[0], 4) == 0.20   # 2024 vs 2023: (120-100)/100
    assert round(growth[1], 4) == 0.25   # 2023 vs 2022: (100-80)/80
    assert growth[2] is None             # oldest period has no prior


def test_cumulative_growth():
    values = [120, 110, 100]  # most recent first
    assert cumulative_growth(values) == 0.20  # (120-100)/100


def test_margin_series_handles_zero_denominator():
    result = margin_series([50, 0], [100, 0])
    assert result[0] == 0.5
    assert result[1] is None


def test_build_annual_kpi_table():
    statements = [
        {"date": "2024", "revenue": 1100, "grossProfit": 550, "operatingIncome": 220, "depreciationAndAmortization": 50},
        {"date": "2023", "revenue": 1000, "grossProfit": 480, "operatingIncome": 200, "depreciationAndAmortization": 45},
    ]
    kpis = build_annual_kpi_table(statements)
    assert kpis["gross_margin"][0] == 0.5
    assert round(kpis["revenue_yoy_growth"][0], 4) == 0.10
    assert round(kpis["operating_income_yoy_growth"][0], 4) == 0.10


def test_quarterly_yoy_comparison_needs_five_quarters():
    quarters = [{"revenue": q} for q in [110, 105, 100, 95, 100]]  # 5 quarters, most recent first
    result = quarterly_yoy_comparison(quarters, "revenue")
    assert result["current"] == 110
    assert result["year_ago"] == 100
    assert result["growth"] == 0.10


def test_quarterly_yoy_comparison_insufficient_history():
    quarters = [{"revenue": q} for q in [110, 105]]
    result = quarterly_yoy_comparison(quarters, "revenue")
    assert result["current"] is None
