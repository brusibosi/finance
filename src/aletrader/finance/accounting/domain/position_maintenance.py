"""
Position maintenance helpers.

Pure functions for recalculating position metrics from transaction history.
"""

from decimal import Decimal
from typing import Sequence

from aletrader.finance.accounting.interfaces import AvgCostTransactionLike


def calculate_avg_cost_from_transactions(
    transactions: Sequence[AvgCostTransactionLike],
) -> Decimal | None:
    """
    Recalculate average cost from transaction history.

    Returns None if the position is closed or no transactions exist.
    """
    if not transactions:
        return None

    total_cost = Decimal("0")
    total_qty = Decimal("0")

    for tx in transactions:
        if tx.side == "BUY":
            gross_value = tx.qty * tx.price * tx.fx
            cost_total = tx.commission + tx.fees + tx.taxes
            total_cost += gross_value + cost_total
            total_qty += tx.qty
        elif tx.side == "SELL":
            total_qty -= tx.qty
            if total_qty <= 0:
                total_cost = Decimal("0")
                total_qty = Decimal("0")

    if total_qty <= 0:
        return None

    return total_cost / total_qty


def calculate_avg_entry_price_and_fx_from_transactions(
    transactions: Sequence[AvgCostTransactionLike],
) -> tuple[Decimal, Decimal] | None:
    """
    Calculate average entry price and FX for open position (excluding transaction costs).
    
    This uses a moving-average cost model that:
    - Includes BUY quantities at trade price (excluding commission/fees/taxes)
    - Reduces cost basis proportionally on SELL
    - Returns None if the position is closed
    """
    if not transactions:
        return None

    total_qty = Decimal("0")
    total_price_qty = Decimal("0")
    total_base_cost = Decimal("0")

    for tx in transactions:
        qty = Decimal(str(tx.qty))
        price = Decimal(str(tx.price))
        fx = Decimal(str(tx.fx))

        if tx.side == "BUY":
            total_qty += qty
            total_price_qty += qty * price
            total_base_cost += qty * price * fx
            continue

        if tx.side == "SELL":
            if total_qty <= 0:
                continue

            avg_price = total_price_qty / total_qty
            avg_base_cost = total_base_cost / total_qty

            total_qty -= qty
            if total_qty <= 0:
                total_qty = Decimal("0")
                total_price_qty = Decimal("0")
                total_base_cost = Decimal("0")
                continue

            total_price_qty -= avg_price * qty
            total_base_cost -= avg_base_cost * qty

    if total_qty <= 0:
        return None

    avg_price = total_price_qty / total_qty
    if avg_price == 0:
        return None

    avg_base_cost = total_base_cost / total_qty
    avg_fx = avg_base_cost / avg_price

    return avg_price, avg_fx
