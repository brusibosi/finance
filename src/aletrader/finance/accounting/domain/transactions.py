"""
Transaction-level accounting logic.

Pure domain functions for transaction processing and P&L calculations.
All monetary values use Decimal with ROUND_HALF_UP rounding.
"""

from decimal import Decimal, ROUND_HALF_UP, getcontext
from typing import Literal, TypedDict

# Set global decimal context with ROUND_HALF_UP
# Per constitution: explicit rounding mode required
getcontext().rounding = ROUND_HALF_UP
getcontext().prec = 28  # High precision for financial calculations


class AccountStateBefore(TypedDict):
    """Account state before transaction (Balance Sheet Approach)."""

    cash: Decimal
    max_equity_to_date: Decimal
    initial_equity: Decimal


class PositionStateBefore(TypedDict):
    """Position state before transaction."""

    qty: Decimal
    avg_cost: Decimal
    last_price: Decimal
    fx: Decimal


class TransactionInput(TypedDict):
    """Transaction input parameters."""

    type: Literal["ORDER", "ORDER_SL", "ORDER_TP", "FILL", "SL", "TP", "MARK_TO_MARKET", "ADJUSTMENT"]
    side: Literal["BUY", "SELL"]
    qty: Decimal
    price: Decimal
    commission: Decimal
    fees: Decimal
    taxes: Decimal
    fx: Decimal
    sl_price: Decimal | None


class TransactionResult(TypedDict):
    """Transaction result with all calculated fields (Balance Sheet Approach)."""

    gross_value: Decimal
    cost_total: Decimal
    net_value: Decimal
    cash_after: Decimal
    position_qty_after: Decimal
    position_avg_cost_after: Decimal
    position_notional_after: Decimal
    realized_pnl_delta: Decimal  # Retained for informational/logging purposes only
    last_price_after: Decimal
    fx_after: Decimal
    position_removed: bool


def calculate_gross_value(qty: Decimal, price: Decimal, fx: Decimal) -> Decimal:
    """
    Calculate gross value: qty * price * fx.

    Args:
        qty: Transaction quantity
        price: Transaction price in symbol currency
        fx: FX rate from symbol currency to account currency

    Returns:
        Gross value in account currency
    """
    return (qty * price * fx).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def calculate_cost_total(commission: Decimal, fees: Decimal, taxes: Decimal) -> Decimal:
    """
    Calculate total costs: commission + fees + taxes.

    Args:
        commission: Commission cost
        fees: Additional fees
        taxes: Tax costs

    Returns:
        Total costs in account currency
    """
    return (commission + fees + taxes).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def calculate_net_value(
    gross_value: Decimal,
    cost_total: Decimal,
    side: str,
) -> Decimal:
    """
    Calculate net cash impact of a transaction.

    BUY: net_value = -(gross_value + cost_total)
    SELL: net_value = gross_value - cost_total
    """
    if side == "BUY":
        return -(gross_value + cost_total)
    if side == "SELL":
        return gross_value - cost_total
    raise ValueError(f"Unknown side: {side}")


