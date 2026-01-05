"""Unit tests for cash calculation from transactions."""

from decimal import Decimal

from aletrader.finance.accounting.domain.calculations import (
    calculate_cash_from_initial_and_transactions,
)


class MockTransaction:
    """Mock transaction for testing."""

    def __init__(
        self,
        type: str,
        side: str | None = None,
        qty: Decimal | None = None,
        price: Decimal | None = None,
        commission: Decimal | None = None,
        fees: Decimal | None = None,
        taxes: Decimal | None = None,
        amount: Decimal | None = None,
    ):
        self.type = type
        self.side = side
        self.qty = qty
        self.price = price
        self.commission = commission
        self.fees = fees
        self.taxes = taxes
        self.amount = amount


def test_cash_from_initial_only() -> None:
    """Test cash calculation with no transactions."""
    result = calculate_cash_from_initial_and_transactions(Decimal("10000"), [])
    assert result == Decimal("10000")


def test_cash_with_buy_transaction() -> None:
    """Test cash decreases with BUY."""
    tx = MockTransaction(
        type="FILL",
        side="BUY",
        qty=Decimal("10"),
        price=Decimal("100"),
        commission=Decimal("1"),
        fees=Decimal("0.5"),
        taxes=Decimal("0"),
    )
    result = calculate_cash_from_initial_and_transactions(Decimal("10000"), [tx])
    # 10000 - (10*100 + 1 + 0.5) = 10000 - 1001.5 = 8998.5
    assert result == Decimal("8998.5")


def test_cash_with_sell_transaction() -> None:
    """Test cash increases with SELL."""
    tx = MockTransaction(
        type="FILL",
        side="SELL",
        qty=Decimal("10"),
        price=Decimal("110"),
        commission=Decimal("1"),
        fees=Decimal("0.5"),
        taxes=Decimal("0"),
    )
    result = calculate_cash_from_initial_and_transactions(Decimal("10000"), [tx])
    # 10000 + (10*110 - 1 - 0.5) = 10000 + 1098.5 = 11098.5
    assert result == Decimal("11098.5")


def test_cash_with_deposit() -> None:
    """Test cash increases with DEPOSIT."""
    tx = MockTransaction(type="DEPOSIT", amount=Decimal("5000"))
    result = calculate_cash_from_initial_and_transactions(Decimal("10000"), [tx])
    assert result == Decimal("15000")


def test_cash_with_withdrawal() -> None:
    """Test cash decreases with WITHDRAWAL."""
    tx = MockTransaction(type="WITHDRAWAL", amount=Decimal("2000"))
    result = calculate_cash_from_initial_and_transactions(Decimal("10000"), [tx])
    assert result == Decimal("8000")


def test_cash_with_multiple_transactions() -> None:
    """Test cash with mixed transaction types."""
    transactions = [
        MockTransaction(
            type="FILL",
            side="BUY",
            qty=Decimal("10"),
            price=Decimal("100"),
            commission=Decimal("1"),
            fees=Decimal("0"),
            taxes=Decimal("0"),
        ),
        MockTransaction(
            type="FILL",
            side="SELL",
            qty=Decimal("10"),
            price=Decimal("110"),
            commission=Decimal("1"),
            fees=Decimal("0"),
            taxes=Decimal("0"),
        ),
    ]
    result = calculate_cash_from_initial_and_transactions(Decimal("10000"), transactions)
    # 10000 - 1001 + 1099 = 10098
    assert result == Decimal("10098")


def test_cash_with_sl_transaction() -> None:
    """Test cash increases with SL (stop loss)."""
    tx = MockTransaction(
        type="SL",
        side="SELL",
        qty=Decimal("10"),
        price=Decimal("95"),
        commission=Decimal("1"),
        fees=Decimal("0"),
        taxes=Decimal("0"),
    )
    result = calculate_cash_from_initial_and_transactions(Decimal("10000"), [tx])
    # 10000 + (10*95 - 1) = 10000 + 949 = 10949
    assert result == Decimal("10949")


def test_cash_with_tp_transaction() -> None:
    """Test cash increases with TP (take profit)."""
    tx = MockTransaction(
        type="TP",
        side="SELL",
        qty=Decimal("10"),
        price=Decimal("120"),
        commission=Decimal("1"),
        fees=Decimal("0.5"),
        taxes=Decimal("0"),
    )
    result = calculate_cash_from_initial_and_transactions(Decimal("10000"), [tx])
    # 10000 + (10*120 - 1 - 0.5) = 10000 + 1198.5 = 11198.5
    assert result == Decimal("11198.5")


def test_cash_with_none_costs() -> None:
    """Test that None costs are treated as zero."""
    tx = MockTransaction(
        type="FILL",
        side="BUY",
        qty=Decimal("10"),
        price=Decimal("100"),
        commission=None,
        fees=None,
        taxes=None,
    )
    result = calculate_cash_from_initial_and_transactions(Decimal("10000"), [tx])
    # 10000 - (10*100 + 0) = 9000
    assert result == Decimal("9000")
