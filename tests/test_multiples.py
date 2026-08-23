from stock_agent.valuation.multiples import (
    calculate_multiples,
    calculate_net_real_assets_adjustment,
    calculate_price_scenarios,
    calculate_real_assets,
    calculate_real_liabilities_per_share,
)


def test_calculate_multiples():
    result = calculate_multiples(annual_growth_rate=15, quarterly_growth_rate=10)
    assert result["annual_aggressive"] == 25
    assert result["annual_conservative"] == 23
    assert result["quarter_aggressive"] == 20
    assert result["quarter_conservative"] == 18


def test_calculate_real_assets():
    real_assets = calculate_real_assets(total_assets=1000, intangibles_and_goodwill=200, ppe=400)
    assert real_assets == 600  # 1000 - 200 - 0.5*400


def test_real_liabilities_per_share():
    per_share = calculate_real_liabilities_per_share(
        net_liabilities=-500, market_cap=10000, stock_price=50
    )
    assert per_share == -2.5  # (-500/10000) * 50


def test_price_scenarios():
    multiples = {
        "annual_aggressive": 25, "annual_conservative": 23,
        "quarter_aggressive": 20, "quarter_conservative": 18,
    }
    result = calculate_price_scenarios(multiples, adjusted_eps=2.0, real_liabilities_per_share=1.0)
    assert result.annual_aggressive == 51.0   # 25*2 + 1
    assert result.annual_conservative == 47.0  # 23*2 + 1
    assert result.quarter_aggressive == 41.0   # 20*2 + 1
    assert result.quarter_conservative == 37.0  # 18*2 + 1


def test_net_real_assets_adjustment():
    result = calculate_net_real_assets_adjustment(
        total_assets=1000, intangibles_and_goodwill=100, ppe=200,
        total_liabilities=500, market_cap=5000, stock_price=25,
    )
    # net_real_assets = 1000 - 100 - 100 - 500 = 300
    assert result["net_real_assets"] == 300
    assert result["pct_of_market_cap"] == 0.06
    assert result["per_share_value"] == 1.5
