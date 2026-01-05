"""Unit tests for realized P&L from exit transactions."""

from decimal import Decimal

from aletrader.finance.accounting.domain.aggregations import (
    calculate_realized_pnl_from_exit_transactions,
)


class MockLedgerTransaction:
    """Mock ledger transaction for testing."""

    def __init__(self, side: str, realized_pnl_delta: Decimal | None):
        self.side = side
        self.realized_pnl_delta = realized_pnl_delta


def test_realized_pnl_from_single_exit() -> None:
    """Test realized P&L from single SELL."""
    tx = MockLedgerTransaction(side="SELL", realized_pnl_delta=Decimal("100"))
    result = calculate_realized_pnl_from_exit_transactions([tx])
    assert result == Decimal("100")


def test_realized_pnl_ignores_buy() -> None:
    """Test that BUY transactions are ignored."""
    transactions = [
        MockLedgerTransaction(side="BUY", realized_pnl_delta=Decimal("0")),
        MockLedgerTransaction(side="SELL", realized_pnl_delta=Decimal("100")),
    ]
    result = calculate_realized_pnl_from_exit_transactions(transactions)
    assert result == Decimal("100")


def test_realized_pnl_from_multiple_exits() -> None:
    """Test realized P&L from multiple exits."""
    transactions = [
        MockLedgerTransaction(side="SELL", realized_pnl_delta=Decimal("100")),
        MockLedgerTransaction(side="SELL", realized_pnl_delta=Decimal("-50")),
        MockLedgerTransaction(side="SELL", realized_pnl_delta=Decimal("75")),
    ]
    result = calculate_realized_pnl_from_exit_transactions(transactions)
    assert result == Decimal("125")


def test_realized_pnl_with_none_values() -> None:
    """Test that None realized_pnl_delta is handled."""
    transactions = [
        MockLedgerTransaction(side="SELL", realized_pnl_delta=None),
        MockLedgerTransaction(side="SELL", realized_pnl_delta=Decimal("100")),
    ]
    result = calculate_realized_pnl_from_exit_transactions(transactions)
    assert result == Decimal("100")


def test_realized_pnl_empty_transactions() -> None:
    """Test with no transactions."""
    result = calculate_realized_pnl_from_exit_transactions([])
    assert result == Decimal("0")


def test_realized_pnl_only_buys() -> None:
    """Test with only BUY transactions (no realized P&L)."""
    transactions = [
        MockLedgerTransaction(side="BUY", realized_pnl_delta=Decimal("0")),
        MockLedgerTransaction(side="BUY", realized_pnl_delta=Decimal("0")),
    ]
    result = calculate_realized_pnl_from_exit_transactions(transactions)
    assert result == Decimal("0")


def test_realized_pnl_negative_total() -> None:
    """Test realized P&L with net loss."""
    transactions = [
        MockLedgerTransaction(side="SELL", realized_pnl_delta=Decimal("50")),
        MockLedgerTransaction(side="SELL", realized_pnl_delta=Decimal("-100")),
    ]
    result = calculate_realized_pnl_from_exit_transactions(transactions)
    assert result == Decimal("-50")


def test_realized_pnl_precision() -> None:
    """Test that precision is preserved."""
    transactions = [
        MockLedgerTransaction(side="SELL", realized_pnl_delta=Decimal("123.456789")),
        MockLedgerTransaction(side="SELL", realized_pnl_delta=Decimal("0.000001")),
    ]
    result = calculate_realized_pnl_from_exit_transactions(transactions)
    assert result == Decimal("123.456790")
