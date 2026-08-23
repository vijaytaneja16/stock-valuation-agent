from stock_agent.valuation.adjusted_earnings import (
    AdjustedEarningsInputs,
    calculate_adjusted_earnings,
)


def test_low_tax_rate_floors_at_20_percent():
    result = calculate_adjusted_earnings(AdjustedEarningsInputs(
        ttm_pretax_income=1000,
        one_time_items=0,
        net_interest_income=0,
        ttm_tax_expense=100,  # 10% effective rate
        reported_net_income=900,
        reported_diluted_eps=2.0,
    ))
    assert result.tax_rate_applied == 0.20
    assert result.adjusted_net_income == 800  # 1000 * (1 - 0.20)


def test_mid_tax_rate_uses_actual_rate():
    result = calculate_adjusted_earnings(AdjustedEarningsInputs(
        ttm_pretax_income=1000,
        one_time_items=0,
        net_interest_income=0,
        ttm_tax_expense=220,  # 22% effective rate
        reported_net_income=780,
        reported_diluted_eps=2.0,
    ))
    assert result.tax_rate_applied == 0.22
    assert round(result.adjusted_net_income, 2) == 780.0


def test_high_tax_rate_caps_at_25_percent():
    result = calculate_adjusted_earnings(AdjustedEarningsInputs(
        ttm_pretax_income=1000,
        one_time_items=0,
        net_interest_income=0,
        ttm_tax_expense=300,  # 30% effective rate
        reported_net_income=700,
        reported_diluted_eps=2.0,
    ))
    assert result.tax_rate_applied == 0.25
    assert result.adjusted_net_income == 750  # 1000 * (1 - 0.25)


def test_one_time_income_is_stripped_out():
    result = calculate_adjusted_earnings(AdjustedEarningsInputs(
        ttm_pretax_income=1200,  # includes a 200 one-time gain
        one_time_items=200,
        net_interest_income=0,
        ttm_tax_expense=240,  # 20% of the reported 1200
        reported_net_income=960,
        reported_diluted_eps=3.0,
    ))
    assert result.adjusted_pretax_income == 1000


def test_net_interest_expense_is_added_back():
    result = calculate_adjusted_earnings(AdjustedEarningsInputs(
        ttm_pretax_income=1000,
        one_time_items=0,
        net_interest_income=-50,  # net interest EXPENSE of 50
        ttm_tax_expense=200,
        reported_net_income=800,
        reported_diluted_eps=2.0,
    ))
    assert result.adjusted_pretax_income == 1050


def test_adjustment_ratio_scales_eps():
    result = calculate_adjusted_earnings(AdjustedEarningsInputs(
        ttm_pretax_income=1000,
        one_time_items=0,
        net_interest_income=0,
        ttm_tax_expense=100,
        reported_net_income=900,
        reported_diluted_eps=3.0,
    ))
    # adjusted_net_income=800, reported_net_income=900 -> ratio = 0.8889
    assert round(result.adjustment_ratio, 4) == round(800 / 900, 4)
    assert round(result.adjusted_eps, 4) == round(3.0 * (800 / 900), 4)
