"""
Position-specific accounting calculations.
"""

from decimal import Decimal, ROUND_HALF_UP


def _ensure_decimal(value: Decimal, name: str) -> None:
    """Validate that a value is a Decimal."""
    if not isinstance(value, Decimal):
        raise TypeError(f"{name} must be a Decimal (got {type(value).__name__})")


def calculate_unrealized_pnl(
    qty: Decimal,
    last_price: Decimal,
    fx: Decimal,
    avg_cost: Decimal,
) -> Decimal:
    """
    Calculate unrealized P&L for a position.

    Args:
        qty: Position quantity
        last_price: Last mark price in symbol currency
        fx: FX rate
        avg_cost: Average cost in account currency

    Returns:
        Unrealized P&L
    """
    _ensure_decimal(qty, "qty")
    _ensure_decimal(last_price, "last_price")
    _ensure_decimal(fx, "fx")
    _ensure_decimal(avg_cost, "avg_cost")
    return (qty * (last_price * fx - avg_cost)).quantize(
        Decimal("0.000001"),
        rounding=ROUND_HALF_UP,
    )


def calculate_unrealized_pnl_canonical(
    last_price: Decimal,
    entry_price: Decimal,
    qty: Decimal,
    fx: Decimal,
    entry_fx: Decimal | None = None,
) -> Decimal:
    """
    Canonical unrealised P&L formula.

    Formula: Unrealised P&L = (LastPrice * FX - EntryPrice * EntryFX) * Qty

    Args:
        last_price: Last market price in symbol currency
        entry_price: Entry price in symbol currency
        qty: Position quantity
        fx: FX rate from symbol currency to base currency (for last_price)
        entry_fx: FX rate from symbol currency to base currency (for entry_price)

    Returns:
        Unrealised P&L in base currency

    Raises:
        ValueError: If entry_price is NULL or zero
    """
    _ensure_decimal(last_price, "last_price")
    _ensure_decimal(entry_price, "entry_price")
    _ensure_decimal(qty, "qty")
    _ensure_decimal(fx, "fx")
    if entry_fx is not None:
        _ensure_decimal(entry_fx, "entry_fx")

    if entry_price == 0:
        raise ValueError(
            "Entry price must be non-null and non-zero for unrealised P&L calculation. "
            f"Got entry_price={entry_price}"
        )

    effective_entry_fx = entry_fx if entry_fx is not None else fx
    last_price_base = last_price * fx
    entry_price_base = entry_price * effective_entry_fx
    unrealized_pnl = (last_price_base - entry_price_base) * qty
    return unrealized_pnl.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def validate_position_notional(
    notional: Decimal,
    qty: Decimal,
    last_price: Decimal,
    fx_rate: Decimal,
    tolerance: Decimal = Decimal("0.01"),
) -> Decimal:
    """
    Validate and correct position notional value.

    Recalculates notional if stored value doesn't match calculation within tolerance.

    Args:
        notional: Stored notional value
        qty: Position quantity
        last_price: Last price
        fx_rate: FX rate
        tolerance: Allowed difference between stored and calculated

    Returns:
        Corrected notional value (recalculated if mismatch)
    """
    _ensure_decimal(notional, "notional")
    _ensure_decimal(qty, "qty")
    _ensure_decimal(last_price, "last_price")
    _ensure_decimal(fx_rate, "fx_rate")
    _ensure_decimal(tolerance, "tolerance")
    if tolerance < 0:
        raise ValueError("tolerance must be >= 0")

    expected_notional = qty * last_price * fx_rate
    notional_diff = abs(notional - expected_notional)
    if notional_diff > tolerance:
        return expected_notional
    return notional


def evaluate_notional_mismatch(
    notional: Decimal,
    qty: Decimal,
    last_price: Decimal,
    fx_rate: Decimal,
    tolerance: Decimal = Decimal("0.01"),
) -> tuple[Decimal, Decimal, bool]:
    """
    Evaluate notional mismatch against expected value.

    Returns (expected_notional, diff, mismatch).
    """
    _ensure_decimal(notional, "notional")
    _ensure_decimal(qty, "qty")
    _ensure_decimal(last_price, "last_price")
    _ensure_decimal(fx_rate, "fx_rate")
    _ensure_decimal(tolerance, "tolerance")
    if tolerance < 0:
        raise ValueError("tolerance must be >= 0")

    expected_notional = qty * last_price * fx_rate
    diff = abs(notional - expected_notional)
    return (expected_notional, diff, diff > tolerance)
