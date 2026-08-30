from stock_agent.valuation.multiples import (
    calculate_blended_growth_rate,
    calculate_multiples,
    calculate_price_scenarios,
    calculate_real_assets,
    calculate_real_liabilities_per_share,
)


# --- Blended growth rate ---

def test_blended_growth_rate_accelerating_quarter_averages():
    # quarterly (20) > annual (10) -> simple average
    blended = calculate_blended_growth_rate(
        annual_growth_rate=10, quarterly_growth_rate=20, quarterly_revenue_growth_rate=100
    )
    assert blended == 15  # (20+10)/2


def test_blended_growth_rate_decelerating_quarter_extrapolates_further_down():
    # quarterly (5) <= annual (10) -> 2*quarterly - annual, not a simple average
    blended = calculate_blended_growth_rate(
        annual_growth_rate=10, quarterly_growth_rate=5, quarterly_revenue_growth_rate=100
    )
    assert blended == 0  # 5 - (10-5) = 0, vs. a naive average of 7.5


def test_blended_growth_rate_equal_quarter_and_annual_uses_deceleration_branch():
    # quarterly == annual falls into the "else" branch per the spec (only
    # strictly-greater triggers the average branch)
    blended = calculate_blended_growth_rate(
        annual_growth_rate=10, quarterly_growth_rate=10, quarterly_revenue_growth_rate=100
    )
    assert blended == 10  # 10 - (10-10) = 10


def test_blended_growth_rate_capped_at_3x_quarterly_revenue_growth():
    # Uncapped blended would be (50+10)/2 = 30, but 3x revenue growth (2%) = 6
    blended = calculate_blended_growth_rate(
        annual_growth_rate=10, quarterly_growth_rate=50, quarterly_revenue_growth_rate=2
    )
    assert blended == 6  # capped at 3*2


def test_blended_growth_rate_not_capped_when_within_bounds():
    blended = calculate_blended_growth_rate(
        annual_growth_rate=10, quarterly_growth_rate=20, quarterly_revenue_growth_rate=100
    )
    assert blended == 15  # well under 3*100=300, cap doesn't bind


def test_blended_growth_rate_handles_negative_revenue_growth_cap():
    # If revenue growth is negative, 3x it is a low (negative) cap -- a
    # blended rate above that gets pulled down to the cap.
    blended = calculate_blended_growth_rate(
        annual_growth_rate=10, quarterly_growth_rate=20, quarterly_revenue_growth_rate=-2
    )
    assert blended == -6  # 3 * -2, since 15 > -6


# --- calculate_multiples (now includes blended) ---

def test_calculate_multiples_includes_blended():
    result = calculate_multiples(
        annual_growth_rate=10, quarterly_growth_rate=20, quarterly_revenue_growth_rate=100
    )
    assert result["annual_aggressive"] == 20
    assert result["annual_conservative"] == 18
    assert result["quarter_aggressive"] == 30
    assert result["quarter_conservative"] == 28
    assert result["blended_growth_rate"] == 15
    assert result["blended_aggressive"] == 25
    assert result["blended_conservative"] == 23


# --- Balance sheet / real assets calculations (unchanged) ---

def test_calculate_real_assets():
    real_assets = calculate_real_assets(total_assets=1000, intangibles_and_goodwill=200, ppe=400)
    assert real_assets == 600  # 1000 - 200 - 0.5*400


def test_real_liabilities_per_share():
    per_share = calculate_real_liabilities_per_share(
        net_liabilities=-500, market_cap=10000, stock_price=50
    )
    assert per_share == -2.5  # (-500/10000) * 50


def test_price_scenarios_includes_blended():
    multiples = {
        "annual_aggressive": 25, "annual_conservative": 23,
        "quarter_aggressive": 20, "quarter_conservative": 18,
        "blended_aggressive": 22, "blended_conservative": 20,
    }
    result = calculate_price_scenarios(multiples, adjusted_eps=2.0, real_liabilities_per_share=1.0)
    assert result.annual_aggressive == 51.0    # 25*2 + 1
    assert result.annual_conservative == 47.0   # 23*2 + 1
    assert result.quarter_aggressive == 41.0    # 20*2 + 1
    assert result.quarter_conservative == 37.0  # 18*2 + 1
    assert result.blended_aggressive == 45.0    # 22*2 + 1
    assert result.blended_conservative == 41.0  # 20*2 + 1


def test_real_liabilities_adjustment_applied_only_once_per_scenario():
    # Regression test for a fixed bug: the balance-sheet adjustment must
    # appear exactly once in each price scenario, not be added again
    # elsewhere. Confirm the adjustment shows up as a pure additive offset
    # equal to real_liabilities_per_share, nothing more.
    multiples = {
        "annual_aggressive": 20, "annual_conservative": 18,
        "quarter_aggressive": 15, "quarter_conservative": 13,
        "blended_aggressive": 17, "blended_conservative": 15,
    }
    without_adjustment = calculate_price_scenarios(multiples, adjusted_eps=3.0, real_liabilities_per_share=0.0)
    with_adjustment = calculate_price_scenarios(multiples, adjusted_eps=3.0, real_liabilities_per_share=5.0)

    assert with_adjustment.annual_aggressive - without_adjustment.annual_aggressive == 5.0
    assert with_adjustment.blended_conservative - without_adjustment.blended_conservative == 5.0
