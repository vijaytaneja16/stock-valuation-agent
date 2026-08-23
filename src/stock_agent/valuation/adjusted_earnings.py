"""Implements the adjusted-earnings waterfall from the spec:

1. Start from TTM pretax income.
2. Strip one-time items (gains/losses on sale, other non-operating items).
3. Remove net interest income, or add back net interest expense.
4. Apply a bracketed tax rate: floor at 20% if the effective rate is lower,
   use the actual rate between 20-25%, and cap at 25% if higher.
5. Compute the adjustment ratio (adjusted / reported net income).
6. Apply that ratio to reported diluted EPS to get adjusted EPS.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AdjustedEarningsInputs:
    ttm_pretax_income: float
    one_time_items: float          # positive = income to remove, negative = expense to remove
    net_interest_income: float     # positive if net interest income, negative if net interest expense
    ttm_tax_expense: float
    reported_net_income: float
    reported_diluted_eps: float


@dataclass
class AdjustedEarningsResult:
    adjusted_pretax_income: float
    effective_tax_rate: float
    tax_rate_applied: float
    adjusted_net_income: float
    adjustment_ratio: float
    adjusted_eps: float


def calculate_adjusted_earnings(i: AdjustedEarningsInputs) -> AdjustedEarningsResult:
    adjusted_pretax = i.ttm_pretax_income - i.one_time_items

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
        adjusted_pretax_income=adjusted_pretax,
        effective_tax_rate=effective_tax_rate,
        tax_rate_applied=tax_rate_applied,
        adjusted_net_income=adjusted_net_income,
        adjustment_ratio=adjustment_ratio,
        adjusted_eps=adjusted_eps,
    )
