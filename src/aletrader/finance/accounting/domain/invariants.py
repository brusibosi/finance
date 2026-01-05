"""
Invariant validation functions.

Enforces accounting invariants and business rules.
All validations return None on success or raise ValueError with clear message.
"""

from decimal import Decimal

from trading_shared.dto.config import TradingEnvironment, normalize_trading_environment


def is_within_tolerance(
    value_a: Decimal,
    value_b: Decimal,
    tolerance: Decimal,
) -> bool:
    """
    Check if two values match within tolerance.
    """
    return abs(value_a - value_b) <= tolerance


def exceeds_absolute(
    value: Decimal,
    threshold: Decimal,
) -> bool:
    """
    Check if absolute value exceeds a threshold.
    """
    return abs(value) > threshold


def validate_account_creation(
    account_id: str,
    initial_equity: Decimal,
    base_currency: str,
    environment: str,
) -> None:
    """
    Validate account creation inputs.

    Args:
        account_id: Account identifier
        initial_equity: Initial equity
        base_currency: Base currency code
        environment: Environment type

    Raises:
        ValueError: If validation fails
    """
    if not account_id or not account_id.strip():
        raise ValueError("account_id must be non-empty")

    if initial_equity < 0:
        raise ValueError("initial_equity must be >= 0")

    if not base_currency or len(base_currency) != 3:
        raise ValueError("base_currency must be a valid 3-letter currency code")

    try:
        normalize_trading_environment(environment)
    except ValueError:
        valid_envs = ", ".join(TradingEnvironment.get_valid_environments())
        raise ValueError(f"environment must be one of: {valid_envs} (got {environment})")


def validate_zero_quantity_or_price(qty: Decimal, price: Decimal) -> None:
    """
    Validate that quantity and price are not zero (FR-025).

    Args:
        qty: Transaction quantity
        price: Transaction price

    Raises:
        ValueError: If qty or price is zero
    """
    if qty == 0:
        raise ValueError("qty must be > 0 (FR-025)")

    if price == 0:
        raise ValueError("price must be > 0 (FR-025)")


def validate_insufficient_cash(cash_before: Decimal, net_value: Decimal) -> None:
    """
    Validate that BUY transaction does not result in negative cash (FR-023).

    Args:
        cash_before: Cash before transaction
        net_value: Net cash impact (negative for BUY)

    Raises:
        ValueError: If cash after transaction would be negative
    """
    cash_after = cash_before + net_value
    if cash_after < 0:
        raise ValueError(
            f"Insufficient cash: cash_before={cash_before}, net_value={net_value}, "
            f"cash_after={cash_after} (FR-023)"
        )


def validate_mark_to_market_has_position(
    has_position: bool,
    symbol: str,
) -> None:
    """
    Validate that MARK_TO_MARKET transaction has an open position (FR-024).

    Args:
        has_position: Whether position exists for symbol
        symbol: Trading symbol

    Raises:
        ValueError: If no position exists
    """
    if not has_position:
        raise ValueError(
            f"MARK_TO_MARKET transaction requires open position for symbol {symbol} (FR-024)"
        )


def validate_balance_invariant(
    cash: Decimal,
    position_notional_sum: Decimal,
    equity: Decimal,
    tolerance: Decimal,
) -> None:
    """
    Validate balance invariant: equity = cash + sum(position_notional) (FR-012).

    Args:
        cash: Account cash
        position_notional_sum: Sum of all position notional values
        equity: Account equity
        tolerance: Allowed difference between equity and cash+positions

    Raises:
        ValueError: If invariant is violated beyond tolerance
    """
    expected_equity = cash + position_notional_sum
    difference = abs(equity - expected_equity)

    if difference > tolerance:
        raise ValueError(
            f"Balance invariant violated: equity={equity}, "
            f"cash + positions={expected_equity}, difference={difference}, "
            f"tolerance={tolerance} (FR-012)"
        )


