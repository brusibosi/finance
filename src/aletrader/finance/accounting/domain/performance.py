"""
Strategy performance calculation helpers.

Pure domain logic for aggregating performance metrics.
"""

from decimal import Decimal
from typing import Any, Sequence

from aletrader.finance.accounting.interfaces import StrategyPerformanceLike


def calculate_rate(numerator: int, denominator: int) -> Decimal | None:
    """
    Calculate percentage rate (0-100).

    Returns None when denominator is zero or negative.
    """
    if denominator <= 0:
        return None
    return (Decimal(numerator) / Decimal(denominator)) * Decimal("100")


def calculate_strategy_totals(
    strategies: Sequence[StrategyPerformanceLike],
) -> dict[str, Any]:
    """
    Aggregate totals across strategy performance records.
    """
    totals: dict[str, Any] = {
        "signals_generated": 0,
        "signals_approved": 0,
        "signals_rejected": 0,
        "total_trades": 0,
        "winning_trades": 0,
        "losing_trades": 0,
        "total_pnl": Decimal("0"),
        "win_rate": Decimal("0"),
    }

    for strategy in strategies:
        totals["signals_generated"] += strategy.signals_generated
        totals["signals_approved"] += strategy.signals_approved
        totals["signals_rejected"] += strategy.signals_rejected
        totals["winning_trades"] += strategy.winning_trades
        totals["losing_trades"] += strategy.losing_trades
        totals["total_pnl"] += strategy.realized_pnl

    totals["total_trades"] = totals["winning_trades"] + totals["losing_trades"]
    if totals["total_trades"] > 0:
        totals["win_rate"] = (
            Decimal(totals["winning_trades"])
            / Decimal(totals["total_trades"])
            * Decimal("100")
        )

    return totals


def apply_exit_metrics(
    *,
    realized_pnl: Decimal,
    total_pnl: Decimal,
    total_commission: Decimal,
    winning_trades: int,
    losing_trades: int,
    pnl: Decimal,
    commission: Decimal,
) -> dict[str, Decimal | int]:
    """
    Apply exit updates to cumulative performance metrics.
    """
    updated_realized = realized_pnl + pnl
    updated_total = total_pnl + pnl
    updated_commission = total_commission + commission

    if pnl > Decimal("0"):
        winning_trades += 1
    elif pnl < Decimal("0"):
        losing_trades += 1

    return {
        "realized_pnl": updated_realized,
        "total_pnl": updated_total,
        "total_commission": updated_commission,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
    }


def calculate_total_trades(
    winning_trades: int,
    losing_trades: int,
) -> int:
    """Calculate total trades from wins and losses."""
    return winning_trades + losing_trades
