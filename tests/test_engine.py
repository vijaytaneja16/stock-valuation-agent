from stock_agent.valuation.engine import run_valuation


def _synthetic_annual_income_statements():
    # Most recent first, 3 years, ~10% growth
    return [
        {"date": "2024", "revenue": 1210, "grossProfit": 605, "operatingIncome": 242, "depreciationAndAmortization": 55},
        {"date": "2023", "revenue": 1100, "grossProfit": 550, "operatingIncome": 220, "depreciationAndAmortization": 50},
        {"date": "2022", "revenue": 1000, "grossProfit": 480, "operatingIncome": 200, "depreciationAndAmortization": 45},
    ]


def _synthetic_quarterly_income_statements():
    # Most recent first, 5 quarters so YOY comparison works
    return [
        {"revenue": 320, "operatingIncome": 64, "depreciationAndAmortization": 14},
        {"revenue": 300, "operatingIncome": 60, "depreciationAndAmortization": 13},
        {"revenue": 290, "operatingIncome": 58, "depreciationAndAmortization": 13},
        {"revenue": 300, "operatingIncome": 60, "depreciationAndAmortization": 14},
        {"revenue": 290, "operatingIncome": 58, "depreciationAndAmortization": 13},  # year-ago quarter
    ]


def test_run_valuation_end_to_end():
    result = run_valuation(
        annual_income_statements=_synthetic_annual_income_statements(),
        quarterly_income_statements=_synthetic_quarterly_income_statements(),
        annual_cash_flows=[
            {"date": "2024", "operatingCashFlow": 250, "capitalExpenditure": -60},
            {"date": "2023", "operatingCashFlow": 230, "capitalExpenditure": -55},
            {"date": "2022", "operatingCashFlow": 210, "capitalExpenditure": -50},
        ],
        latest_balance_sheet={
            "totalAssets": 2000,
            "goodwillAndIntangibleAssets": 300,
            "propertyPlantEquipmentNet": 500,
            "totalLiabilities": 900,
        },
        ttm_income_inputs={
            "ttm_pretax_income": 300,
            "annual_one_time_items": [0, 0, 0],
            "net_interest_income": 0,
            "ttm_tax_expense": 60,   # 20% effective rate
            "reported_net_income": 240,
            "reported_diluted_eps": 4.0,
        },
        market_cap=5000,
        stock_price=100,
    )

    # Sanity checks -- exact numbers matter less here than confirming every
    # stage of the pipeline runs and produces internally consistent output.
    assert result["annual_kpis"]["revenue_yoy_growth"][0] is not None
    assert result["adjusted_earnings"]["adjusted_eps"] > 0
    assert "annual_aggressive" in result["final_price_scenarios"]
    assert "annual_conservative" in result["final_price_scenarios"]
    assert isinstance(result["callouts"], list)

    # Aggressive scenario should always be >= conservative for the same period,
    # since it uses a higher multiple on the same adjusted EPS
    assert result["final_price_scenarios"]["annual_aggressive"] >= result["final_price_scenarios"]["annual_conservative"]