def validate_pnl_consistency(
    initial_equity: Decimal,
    equity: Decimal,
    realized_pnl_cum: Decimal,
    unrealized_pnl_cum: Decimal,
    tolerance: Decimal,
) -> None:
    """
    Validate P&L consistency: (equity - initial_equity) = realized + unrealized (FR-013).

    Args:
        initial_equity: Initial equity
        equity: Current equity
        realized_pnl_cum: Cumulative realized P&L
        unrealized_pnl_cum: Cumulative unrealized P&L
        tolerance: Allowed difference between total P&L and realized+unrealized

    Raises:
        ValueError: If invariant is violated beyond tolerance
    """
    total_pnl = equity - initial_equity
    expected_total = realized_pnl_cum + unrealized_pnl_cum
    difference = abs(total_pnl - expected_total)

    if difference > tolerance:
        raise ValueError(
            f"P&L consistency violated: total_pnl={total_pnl}, "
            f"realized + unrealized={expected_total}, difference={difference}, "
            f"tolerance={tolerance} (FR-013)"
        )


def validate_position_quantity(qty: Decimal) -> None:
    """
    Validate position quantity for long-only accounts (FR-011).

    Args:
        qty: Position quantity

    Raises:
        ValueError: If quantity is negative (short positions not allowed in v1)
    """
    if qty < 0:
        raise ValueError(
            f"Position quantity cannot be negative (long-only): qty={qty} (FR-011)"
        )


def validate_position_state(
    qty: Decimal,
    avg_cost: Decimal,
    last_price: Decimal,
    fx: Decimal,
    symbol: str,
) -> None:
    """
    Validate position state before creating or updating position.

    Ensures all position fields are valid and positive (CRITICAL for data integrity).

    Args:
        qty: Position quantity
        avg_cost: Average cost per share
        last_price: Last market price
        fx: FX rate
        symbol: Trading symbol (for error messages)

    Raises:
        ValueError: If any validation fails
    """
    if qty <= 0:
        raise ValueError(
            f"Position quantity must be > 0 for symbol {symbol}: qty={qty}"
        )

    if avg_cost <= 0:
        raise ValueError(
            f"Position average cost must be > 0 for symbol {symbol}: avg_cost={avg_cost}. "
            f"This indicates a critical bug in average cost calculation."
        )

    if last_price <= 0:
        raise ValueError(
            f"Position last price must be > 0 for symbol {symbol}: last_price={last_price}"
        )

    if fx <= 0:
        raise ValueError(
            f"Position FX rate must be > 0 for symbol {symbol}: fx={fx}"
        )


def check_chronological_order(
    new_timestamp: str,
    last_timestamp: str | None,
) -> None:
    """
    Check that transaction timestamp is >= last transaction timestamp (FR-014).

    Args:
        new_timestamp: New transaction timestamp (ISO8601)
        last_timestamp: Last transaction timestamp (ISO8601) or None

    Raises:
        ValueError: If new timestamp is earlier than last timestamp
    """
    if last_timestamp is None:
        return  # First transaction for account

    if new_timestamp < last_timestamp:
        raise ValueError(
            f"Transaction timestamp must be >= last transaction: "
            f"new={new_timestamp}, last={last_timestamp} (FR-014)"
        )


def validate_commission_on_execution_only(
    tx_type: str,
    commission: Decimal,
    fees: Decimal,
    taxes: Decimal,
) -> None:
    """
    Validate that commission/fees/taxes are only charged on execution events.

    Commission must be charged only on execution events (FILL, SL, TP).
    ORDER types (ORDER, ORDER_SL, ORDER_TP) and MARK_TO_MARKET must have zero costs.

    Args:
        tx_type: Transaction type
        commission: Commission amount
        fees: Fees amount
        taxes: Taxes amount

    Raises:
        ValueError: If costs are applied to non-execution events
    """
    if tx_type in ("ORDER", "ORDER_SL", "ORDER_TP", "MARK_TO_MARKET"):
        if commission != 0:
            raise ValueError(
                f"Commission must be zero for {tx_type} transactions. "
                f"Commission is only charged on execution events (FILL, SL, TP). "
                f"Got commission={commission}"
            )
        if fees != 0:
            raise ValueError(
                f"Fees must be zero for {tx_type} transactions. "
                f"Fees are only charged on execution events (FILL, SL, TP). "
                f"Got fees={fees}"
            )
        if taxes != 0:
            raise ValueError(
                f"Taxes must be zero for {tx_type} transactions. "
                f"Taxes are only charged on execution events (FILL, SL, TP). "
                f"Got taxes={taxes}"
            )


