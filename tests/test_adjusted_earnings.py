from stock_agent.valuation.adjusted_earnings import (
    AdjustedEarningsInputs,
    calculate_adjusted_earnings,
    resolve_one_time_item_adjustment,
)


# --- resolve_one_time_item_adjustment: strip TTM value, always add back the average ---

def test_single_occurrence_still_gets_averaged_across_full_window():
    # Nonzero in only the most recent year -> TTM value is still stripped,
    # and the average (across all 5 years, zeros included) is still added
    # back -- even though it only happened once.
    ttm_value, average = resolve_one_time_item_adjustment([200, 0, 0, 0, 0])
    assert ttm_value == 200
    assert average == 40  # (200+0+0+0+0) / 5


def test_zero_occurrences_gives_zero_both_ways():
    ttm_value, average = resolve_one_time_item_adjustment([0, 0, 0, 0, 0])
    assert ttm_value == 0
    assert average == 0


def test_multiple_occurrences_averages_across_full_window():
    ttm_value, average = resolve_one_time_item_adjustment([300, 0, 200, 100, 0])
    assert ttm_value == 300
    assert average == 120  # (300+0+200+100+0) / 5


def test_mixed_sign_occurrences_average_correctly():
    ttm_value, average = resolve_one_time_item_adjustment([100, 0, -40, 0, 0])
    assert ttm_value == 100
    assert average == 12  # (100+0-40+0+0) / 5


def test_empty_list_defaults_to_zero():
    ttm_value, average = resolve_one_time_item_adjustment([])
    assert ttm_value == 0.0
    assert average == 0.0


def test_single_element_list_averages_over_itself():
    # Fallback case: only the TTM figure is available, no historical
    # breakdown -- averaging over a 1-year window just returns that value,
    # so the strip and add-back cancel out (net zero adjustment).
    ttm_value, average = resolve_one_time_item_adjustment([75])
    assert ttm_value == 75
    assert average == 75


# --- calculate_adjusted_earnings: full pipeline ---

def test_low_tax_rate_floors_at_20_percent():
    result = calculate_adjusted_earnings(AdjustedEarningsInputs(
        ttm_pretax_income=1000,
        annual_one_time_items=[0],
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
        annual_one_time_items=[0],
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
        annual_one_time_items=[0],
        net_interest_income=0,
        ttm_tax_expense=300,  # 30% effective rate
        reported_net_income=700,
        reported_diluted_eps=2.0,
    ))
    assert result.tax_rate_applied == 0.30
    assert result.adjusted_net_income == 700  # 1000 * (1 - 0.30)


def test_one_time_item_occurring_once_still_gets_normalized_to_average():
    # Even though the gain appears in only 1 of 5 years, it's still
    # stripped at its full TTM value and replaced with the 5-year average
    # (40, not 0) -- per the "always add back the average" rule.
    result = calculate_adjusted_earnings(AdjustedEarningsInputs(
        ttm_pretax_income=1200,  # includes a 200 one-time gain
        annual_one_time_items=[200, 0, 0, 0, 0],
        net_interest_income=0,
        ttm_tax_expense=240,  # 20% of the reported 1200
        reported_net_income=960,
        reported_diluted_eps=3.0,
    ))
    assert result.one_time_item_ttm_value_stripped == 200
    assert result.one_time_item_average_added_back == 40  # (200+0+0+0+0)/5
    assert result.adjusted_pretax_income == 1040  # 1200 - 200 + 40


def test_item_occurring_multiple_times_strips_ttm_then_adds_back_average():
    # TTM actual is 200, also showed up in a second year (150). Strip the
    # full TTM value (200) first, then add back the 5-year average (70).
    result = calculate_adjusted_earnings(AdjustedEarningsInputs(
        ttm_pretax_income=1200,
        annual_one_time_items=[200, 0, 150, 0, 0],
        net_interest_income=0,
        ttm_tax_expense=240,
        reported_net_income=960,
        reported_diluted_eps=3.0,
    ))
    assert result.one_time_item_ttm_value_stripped == 200
    assert result.one_time_item_average_added_back == 70  # (200+0+150+0+0)/5
    assert result.adjusted_pretax_income == 1070  # 1200 - 200 + 70


def test_ttm_value_below_average_increases_adjusted_pretax():
    # This year's actual one-time item (50) is smaller than its historical
    # average (110) -- the correction should ADD to pretax income overall,
    # since the TTM figure understates the item's normal contribution.
    result = calculate_adjusted_earnings(AdjustedEarningsInputs(
        ttm_pretax_income=1000,
        annual_one_time_items=[50, 200, 100, 200, 0],
        net_interest_income=0,
        ttm_tax_expense=200,
        reported_net_income=800,
        reported_diluted_eps=2.0,
    ))
    assert result.one_time_item_ttm_value_stripped == 50
    assert result.one_time_item_average_added_back == 110  # (50+200+100+200+0)/5
    assert result.adjusted_pretax_income == 1060  # 1000 - 50 + 110


def test_net_interest_expense_is_added_back():
    result = calculate_adjusted_earnings(AdjustedEarningsInputs(
        ttm_pretax_income=1000,
        annual_one_time_items=[0],
        net_interest_income=-50,  # net interest EXPENSE of 50
        ttm_tax_expense=200,
        reported_net_income=800,
        reported_diluted_eps=2.0,
    ))
    assert result.adjusted_pretax_income == 1000


def test_adjustment_ratio_scales_eps():
    result = calculate_adjusted_earnings(AdjustedEarningsInputs(
        ttm_pretax_income=1000,
        annual_one_time_items=[0],
        net_interest_income=0,
        ttm_tax_expense=100,
        reported_net_income=900,
        reported_diluted_eps=3.0,
    ))
    assert round(result.adjustment_ratio, 4) == round(800 / 900, 4)
    assert round(result.adjusted_eps, 4) == round(3.0 * (800 / 900), 4)