def apply_transaction(
    account_before: AccountStateBefore,
    position_before: PositionStateBefore | None,
    tx_input: TransactionInput,
) -> TransactionResult:
    """
    Apply transaction and calculate new state.

    Pure function: no side effects, deterministic.
    Per constitution: all accounting logic in pure domain functions.

    Args:
        account_before: Account state before transaction
        position_before: Position state before transaction (None if no position)
        tx_input: Transaction input parameters

    Returns:
        Transaction result with all calculated fields
    """
    # Calculate monetary values
    gross_value = calculate_gross_value(tx_input["qty"], tx_input["price"], tx_input["fx"])
    cost_total = calculate_cost_total(tx_input["commission"], tx_input["fees"], tx_input["taxes"])

    # Calculate net cash impact
    if tx_input["side"] == "BUY":
        net_value = -(gross_value + cost_total)  # Negative: cash decreases
    else:  # SELL
        net_value = gross_value - cost_total  # Positive: cash increases

    # Handle different transaction types
    tx_type = tx_input["type"]

    if tx_type in ("ORDER", "ORDER_SL", "ORDER_TP"):
        # Orders have no cash/position impact
        return _apply_order_transaction(account_before, position_before, tx_input, gross_value, cost_total, net_value)
    if tx_type == "MARK_TO_MARKET":
        # Mark to market only updates prices
        return _apply_mark_to_market(account_before, position_before, tx_input, gross_value, cost_total, net_value)
    if tx_type in ("FILL", "SL", "TP"):
        # Fills affect cash and positions
        if tx_input["side"] == "BUY":
            return _apply_buy_fill(account_before, position_before, tx_input, gross_value, cost_total, net_value)
        return _apply_sell_fill(account_before, position_before, tx_input, gross_value, cost_total, net_value)
    # ADJUSTMENT
    raise ValueError(f"Transaction type {tx_type} not yet implemented")


def _apply_order_transaction(
    account_before: AccountStateBefore,
    position_before: PositionStateBefore | None,
    tx_input: TransactionInput,
    gross_value: Decimal,
    cost_total: Decimal,
    net_value: Decimal,
) -> TransactionResult:
    """Apply ORDER/ORDER_SL/ORDER_TP transaction (no cash/position impact)."""
    return TransactionResult(
        gross_value=gross_value,
        cost_total=cost_total,
        net_value=net_value,
        cash_after=account_before["cash"],  # Unchanged
        position_qty_after=position_before["qty"] if position_before else Decimal("0"),
        position_avg_cost_after=position_before["avg_cost"] if position_before else Decimal("0"),
        position_notional_after=(
            position_before["qty"] * position_before["last_price"] * position_before["fx"]
            if position_before
            else Decimal("0")
        ),
        realized_pnl_delta=Decimal("0"),
        last_price_after=tx_input["price"],
        fx_after=tx_input["fx"],
        position_removed=False,
    )


def _apply_mark_to_market(
    account_before: AccountStateBefore,
    position_before: PositionStateBefore | None,
    tx_input: TransactionInput,
    gross_value: Decimal,
    cost_total: Decimal,
    net_value: Decimal,
) -> TransactionResult:
    """Apply MARK_TO_MARKET transaction (update prices only)."""
    if not position_before:
        raise ValueError("MARK_TO_MARKET requires existing position")

    return TransactionResult(
        gross_value=gross_value,
        cost_total=cost_total,
        net_value=net_value,
        cash_after=account_before["cash"],  # Unchanged
        position_qty_after=position_before["qty"],
        position_avg_cost_after=position_before["avg_cost"],  # Unchanged
        position_notional_after=position_before["qty"] * tx_input["price"] * tx_input["fx"],
        realized_pnl_delta=Decimal("0"),
        last_price_after=tx_input["price"],
        fx_after=tx_input["fx"],
        position_removed=False,
    )