def validate_entry_unrealized_pnl_zero(
    unrealized_pnl: Decimal,
    symbol: str,
) -> None:
    """
    Validate that unrealized P&L is zero at entry (Rule 3.4).

    On entry, unrealized P&L MUST be 0.00 because there's no price movement yet.

    Args:
        unrealized_pnl: Unrealized P&L value
        symbol: Trading symbol (for error message)

    Raises:
        ValueError: If unrealized P&L is not zero at entry
    """
    if unrealized_pnl != 0:
        raise ValueError(
            f"Unrealized P&L must be 0.00 at entry for symbol {symbol}. "
            f"Got {unrealized_pnl}. Entry has no price movement yet (Rule 3.4)"
        )


def validate_unrealized_pnl_formula(
    unrealized_pnl: Decimal,
    last_price: Decimal,
    entry_price: Decimal,
    quantity: Decimal,
    symbol: str,
    tolerance: Decimal,
) -> None:
    """
    Validate unrealized P&L formula: unrealized_pnl = (last_price - entry_price) * quantity (Rule 4).

    Unrealized P&L is price movement only - no commission, fees, or slippage.

    Args:
        unrealized_pnl: Calculated unrealized P&L
        last_price: Last market price
        entry_price: Entry price
        quantity: Position quantity
        symbol: Trading symbol (for error message)
        tolerance: Allowed difference between expected and actual

    Raises:
        ValueError: If formula doesn't match
    """
    expected_unrealized = (last_price - entry_price) * quantity
    difference = abs(unrealized_pnl - expected_unrealized)

    if difference > tolerance:
        raise ValueError(
            f"Unrealized P&L formula violation for {symbol}: "
            f"expected=(last_price - entry_price) * qty = ({last_price} - {entry_price}) * {quantity} = {expected_unrealized}, "
            f"got={unrealized_pnl}, difference={difference} (Rule 4)"
        )


def validate_exit_unrealized_pnl_zero(
    unrealized_pnl: Decimal,
    symbol: str,
    position_closed: bool,
) -> None:
    """
    Validate that unrealized P&L is zero for closed positions (Rule 5.5, Rule 6).

    On exit, unrealized P&L MUST be set to 0.00. Closed positions have no unrealized P&L.

    Args:
        unrealized_pnl: Unrealized P&L value
        symbol: Trading symbol (for error message)
        position_closed: Whether position is closed

    Raises:
        ValueError: If unrealized P&L is not zero for closed position
    """
    if position_closed and unrealized_pnl != 0:
        raise ValueError(
            f"Unrealized P&L must be 0.00 for closed position {symbol}. "
            f"Got {unrealized_pnl}. Closed positions have no unrealized P&L (Rule 5.5, Rule 6)"
        )


def validate_exit_realized_pnl_formula(
    realized_pnl: Decimal,
    exit_price: Decimal,
    entry_price: Decimal,
    quantity: Decimal,
    commission: Decimal,
    symbol: str,
    tolerance: Decimal,
) -> None:
    """
    Validate realized P&L formula: realized_pnl = (exit_price - entry_price) * quantity - commission (Rule 5.2).

    Args:
        realized_pnl: Calculated realized P&L
        exit_price: Exit price
        entry_price: Entry price
        quantity: Position quantity
        commission: Commission cost
        symbol: Trading symbol (for error message)
        tolerance: Allowed difference between expected and actual

    Raises:
        ValueError: If formula doesn't match
    """
    expected_realized = (exit_price - entry_price) * quantity - commission
    difference = abs(realized_pnl - expected_realized)

    if difference > tolerance:
        raise ValueError(
            f"Realized P&L formula violation for {symbol}: "
            f"expected=(exit_price - entry_price) * qty - commission = "
            f"({exit_price} - {entry_price}) * {quantity} - {commission} = {expected_realized}, "
            f"got={realized_pnl}, difference={difference} (Rule 5.2)"
        )


def validate_equity_reconciliation(
    equity: Decimal,
    cash: Decimal,
    open_positions_market_value: Decimal,
    tolerance: Decimal,
) -> None:
    """
    Validate equity reconciliation: equity = cash + sum(open_position.market_value) (Rule 8).

    This is a mandatory assertion that must hold at all times.
    Failure must stop execution.

    Args:
        equity: Account equity
        cash: Account cash
        open_positions_market_value: Sum of market values for all OPEN positions
        (market_value = last_price * quantity)
        tolerance: Allowed difference between equity and expected

    Raises:
        ValueError: If equity doesn't reconcile (stops execution)
    """
    expected_equity = cash + open_positions_market_value
    difference = abs(equity - expected_equity)

    if difference > tolerance:
        raise ValueError(
            f"EQUITY RECONCILIATION FAILED (Rule 8): "
            f"equity={equity}, cash={cash}, open_positions_market_value={open_positions_market_value}, "
            f"expected_equity={expected_equity}, difference={difference}, "
            f"tolerance={tolerance}. "
            f"Execution must stop - accounting integrity violated."
        )


