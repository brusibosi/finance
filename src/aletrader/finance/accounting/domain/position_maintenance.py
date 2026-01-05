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


def reconstruct_positions_from_transactions(
    transactions: list,
    market_prices: dict[str, Decimal],
    fx_rates: dict[str, Decimal],
) -> list[dict]:
    """
    Reconstruct open positions from transaction history.

    For each symbol:
    1. Find last transaction
    2. If position_qty_after > 0, position is open
    3. Calculate unrealized P&L using current market price

    Args:
        transactions: All position transactions (PositionTransactionLike)
        market_prices: Current market prices by symbol
        fx_rates: Current FX rates by symbol

    Returns:
        List of position state dictionaries
    """
    from aletrader.finance.accounting.domain.position_calculations import (
        calculate_unrealized_pnl,
    )

    # Group by symbol and find last transaction
    last_tx_per_symbol: dict[str, any] = {}

    for tx in transactions:
        symbol = tx.symbol
        if symbol not in last_tx_per_symbol:
            last_tx_per_symbol[symbol] = tx
        else:
            # Compare timestamps (ISO format strings)
            if tx.timestamp > last_tx_per_symbol[symbol].timestamp:
                last_tx_per_symbol[symbol] = tx

    positions = []

    for symbol, last_tx in last_tx_per_symbol.items():
        qty_after = Decimal(str(last_tx.position_qty_after))

        if qty_after <= 0:
            continue  # Position closed

        # Get current market data (fallback to last transaction price/fx)
        last_price = market_prices.get(symbol, Decimal(str(last_tx.price)))
        fx_rate = fx_rates.get(symbol, Decimal(str(last_tx.fx_rate_used)))
        avg_cost = Decimal(str(last_tx.position_avg_cost_after))

        # Calculate unrealized P&L
        unrealized_pnl = calculate_unrealized_pnl(
            qty=qty_after,
            last_price=last_price,
            fx=fx_rate,
            avg_cost=avg_cost,
        )

        # Calculate notional (market value)
        notional = qty_after * last_price * fx_rate

        positions.append(
            {
                "symbol": symbol,
                "qty": qty_after,
                "avg_cost": avg_cost,
                "last_price": last_price,
                "fx": fx_rate,
                "notional": notional,
                "unrealized_pnl": unrealized_pnl,
            }
        )

    return positions

