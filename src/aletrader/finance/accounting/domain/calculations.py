"""
Core accounting calculations.

Pure domain logic with no I/O or logging.
"""

from decimal import Decimal, ROUND_HALF_UP


def _ensure_decimal(value: Decimal, name: str) -> None:
    """Validate that a value is a Decimal."""
    if not isinstance(value, Decimal):
        raise TypeError(f"{name} must be a Decimal (got {type(value).__name__})")


def _ensure_non_empty_str(value: str, name: str) -> None:
    """Validate that a string is non-empty."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def calculate_position_notional(
    qty: Decimal,
    last_price: Decimal,
    fx_rate: Decimal,
    currency: str,
    base_currency: str,
    stored_notional: Decimal | None = None,
) -> Decimal:
    """
    Calculate position notional value in base currency.

    Formula: qty * last_price * fx_rate (if currency != base_currency)
             qty * last_price (if currency == base_currency)

    Args:
        qty: Position quantity
        last_price: Last price in symbol currency
        fx_rate: FX rate from symbol currency to base currency
        currency: Symbol currency code
        base_currency: Account base currency code
        stored_notional: Optional stored notional value (for validation)

    Returns:
        Position notional value in base currency

    Raises:
        TypeError: If numeric inputs are not Decimal
        ValueError: If inputs are invalid
    """
    _ensure_decimal(qty, "qty")
    _ensure_decimal(last_price, "last_price")
    _ensure_decimal(fx_rate, "fx_rate")
    _ensure_non_empty_str(currency, "currency")
    _ensure_non_empty_str(base_currency, "base_currency")

    if qty < 0:
        raise ValueError("qty must be >= 0")
    if qty > 0 and last_price <= 0:
        raise ValueError("last_price must be > 0 when qty > 0")
    if currency != base_currency and fx_rate <= 0:
        raise ValueError("fx_rate must be > 0 when currency != base_currency")

    expected_notional = (
        qty * last_price
        if currency == base_currency
        else qty * last_price * fx_rate
    )

    if stored_notional is None:
        return expected_notional

    _ensure_decimal(stored_notional, "stored_notional")
    return stored_notional


def calculate_equity(
    cash: Decimal,
    position_notional_sum: Decimal,
) -> Decimal:
    """
    Calculate equity: cash + sum of position notional values.

    Args:
        cash: Account cash
        position_notional_sum: Sum of all position notional values

    Returns:
        Account equity
    """
    _ensure_decimal(cash, "cash")
    _ensure_decimal(position_notional_sum, "position_notional_sum")
    return (cash + position_notional_sum).quantize(
        Decimal("0.000001"),
        rounding=ROUND_HALF_UP,
    )


def calculate_equity_canonical(
    cash: Decimal,
    positions_market_value: Decimal,
) -> Decimal:
    """
    Canonical equity formula.

    Formula: Equity = Cash + Sum(Position Market Value)
    """
    return calculate_equity(
        cash=cash,
        position_notional_sum=positions_market_value,
    )


def calculate_amount_base(
    amount_native: Decimal,
    fx_rate_used: Decimal,
) -> Decimal:
    """
    Convert native amount to base currency using FX rate.
    """
    _ensure_decimal(amount_native, "amount_native")
    _ensure_decimal(fx_rate_used, "fx_rate_used")
    return amount_native * fx_rate_used


def calculate_amount_native(
    qty: Decimal,
    price: Decimal,
) -> Decimal:
    """
    Calculate native amount: qty * price.
    """
    _ensure_decimal(qty, "qty")
    _ensure_decimal(price, "price")
    return qty * price


def resolve_amount_native(
    amount_native: Decimal | None,
    qty: Decimal,
    price: Decimal,
) -> Decimal:
    """
    Resolve amount_native with fallback to qty * price.
    """
    if amount_native is not None:
        return amount_native
    return calculate_amount_native(qty=qty, price=price)


def resolve_amount_base(
    amount_base: Decimal | None,
    amount_native: Decimal | None,
    qty: Decimal,
    price: Decimal,
) -> Decimal:
    """
    Resolve amount_base with fallback to amount_native or qty * price.
    """
    if amount_base is not None:
        return amount_base
    if amount_native is not None:
        return amount_native
    return calculate_amount_native(qty=qty, price=price)


def calculate_total_pnl(
    initial_equity: Decimal,
    current_equity: Decimal,
) -> Decimal:
    """
    Calculate total P&L: current_equity - initial_equity.

    Args:
        initial_equity: Initial equity (invested capital)
        current_equity: Current equity

    Returns:
        Total P&L
    """
    _ensure_decimal(initial_equity, "initial_equity")
    _ensure_decimal(current_equity, "current_equity")
    return (current_equity - initial_equity).quantize(
        Decimal("0.000001"),
        rounding=ROUND_HALF_UP,
    )


def calculate_total_pnl_pct(
    total_pnl: Decimal,
    initial_equity: Decimal,
) -> Decimal:
    """
    Calculate total P&L percentage using initial_equity as denominator.

    total_pnl_pct = (total_pnl / initial_equity) * 100

    Args:
        total_pnl: Total P&L (current_equity - initial_equity)
        initial_equity: Initial equity (invested capital)

    Returns:
        Total P&L percentage, or 0 if initial_equity <= 0
    """
    _ensure_decimal(total_pnl, "total_pnl")
    _ensure_decimal(initial_equity, "initial_equity")
    if initial_equity <= 0:
        return Decimal("0")
    pnl_pct = (total_pnl / initial_equity) * Decimal("100")
    return pnl_pct.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def calculate_total_pnl_metrics(
    initial_equity: Decimal,
    current_equity: Decimal,
) -> tuple[Decimal, Decimal]:
    """
    Calculate total P&L and percentage.

    Args:
        initial_equity: Initial equity (invested capital)
        current_equity: Current equity

    Returns:
        Tuple of (total_pnl, total_pnl_pct)
    """
    total_pnl = calculate_total_pnl(initial_equity=initial_equity, current_equity=current_equity)
    total_pnl_pct = calculate_total_pnl_pct(total_pnl=total_pnl, initial_equity=initial_equity)
    return (total_pnl, total_pnl_pct)


def calculate_cash_from_initial_and_transactions(
    initial_equity: Decimal,
    transactions: list,
) -> Decimal:
    """
    Calculate current cash from initial equity and all cash movements.

    Formula: cash = initial_equity + sum(cash_delta for all transactions)

    Cash movements:
    - BUY: cash decreases by (qty * price + commission + fees + taxes)
    - SELL: cash increases by (qty * price - commission - fees - taxes)
    - SL/TP: cash increases by (qty * price - commission - fees - taxes)
    - DEPOSIT: cash increases by amount
    - WITHDRAWAL: cash decreases by amount

    Args:
        initial_equity: Starting cash balance
        transactions: All transactions affecting cash (CashMovementTransactionLike)

    Returns:
        Current cash balance

    Raises:
        TypeError: If initial_equity is not Decimal
    """
    _ensure_decimal(initial_equity, "initial_equity")
    
    cash = initial_equity

    for tx in transactions:
        # Convert to Decimal with safety
        commission = Decimal(str(tx.commission)) if tx.commission is not None else Decimal("0")
        fees = Decimal(str(tx.fees)) if tx.fees is not None else Decimal("0")
        taxes = Decimal(str(tx.taxes)) if tx.taxes is not None else Decimal("0")
        costs = commission + fees + taxes

        if tx.type == "FILL":
            qty = Decimal(str(tx.qty))
            price = Decimal(str(tx.price))

            if tx.side == "BUY":
                # Cash out: qty * price + costs
                cash -= qty * price + costs
            elif tx.side == "SELL":
                # Cash in: qty * price - costs
                cash += qty * price - costs

        elif tx.type in ("SL", "TP"):
            # Exit: cash in
            qty = Decimal(str(tx.qty))
            price = Decimal(str(tx.price))
            cash += qty * price - costs

        elif tx.type == "DEPOSIT":
            amount = Decimal(str(tx.amount))
            cash += amount

        elif tx.type == "WITHDRAWAL":
            amount = Decimal(str(tx.amount))
            cash -= amount

    return cash

