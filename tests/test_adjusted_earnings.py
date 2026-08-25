from stock_agent.valuation.adjusted_earnings import (
    AdjustedEarningsInputs,
    calculate_adjusted_earnings,
    resolve_one_time_item_adjustment,
)


# --- resolve_one_time_item_adjustment: the recurrence-detection logic itself ---

def test_single_occurrence_is_treated_as_genuinely_one_time():
    # Nonzero in only the most recent year -> use that year's actual value
    adjustment, is_recurring = resolve_one_time_item_adjustment([200, 0, 0, 0, 0])
    assert adjustment == 200
    assert is_recurring is False


def test_zero_occurrences_is_not_recurring():
    adjustment, is_recurring = resolve_one_time_item_adjustment([0, 0, 0, 0, 0])
    assert adjustment == 0
    assert is_recurring is False


def test_multiple_occurrences_is_treated_as_recurring_and_averaged():
    # Nonzero in 3 of the last 5 years -> recurring, use the average of
    # just those 3 occurrences (not diluted by the 2 zero years)
    adjustment, is_recurring = resolve_one_time_item_adjustment([300, 0, 200, 100, 0])
    assert is_recurring is True
    assert adjustment == 200  # (300 + 200 + 100) / 3


def test_two_occurrences_is_enough_to_count_as_recurring():
    adjustment, is_recurring = resolve_one_time_item_adjustment([150, 0, 0, 0, 50])
    assert is_recurring is True
    assert adjustment == 100  # (150 + 50) / 2


def test_mixed_sign_occurrences_average_correctly():
    # One year a gain, another year a loss -- still "recurring" if it shows
    # up more than once, and the average nets them against each other
    adjustment, is_recurring = resolve_one_time_item_adjustment([100, 0, -40, 0, 0])
    assert is_recurring is True
    assert adjustment == 30  # (100 + -40) / 2


def test_empty_list_defaults_to_zero_not_recurring():
    adjustment, is_recurring = resolve_one_time_item_adjustment([])
    assert adjustment == 0.0
    assert is_recurring is False


def test_single_element_list_treated_as_one_time_ttm_value():
    # Fallback case: only the TTM figure is available, no historical breakdown
    adjustment, is_recurring = resolve_one_time_item_adjustment([75])
    assert adjustment == 75
    assert is_recurring is False


# --- calculate_adjusted_earnings: full pipeline, including recurrence detection ---

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
    assert result.tax_rate_applied == 0.25
    assert result.adjusted_net_income == 750  # 1000 * (1 - 0.25)


def test_genuine_one_time_income_is_fully_stripped_out():
    # Gain appears in only 1 of the last 5 years -> use the full TTM value
    result = calculate_adjusted_earnings(AdjustedEarningsInputs(
        ttm_pretax_income=1200,  # includes a 200 one-time gain
        annual_one_time_items=[200, 0, 0, 0, 0],
        net_interest_income=0,
        ttm_tax_expense=240,  # 20% of the reported 1200
        reported_net_income=960,
        reported_diluted_eps=3.0,
    ))
    assert result.one_time_item_is_recurring is False
    assert result.one_time_item_adjustment == 200
    assert result.adjusted_pretax_income == 1000


def test_recurring_item_uses_average_not_full_ttm_value():
    # Same 200 TTM gain, but it also showed up in 2 other years -> treated
    # as recurring, so only the average of the occurrences (150, not 200)
    # gets stripped out of pretax income.
    result = calculate_adjusted_earnings(AdjustedEarningsInputs(
        ttm_pretax_income=1200,
        annual_one_time_items=[200, 0, 150, 100, 0],  # nonzero in 3 of 5 years
        net_interest_income=0,
        ttm_tax_expense=240,
        reported_net_income=960,
        reported_diluted_eps=3.0,
    ))
    assert result.one_time_item_is_recurring is True
    assert result.one_time_item_adjustment == 150  # (200+150+100)/3
    assert result.adjusted_pretax_income == 1050  # 1200 - 150


def test_net_interest_expense_is_added_back():
    result = calculate_adjusted_earnings(AdjustedEarningsInputs(
        ttm_pretax_income=1000,
        annual_one_time_items=[0],
        net_interest_income=-50,  # net interest EXPENSE of 50
        ttm_tax_expense=200,
        reported_net_income=800,
        reported_diluted_eps=2.0,
    ))
    assert result.adjusted_pretax_income == 1050


def test_adjustment_ratio_scales_eps():
    result = calculate_adjusted_earnings(AdjustedEarningsInputs(
        ttm_pretax_income=1000,
        annual_one_time_items=[0],
        net_interest_income=0,
        ttm_tax_expense=100,
        reported_net_income=900,
        reported_diluted_eps=3.0,
    ))
    # adjusted_net_income=800, reported_net_income=900 -> ratio = 0.8889
    assert round(result.adjustment_ratio, 4) == round(800 / 900, 4)
    assert round(result.adjusted_eps, 4) == round(3.0 * (800 / 900), 4)
