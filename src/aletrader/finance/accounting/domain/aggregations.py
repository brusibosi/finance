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


def calculate_realized_pnl_from_transaction_history(
    transactions: Sequence[LedgerTransactionLike],
) -> Decimal:
    """
    Calculate cumulative realized P&L from transaction history using FIFO cost basis.

    This derives realized P&L from raw transaction data (qty, price, commission, fees, taxes)
    without relying on stored realized_pnl_delta field (balance sheet approach).

    Realized P&L only occurs on position exits (SELL/SL/TP).
    Uses FIFO (First In, First Out) to track cost basis per symbol.

    Formula per exit:
        realized_pnl_delta = exit_proceeds - exit_cost
        exit_proceeds = (qty * price * fx) - commission - fees - taxes
        exit_cost = qty * avg_cost_per_share

    Args:
        transactions: All ledger transactions (must have symbol, side, type, qty, price, 
                     commission, fees, taxes, fx attributes)

    Returns:
        Cumulative realized P&L across all exits

    Raises:
        ValueError: If transaction sequence is invalid
    """
    _ensure_sequence(transactions, "transactions")

    # Track cost basis per symbol using FIFO
    # symbol -> list of (qty, total_cost) lots
    cost_basis_by_symbol: dict[str, list[tuple[Decimal, Decimal]]] = {}
    
    realized_pnl_cum = Decimal("0")

    for tx in transactions:
        symbol = tx.symbol
        qty = Decimal(str(tx.qty))
        price = Decimal(str(tx.price))
        commission = Decimal(str(tx.commission)) if tx.commission is not None else Decimal("0")
        fees = Decimal(str(tx.fees)) if tx.fees is not None else Decimal("0")
        taxes = Decimal(str(tx.taxes)) if tx.taxes is not None else Decimal("0")
        fx = Decimal(str(tx.fx)) if hasattr(tx, 'fx') and tx.fx is not None else Decimal("1.0")
        
        costs = commission + fees + taxes

        if tx.side == "BUY":
            # Add to cost basis (FIFO queue)
            total_cost = (qty * price * fx) + costs
            
            if symbol not in cost_basis_by_symbol:
                cost_basis_by_symbol[symbol] = []
            
            cost_basis_by_symbol[symbol].append((qty, total_cost))

        elif tx.side == "SELL":
            # Exit: calculate realized P&L using FIFO
            if symbol not in cost_basis_by_symbol or not cost_basis_by_symbol[symbol]:
                # No cost basis available - this shouldn't happen in correct data
                # Skip this exit (realized P&L = 0 for this transaction)
                continue
            
            exit_proceeds = (qty * price * fx) - costs
            
            # Calculate cost from FIFO lots
            remaining_to_exit = qty
            exit_cost = Decimal("0")
            
            while remaining_to_exit > 0 and cost_basis_by_symbol[symbol]:
                lot_qty, lot_cost = cost_basis_by_symbol[symbol][0]
                avg_cost_per_share = lot_cost / lot_qty
                
                if lot_qty <= remaining_to_exit:
                    # Use entire lot
                    exit_cost += lot_cost
                    remaining_to_exit -= lot_qty
                    cost_basis_by_symbol[symbol].pop(0)
                else:
                    # Use partial lot
                    exit_cost += remaining_to_exit * avg_cost_per_share
                    new_lot_qty = lot_qty - remaining_to_exit
                    new_lot_cost = new_lot_qty * avg_cost_per_share
                    cost_basis_by_symbol[symbol][0] = (new_lot_qty, new_lot_cost)
                    remaining_to_exit = Decimal("0")
            
            realized_pnl_delta = exit_proceeds - exit_cost
            realized_pnl_cum += realized_pnl_delta

    return realized_pnl_cum


