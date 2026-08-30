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
        latest_quarter_balance_sheet={
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


def test_balance_sheet_adjustment_applied_exactly_once():
    """Regression test for a fixed double-counting bug: the real-liabilities-
    per-share adjustment must appear exactly once in each final price
    scenario. Verified by re-running with total_liabilities changed and
    confirming the price moves by exactly one multiple of the resulting
    per-share delta, not two.
    """
    common_kwargs = dict(
        annual_income_statements=_synthetic_annual_income_statements(),
        quarterly_income_statements=_synthetic_quarterly_income_statements(),
        annual_cash_flows=[
            {"date": "2024", "operatingCashFlow": 250, "capitalExpenditure": -60},
            {"date": "2023", "operatingCashFlow": 230, "capitalExpenditure": -55},
            {"date": "2022", "operatingCashFlow": 210, "capitalExpenditure": -50},
        ],
        ttm_income_inputs={
            "ttm_pretax_income": 300,
            "annual_one_time_items": [0, 0, 0],
            "net_interest_income": 0,
            "ttm_tax_expense": 60,
            "reported_net_income": 240,
            "reported_diluted_eps": 4.0,
        },
        market_cap=5000,
        stock_price=100,
    )

    result_a = run_valuation(
        latest_quarter_balance_sheet={
            "totalAssets": 2000, "goodwillAndIntangibleAssets": 300,
            "propertyPlantEquipmentNet": 500, "totalLiabilities": 900,
        },
        **common_kwargs,
    )
    # Increase total liabilities by 1000 -> net_liabilities drops by 1000 ->
    # real_liabilities_per_share drops by (1000/market_cap)*stock_price = 20
    result_b = run_valuation(
        latest_quarter_balance_sheet={
            "totalAssets": 2000, "goodwillAndIntangibleAssets": 300,
            "propertyPlantEquipmentNet": 500, "totalLiabilities": 1900,
        },
        **common_kwargs,
    )

    expected_delta = -20.0  # (-1000 / 5000) * 100
    actual_delta = (
        result_b["final_price_scenarios"]["annual_aggressive"]
        - result_a["final_price_scenarios"]["annual_aggressive"]
    )
    # If the bug were present, this delta would be -40 (double-counted)
    # instead of -20.
    assert round(actual_delta, 4) == expected_delta


def test_low_fcf_to_net_income_ratio_triggers_callout():
    result = run_valuation(
        annual_income_statements=_synthetic_annual_income_statements(),
        quarterly_income_statements=_synthetic_quarterly_income_statements(),
        annual_cash_flows=[
            # FCF = 150-100 = 50; net income 100 -> ratio 0.5, below the 0.8 threshold
            {"date": "2024", "operatingCashFlow": 150, "capitalExpenditure": -100, "netIncome": 100},
            {"date": "2023", "operatingCashFlow": 140, "capitalExpenditure": -50, "netIncome": 95},
            {"date": "2022", "operatingCashFlow": 130, "capitalExpenditure": -45, "netIncome": 90},
        ],
        latest_quarter_balance_sheet={
            "totalAssets": 2000, "goodwillAndIntangibleAssets": 300,
            "propertyPlantEquipmentNet": 500, "totalLiabilities": 900,
        },
        ttm_income_inputs={
            "ttm_pretax_income": 300, "annual_one_time_items": [0, 0, 0],
            "net_interest_income": 0, "ttm_tax_expense": 60,
            "reported_net_income": 240, "reported_diluted_eps": 4.0,
        },
        market_cap=5000, stock_price=100,
    )
    assert any("Free cash flow / net income" in c for c in result["callouts"])


def test_healthy_fcf_to_net_income_ratio_does_not_trigger_callout():
    result = run_valuation(
        annual_income_statements=_synthetic_annual_income_statements(),
        quarterly_income_statements=_synthetic_quarterly_income_statements(),
        annual_cash_flows=[
            # FCF = 150-30 = 120; net income 100 -> ratio 1.2, above threshold
            {"date": "2024", "operatingCashFlow": 150, "capitalExpenditure": -30, "netIncome": 100},
            {"date": "2023", "operatingCashFlow": 140, "capitalExpenditure": -30, "netIncome": 95},
            {"date": "2022", "operatingCashFlow": 130, "capitalExpenditure": -30, "netIncome": 90},
        ],
        latest_quarter_balance_sheet={
            "totalAssets": 2000, "goodwillAndIntangibleAssets": 300,
            "propertyPlantEquipmentNet": 500, "totalLiabilities": 900,
        },
        ttm_income_inputs={
            "ttm_pretax_income": 300, "annual_one_time_items": [0, 0, 0],
            "net_interest_income": 0, "ttm_tax_expense": 60,
            "reported_net_income": 240, "reported_diluted_eps": 4.0,
        },
        market_cap=5000, stock_price=100,
    )
    assert not any("Free cash flow / net income" in c for c in result["callouts"])


def _healthy_annual_cash_flows():
    # FCF/NI = 1.2 for every year -- healthy, won't trigger the annual callout
    return [
        {"date": "2024", "operatingCashFlow": 150, "capitalExpenditure": -30, "netIncome": 100},
        {"date": "2023", "operatingCashFlow": 140, "capitalExpenditure": -30, "netIncome": 95},
        {"date": "2022", "operatingCashFlow": 130, "capitalExpenditure": -30, "netIncome": 90},
    ]


def _common_valuation_kwargs(ttm_reported_net_income=240, **overrides):
    kwargs = dict(
        annual_income_statements=_synthetic_annual_income_statements(),
        quarterly_income_statements=_synthetic_quarterly_income_statements(),
        annual_cash_flows=_healthy_annual_cash_flows(),
        latest_quarter_balance_sheet={
            "totalAssets": 2000, "goodwillAndIntangibleAssets": 300,
            "propertyPlantEquipmentNet": 500, "totalLiabilities": 900,
        },
        ttm_income_inputs={
            "ttm_pretax_income": 300, "annual_one_time_items": [0, 0, 0],
            "net_interest_income": 0, "ttm_tax_expense": 60,
            "reported_net_income": ttm_reported_net_income, "reported_diluted_eps": 4.0,
        },
        market_cap=5000, stock_price=100,
    )
    kwargs.update(overrides)
    return kwargs


def test_low_ttm_fcf_to_net_income_ratio_triggers_callout():
    # TTM FCF = 200 - 150 = 50; TTM net income = 100 -> ratio 0.5, below threshold.
    # Annual figures are healthy (1.2 every year), so only the TTM callout should fire.
    result = run_valuation(
        **_common_valuation_kwargs(
            ttm_reported_net_income=100,
            ttm_operating_cash_flow=200,
            ttm_capital_expenditure=-150,
        )
    )
    assert any("trailing-twelve-month basis" in c for c in result["callouts"])
    assert not any(
        "recent fiscal year" in c and "Free cash flow" in c for c in result["callouts"]
    )


def test_healthy_ttm_fcf_to_net_income_ratio_does_not_trigger_callout():
    # TTM FCF = 200 - 40 = 160; TTM net income = 100 -> ratio 1.6, healthy.
    result = run_valuation(
        **_common_valuation_kwargs(
            ttm_reported_net_income=100,
            ttm_operating_cash_flow=200,
            ttm_capital_expenditure=-40,
        )
    )
    assert not any("trailing-twelve-month basis" in c for c in result["callouts"])


def test_ttm_check_is_skipped_when_ttm_cash_flow_not_provided():
    # No ttm_operating_cash_flow/ttm_capital_expenditure passed -> TTM check
    # is simply skipped, no error, and no TTM callout appears.
    result = run_valuation(**_common_valuation_kwargs())
    assert not any("trailing-twelve-month basis" in c for c in result["callouts"])


def test_annual_and_ttm_fcf_callouts_are_independent():
    # Annual figures are UNHEALTHY (reuse the low-ratio fixture), TTM figures
    # are HEALTHY -- confirm the annual callout fires and the TTM one does not.
    result = run_valuation(
        annual_income_statements=_synthetic_annual_income_statements(),
        quarterly_income_statements=_synthetic_quarterly_income_statements(),
        annual_cash_flows=[
            {"date": "2024", "operatingCashFlow": 150, "capitalExpenditure": -100, "netIncome": 100},
            {"date": "2023", "operatingCashFlow": 140, "capitalExpenditure": -50, "netIncome": 95},
            {"date": "2022", "operatingCashFlow": 130, "capitalExpenditure": -45, "netIncome": 90},
        ],
        latest_quarter_balance_sheet={
            "totalAssets": 2000, "goodwillAndIntangibleAssets": 300,
            "propertyPlantEquipmentNet": 500, "totalLiabilities": 900,
        },
        ttm_income_inputs={
            "ttm_pretax_income": 300, "annual_one_time_items": [0, 0, 0],
            "net_interest_income": 0, "ttm_tax_expense": 60,
            "reported_net_income": 100, "reported_diluted_eps": 4.0,
        },
        market_cap=5000, stock_price=100,
        ttm_operating_cash_flow=200,
        ttm_capital_expenditure=-40,  # TTM FCF=160, ratio=1.6, healthy
    )
    assert any(
        "recent fiscal year" in c and "Free cash flow" in c for c in result["callouts"]
    )
    assert not any("trailing-twelve-month basis" in c for c in result["callouts"])