def _apply_buy_fill(
    account_before: AccountStateBefore,
    position_before: PositionStateBefore | None,
    tx_input: TransactionInput,
    gross_value: Decimal,
    cost_total: Decimal,
    net_value: Decimal,
) -> TransactionResult:
    """Apply BUY FILL transaction (entry or add)."""
    cash_after = account_before["cash"] + net_value  # net_value is negative for BUY

    if position_before is None:
        # Entry: new position
        # Include transaction costs in average cost to maintain equity consistency
        qty_after = tx_input["qty"]
        total_cost = tx_input["qty"] * tx_input["price"] * tx_input["fx"] + cost_total
        avg_cost_after = total_cost / tx_input["qty"]
    else:
        # Add: increase position, recalculate average cost
        # Include transaction costs in average cost
        cost_before = position_before["qty"] * position_before["avg_cost"]
        cost_new = tx_input["qty"] * tx_input["price"] * tx_input["fx"] + cost_total
        qty_after = position_before["qty"] + tx_input["qty"]
        avg_cost_after = (cost_before + cost_new) / qty_after

    # CRITICAL: Ensure avg_cost is always positive
    # This prevents the zero avg_cost bug (Issue #1)
    if avg_cost_after <= 0:
        raise ValueError(
            f"Calculated average cost must be > 0, got {avg_cost_after}. "
            f"This indicates a bug in cost calculation. "
            f"qty={qty_after}, price={tx_input['price']}, fx={tx_input['fx']}, cost_total={cost_total}"
        )

    position_notional_after = qty_after * tx_input["price"] * tx_input["fx"]

    # CRITICAL FIX: Transaction costs on BUY do NOT affect realized P&L
    # They are already included in avg_cost, which affects unrealized P&L
    # Realized P&L only changes when positions are SOLD (in _apply_sell_fill)
    # Setting realized_pnl_delta = -cost_total was DOUBLE-COUNTING costs!
    # This was the root cause of the £680 P&L consistency violation (FR-013)
    # Balance Sheet Approach: P&L delta retained for informational purposes only
    realized_pnl_delta = Decimal("0")

    return TransactionResult(
        gross_value=gross_value,
        cost_total=cost_total,
        net_value=net_value,
        cash_after=cash_after,
        position_qty_after=qty_after,
        position_avg_cost_after=avg_cost_after,
        position_notional_after=position_notional_after,
        realized_pnl_delta=realized_pnl_delta,  # Always 0 for BUY (costs captured in avg_cost)
        last_price_after=tx_input["price"],
        fx_after=tx_input["fx"],
        position_removed=False,
    )


def _apply_sell_fill(
    account_before: AccountStateBefore,
    position_before: PositionStateBefore | None,
    tx_input: TransactionInput,
    gross_value: Decimal,
    cost_total: Decimal,
    net_value: Decimal,
) -> TransactionResult:
    """Apply SELL FILL transaction (reduce or close)."""
    if position_before is None:
        raise ValueError("SELL FILL requires existing position")

    if position_before["qty"] < tx_input["qty"]:
        raise ValueError(f"Insufficient position: have {position_before['qty']}, trying to sell {tx_input['qty']}")

    cash_after = account_before["cash"] + net_value  # net_value is positive for SELL

    # Calculate realized P&L (informational only - not stored in database)
    pnl_gross = (tx_input["price"] * tx_input["fx"] - position_before["avg_cost"]) * tx_input["qty"]
    realized_pnl_delta = pnl_gross - cost_total

    # Update position
    qty_after = position_before["qty"] - tx_input["qty"]
    position_removed = qty_after == 0

    if position_removed:
        avg_cost_after = Decimal("0")
        position_notional_after = Decimal("0")
    else:
        avg_cost_after = position_before["avg_cost"]  # Unchanged for partial close
        position_notional_after = qty_after * tx_input["price"] * tx_input["fx"]

    return TransactionResult(
        gross_value=gross_value,
        cost_total=cost_total,
        net_value=net_value,
        cash_after=cash_after,
        position_qty_after=qty_after,
        position_avg_cost_after=avg_cost_after,
        position_notional_after=position_notional_after,
        realized_pnl_delta=realized_pnl_delta,  # Informational only (not stored)
        last_price_after=tx_input["price"],
        fx_after=tx_input["fx"],
        position_removed=position_removed,
    )


def calculate_drawdown(
    max_equity_to_date: Decimal,
    current_equity: Decimal,
) -> Decimal:
    """
    Calculate drawdown percentage.

    Args:
        max_equity_to_date: Peak equity
        current_equity: Current equity

    Returns:
        Drawdown percentage (0-100)
    """
    if max_equity_to_date <= 0:
        return Decimal("0")

    dd = ((max_equity_to_date - current_equity) / max_equity_to_date) * Decimal("100")
    return dd.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
