"""Implements the adjusted-earnings waterfall from the spec:

1. Start from TTM pretax income.
2. Strip one-time items (gains/losses on sale, other non-operating items) --
   BUT first check whether the item is genuinely one-time. If the same line
   item (e.g. "other income" or "gain on sale of securities") shows up as
   nonzero in more than one of the last 5 fiscal years, it isn't really
   one-time -- use the average of the years it occurred instead of the raw
   TTM figure, so a single unusually large or small year doesn't distort
   the adjustment.
3. Remove net interest income, or add back net interest expense.
4. Apply a bracketed tax rate: floor at 20% if the effective rate is lower,
   use the actual rate between 20-25%, and cap at 25% if higher.
5. Compute the adjustment ratio (adjusted / reported net income).
6. Apply that ratio to reported diluted EPS to get adjusted EPS.
"""
from __future__ import annotations

from dataclasses import dataclass, field


def resolve_one_time_item_adjustment(annual_one_time_items: list[float]) -> tuple[float, bool]:
    """Decide whether the 'one-time' item is genuinely one-time or recurring,
    and return the value to subtract from pretax income.

    annual_one_time_items: the line item's value for each of the last up to
    5 fiscal years, ordered MOST RECENT FIRST (index 0 = TTM/most recent
    year). Positive = income, negative = expense.

    Rule: if the item is nonzero in more than one of those years, it's
    treated as recurring -- the adjustment used is the average of the years
    in which it occurred (not diluted by zero years), rather than just the
    most recent year's figure. If it's nonzero in zero or one year, it's
    treated as genuinely one-time and the most recent year's actual value
    is used.

    Returns (adjustment_value, is_recurring).
    """
    if not annual_one_time_items:
        return 0.0, False

    nonzero_years = [v for v in annual_one_time_items if v != 0]

    if len(nonzero_years) > 1:
        # Recurring -- smooth it by averaging the years it actually occurred.
        adjustment = sum(nonzero_years) / len(nonzero_years)
        return adjustment, True

    # Zero or one occurrence in the lookback window -- genuinely one-time.
    # Use the most recent year's (TTM) actual value, which may be 0.
    return annual_one_time_items[0], False


@dataclass
class AdjustedEarningsInputs:
    ttm_pretax_income: float
    # Most-recent-first, up to 5 years of the "other income / gain on sale
    # of securities" style line item. A single-element list (just the TTM
    # value) is fine if you don't have the historical breakdown handy, but
    # you lose the recurring-item detection this whole function exists for.
    annual_one_time_items: list[float] = field(default_factory=list)
    net_interest_income: float = 0.0    # positive if net interest income, negative if net interest expense
    ttm_tax_expense: float = 0.0
    reported_net_income: float = 0.0
    reported_diluted_eps: float = 0.0


@dataclass
class AdjustedEarningsResult:
    one_time_item_adjustment: float
    one_time_item_is_recurring: bool
    adjusted_pretax_income: float
    effective_tax_rate: float
    tax_rate_applied: float
    adjusted_net_income: float
    adjustment_ratio: float
    adjusted_eps: float


def calculate_adjusted_earnings(i: AdjustedEarningsInputs) -> AdjustedEarningsResult:
    one_time_adjustment, is_recurring = resolve_one_time_item_adjustment(i.annual_one_time_items)

    adjusted_pretax = i.ttm_pretax_income - one_time_adjustment

    if i.net_interest_income > 0:
        adjusted_pretax -= i.net_interest_income
    else:
        adjusted_pretax += abs(i.net_interest_income)

    effective_tax_rate = (
        i.ttm_tax_expense / i.ttm_pretax_income if i.ttm_pretax_income else 0.0
    )

    if effective_tax_rate < 0.20:
        tax_rate_applied = 0.20
    elif effective_tax_rate <= 0.25:
        tax_rate_applied = effective_tax_rate
    else:
        tax_rate_applied = 0.25

    adjusted_net_income = adjusted_pretax * (1 - tax_rate_applied)

    adjustment_ratio = (
        adjusted_net_income / i.reported_net_income if i.reported_net_income else 0.0
    )
    adjusted_eps = i.reported_diluted_eps * adjustment_ratio

    return AdjustedEarningsResult(
        one_time_item_adjustment=one_time_adjustment,
        one_time_item_is_recurring=is_recurring,
        adjusted_pretax_income=adjusted_pretax,
        effective_tax_rate=effective_tax_rate,
        tax_rate_applied=tax_rate_applied,
        adjusted_net_income=adjusted_net_income,
        adjustment_ratio=adjustment_ratio,
        adjusted_eps=adjusted_eps,
    )
