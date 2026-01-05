"""
Aggregation helpers for accounting summaries.
"""

from decimal import Decimal
from typing import Sequence

from aletrader.finance.accounting.interfaces import (
    ApprovedOrderLike,
    LedgerTransactionLike,
    PositionStateLike,
)


def _ensure_sequence(value: Sequence[object], name: str) -> None:
    """Validate that a value is a non-None sequence."""
    if value is None:
        raise ValueError(f"{name} must not be None")


def aggregate_unrealized_pnl(
    positions: Sequence[PositionStateLike],
) -> Decimal:
    """
    Aggregate unrealized P&L across all positions.

    Args:
        positions: List of position states

    Returns:
        Total unrealized P&L
    """
    _ensure_sequence(positions, "positions")
    total = Decimal("0")
    for pos in positions:
        total += pos.unrealized_pnl
    return total


def aggregate_positions_value(
    positions: Sequence[PositionStateLike],
) -> Decimal:
    """
    Aggregate total positions market value.

    Args:
        positions: List of position states

    Returns:
        Total positions value (sum of notional values)
    """
    _ensure_sequence(positions, "positions")
    total = Decimal("0")
    for pos in positions:
        total += pos.notional
    return total


def aggregate_positions_cost(
    positions: Sequence[PositionStateLike],
) -> Decimal:
    """
    Aggregate total positions cost basis.

    Formula: sum(qty * avg_cost) for all positions.
    """
    _ensure_sequence(positions, "positions")
    total = Decimal("0")
    for pos in positions:
        total += pos.qty * pos.avg_cost
    return total


def aggregate_order_risk(
    orders: Sequence[ApprovedOrderLike],
) -> tuple[Decimal, Decimal]:
    """
    Aggregate total risk amount and quantity from approved orders.

    Args:
        orders: List of approved orders

    Returns:
        Tuple of (total_risk, total_quantity)
    """
    _ensure_sequence(orders, "orders")
    total_risk = Decimal("0")
    total_quantity = Decimal("0")
    for order in orders:
        if order.risk_amount:
            total_risk += Decimal(str(order.risk_amount))
        if order.final_quantity > 0:
            total_quantity += Decimal(str(order.final_quantity))
    return (total_risk, total_quantity)


def aggregate_strategy_metrics(
    orders: Sequence[ApprovedOrderLike],
) -> dict[str, dict[str, int | Decimal]]:
    """
    Aggregate metrics by strategy.

    Args:
        orders: List of approved orders

    Returns:
        Dictionary mapping strategy_id to metrics.
    """
    _ensure_sequence(orders, "orders")
    strategies: dict[str, dict[str, int | Decimal]] = {}
    for order in orders:
        strategy_id = order.strategy_id
        if strategy_id not in strategies:
            strategies[strategy_id] = {
                "count": 0,
                "risk": Decimal("0"),
                "quantity": Decimal("0"),
            }
        strategies[strategy_id]["count"] = int(strategies[strategy_id]["count"]) + 1
        if order.risk_amount is not None:
            strategies[strategy_id]["risk"] = (
                strategies[strategy_id]["risk"] + Decimal(str(order.risk_amount))
            )
        if order.final_quantity and order.final_quantity > 0:
            strategies[strategy_id]["quantity"] = (
                strategies[strategy_id]["quantity"] + Decimal(str(order.final_quantity))
            )
    return strategies


def calculate_average_metrics(
    values: Sequence[Decimal | float | None],
) -> Decimal | None:
    """
    Calculate average of numeric values, handling None values.

    Args:
        values: List of numeric values (may contain None)

    Returns:
        Average value, or None if all values are None
    """
    _ensure_sequence(values, "values")
    filtered = [value for value in values if value is not None]
    if not filtered:
        return None
    total = sum(Decimal(str(value)) for value in filtered)
    return total / Decimal(len(filtered))


def calculate_realized_pnl_cum_corrected(
    transactions: Sequence[LedgerTransactionLike],
) -> Decimal:
    """
    Calculate corrected realized P&L cumulative value.

    Old BUY transactions may have realized_pnl_delta as 0/NULL; in that case
    subtract commission/fees/taxes to enforce P&L consistency.
    """
    _ensure_sequence(transactions, "transactions")
    total_realized = Decimal("0")
    total_cost_adjustment = Decimal("0")

    for tx in transactions:
        realized = Decimal(str(tx.realized_pnl_delta)) if tx.realized_pnl_delta is not None else Decimal("0")
        total_realized += realized

        if tx.side == "BUY" and (tx.realized_pnl_delta is None or abs(realized) < Decimal("0.0001")):
            commission = Decimal(str(tx.commission)) if tx.commission is not None else Decimal("0")
            fees = Decimal(str(tx.fees)) if tx.fees is not None else Decimal("0")
            taxes = Decimal(str(tx.taxes)) if tx.taxes is not None else Decimal("0")
            total_cost_adjustment += commission + fees + taxes

    return total_realized - total_cost_adjustment