def validate_cash_never_negative_unexpectedly(
    cash: Decimal,
    context: str = "",
) -> None:
    """
    Validate that cash never goes negative unexpectedly (Rule 14.4).

    Cash can be negative only in specific controlled scenarios (e.g., margin).
    For long-only accounts, cash should not go negative.

    Args:
        cash: Account cash
        context: Context string for error message

    Raises:
        ValueError: If cash is negative unexpectedly
    """
    if cash < 0:
        raise ValueError(
            f"Cash cannot be negative: cash={cash}. {context} "
            f"This indicates insufficient cash validation or accounting error (Rule 14.4)"
        )


def validate_realized_pnl_equals_cash_change(
    realized_pnl_sum: Decimal,
    cash_change: Decimal,
    costs_sum: Decimal,
    tolerance: Decimal,
) -> None:
    """
    Validate that sum of realized P&L = change in cash (net of costs) (Rule 14.5).

    This ensures realized P&L correctly reflects cash movements.

    Args:
        realized_pnl_sum: Sum of all realized P&L deltas
        cash_change: Change in cash (final_cash - initial_cash)
        costs_sum: Sum of all costs (commission + fees + taxes)
        tolerance: Allowed difference between realized P&L sum and cash change

    Raises:
        ValueError: If invariant is violated
    """
    difference = abs(realized_pnl_sum - cash_change)

    if difference > tolerance:
        raise ValueError(
            f"Realized P&L vs Cash Change mismatch (Rule 14.5): "
            f"sum(realized_pnl)={realized_pnl_sum}, cash_change={cash_change}, "
            f"costs_sum={costs_sum}, difference={difference}, "
            f"tolerance={tolerance}. "
            f"Realized P&L must equal cash change (net of costs)."
        )


def validate_commission_applied_once(
    commission_total: Decimal,
    expected_commission: Decimal,
    context: str = "",
    tolerance: Decimal = Decimal("0"),
) -> None:
    """
    Validate that commission is applied exactly once per trade (Rule 6.1).

    Args:
        commission_total: Total commission recorded
        expected_commission: Expected commission (should match)
        context: Context string for error message
        tolerance: Allowed difference between total and expected commission

    Raises:
        ValueError: If commission doesn't match expected (indicates double application)
    """
    difference = abs(commission_total - expected_commission)

    if difference > tolerance:
        raise ValueError(
            f"Commission application error (Rule 6.1): "
            f"total_commission={commission_total}, expected={expected_commission}, "
            f"difference={difference}, tolerance={tolerance}. "
            f"Commission must be applied exactly once per trade. {context}"
        )


def validate_risk_calculation_at_entry(
    risk_amount: Decimal,
    entry_price: Decimal,
    stop_price: Decimal,
    quantity: Decimal,
    equity_at_entry: Decimal,
    tolerance: Decimal,
) -> tuple[Decimal, Decimal]:
    """
    Validate and calculate risk at entry (Rule 7).

    Risk is calculated at entry and stored. It does NOT change after entry.

    Args:
        risk_amount: Risk amount in currency
        entry_price: Entry price
        stop_price: Stop loss price
        quantity: Position quantity
        equity_at_entry: Account equity at entry time
        tolerance: Allowed difference between expected and actual risk amount

    Returns:
        Tuple of (risk_amount, risk_pct) - validated values

    Raises:
        ValueError: If risk calculation doesn't match expected formula
    """
    expected_risk_amount = abs(entry_price - stop_price) * quantity
    difference = abs(risk_amount - expected_risk_amount)

    if difference > tolerance:
        raise ValueError(
            f"Risk calculation error (Rule 7): "
            f"risk_amount={risk_amount}, expected=abs(entry_price - stop_price) * qty = "
            f"abs({entry_price} - {stop_price}) * {quantity} = {expected_risk_amount}, "
            f"difference={difference}"
        )

    if equity_at_entry <= 0:
        raise ValueError(
            f"Equity at entry must be > 0 for risk calculation: equity_at_entry={equity_at_entry}"
        )

    risk_pct = (risk_amount / equity_at_entry) * Decimal("100")

    return (risk_amount, risk_pct)
