"""
Test realized P&L derivation from raw transaction history.

Tests the calculation of realized P&L from ledger transactions
without relying on stored realized_pnl_delta (balance sheet approach).
"""

from decimal import Decimal
from typing import NamedTuple

import pytest

from aletrader.finance.accounting.domain.aggregations import (
    calculate_realized_pnl_from_transaction_history,
)


class MockTransaction(NamedTuple):
    """Mock transaction for testing."""
    symbol: str
    side: str  # BUY, SELL
    type: str  # FILL, EXIT, SL, TP
    qty: Decimal
    price: Decimal
    commission: Decimal
    fees: Decimal
    taxes: Decimal
    fx: Decimal = Decimal("1.0")


def test_realized_pnl_simple_full_exit():
    """
    Test simple case: BUY 100 shares, SELL all 100 shares at profit.
    
    Scenario:
    - BUY 100 @ £10.00, commission £5 → avg_cost = £10.05
    - SELL 100 @ £12.00, commission £5 → exit_price = £12.00
    - Realized P&L = (£12.00 - £10.05) × 100 - £5 = £195 - £5 = £190
    """
    transactions = [
        MockTransaction(
            symbol="AAPL",
            side="BUY",
            type="FILL",
            qty=Decimal("100"),
            price=Decimal("10.00"),
            commission=Decimal("5.00"),
            fees=Decimal("0"),
            taxes=Decimal("0"),
        ),
        MockTransaction(
            symbol="AAPL",
            side="SELL",
            type="EXIT",
            qty=Decimal("100"),
            price=Decimal("12.00"),
            commission=Decimal("5.00"),
            fees=Decimal("0"),
            taxes=Decimal("0"),
        ),
    ]
    
    realized_pnl = calculate_realized_pnl_from_transaction_history(transactions)
    
    # Expected: (12.00 - 10.05) * 100 - 5.00 = 195 - 5 = 190
    expected = Decimal("190.00")
    assert realized_pnl == expected, f"Expected {expected}, got {realized_pnl}"


def test_realized_pnl_partial_exit():
    """
    Test partial exit: BUY 100, SELL 60, SELL remaining 40.
    
    Scenario:
    - BUY 100 @ £10.00, commission £5 → avg_cost = £10.05
    - SELL 60 @ £11.00, commission £3 → realized P&L on 60
    - SELL 40 @ £12.00, commission £2 → realized P&L on 40
    """
    transactions = [
        MockTransaction(
            symbol="AAPL",
            side="BUY",
            type="FILL",
            qty=Decimal("100"),
            price=Decimal("10.00"),
            commission=Decimal("5.00"),
            fees=Decimal("0"),
            taxes=Decimal("0"),
        ),
        MockTransaction(
            symbol="AAPL",
            side="SELL",
            type="EXIT",
            qty=Decimal("60"),
            price=Decimal("11.00"),
            commission=Decimal("3.00"),
            fees=Decimal("0"),
            taxes=Decimal("0"),
        ),
        MockTransaction(
            symbol="AAPL",
            side="SELL",
            type="EXIT",
            qty=Decimal("40"),
            price=Decimal("12.00"),
            commission=Decimal("2.00"),
            fees=Decimal("0"),
            taxes=Decimal("0"),
        ),
    ]
    
    realized_pnl = calculate_realized_pnl_from_transaction_history(transactions)
    
    # Exit 1: (11.00 - 10.05) * 60 - 3.00 = 57.00 - 3.00 = 54.00
    # Exit 2: (12.00 - 10.05) * 40 - 2.00 = 78.00 - 2.00 = 76.00
    # Total: 54.00 + 76.00 = 130.00
    expected = Decimal("130.00")
    assert realized_pnl == expected, f"Expected {expected}, got {realized_pnl}"


def test_realized_pnl_add_to_position():
    """
    Test adding to position: BUY 100, BUY 50 more, SELL all 150.
    
    Scenario:
    - BUY 100 @ £10.00, commission £5 → cost = £1,005
    - BUY 50 @ £11.00, commission £3 → cost = £553
    - Total cost = £1,558, avg_cost = £1,558 / 150 = £10.387
    - SELL 150 @ £12.00, commission £7
    """
    transactions = [
        MockTransaction(
            symbol="AAPL",
            side="BUY",
            type="FILL",
            qty=Decimal("100"),
            price=Decimal("10.00"),
            commission=Decimal("5.00"),
            fees=Decimal("0"),
            taxes=Decimal("0"),
        ),
        MockTransaction(
            symbol="AAPL",
            side="BUY",
            type="FILL",
            qty=Decimal("50"),
            price=Decimal("11.00"),
            commission=Decimal("3.00"),
            fees=Decimal("0"),
            taxes=Decimal("0"),
        ),
        MockTransaction(
            symbol="AAPL",
            side="SELL",
            type="EXIT",
            qty=Decimal("150"),
            price=Decimal("12.00"),
            commission=Decimal("7.00"),
            fees=Decimal("0"),
            taxes=Decimal("0"),
        ),
    ]
    
    realized_pnl = calculate_realized_pnl_from_transaction_history(transactions)
    
    # Entry 1: 100 * 10.00 + 5.00 = 1,005.00
    # Entry 2: 50 * 11.00 + 3.00 = 553.00
    # Total cost: 1,558.00, avg_cost = 1,558.00 / 150 = 10.386667
    # Exit: 150 * 12.00 - 7.00 = 1,793.00
    # Realized P&L = 1,793.00 - 1,558.00 = 235.00
    expected = Decimal("235.00")
    assert realized_pnl == expected, f"Expected {expected}, got {realized_pnl}"


def test_realized_pnl_stop_loss():
    """
    Test stop loss exit (SL type).
    
    Scenario:
    - BUY 100 @ £10.00, commission £5
    - SL triggers at £9.00, commission £5
    - Loss = (£9.00 - £10.05) × 100 - £5 = -£105 - £5 = -£110
    """
    transactions = [
        MockTransaction(
            symbol="AAPL",
            side="BUY",
            type="FILL",
            qty=Decimal("100"),
            price=Decimal("10.00"),
            commission=Decimal("5.00"),
            fees=Decimal("0"),
            taxes=Decimal("0"),
        ),
        MockTransaction(
            symbol="AAPL",
            side="SELL",
            type="SL",
            qty=Decimal("100"),
            price=Decimal("9.00"),
            commission=Decimal("5.00"),
            fees=Decimal("0"),
            taxes=Decimal("0"),
        ),
    ]
    
    realized_pnl = calculate_realized_pnl_from_transaction_history(transactions)
    
    # (9.00 - 10.05) * 100 - 5.00 = -105.00 - 5.00 = -110.00
    expected = Decimal("-110.00")
    assert realized_pnl == expected, f"Expected {expected}, got {realized_pnl}"


def test_realized_pnl_take_profit():
    """
    Test take profit exit (TP type).
    """
    transactions = [
        MockTransaction(
            symbol="AAPL",
            side="BUY",
            type="FILL",
            qty=Decimal("100"),
            price=Decimal("10.00"),
            commission=Decimal("5.00"),
            fees=Decimal("0"),
            taxes=Decimal("0"),
        ),
        MockTransaction(
            symbol="AAPL",
            side="SELL",
            type="TP",
            qty=Decimal("100"),
            price=Decimal("15.00"),
            commission=Decimal("5.00"),
            fees=Decimal("0"),
            taxes=Decimal("0"),
        ),
    ]
    
    realized_pnl = calculate_realized_pnl_from_transaction_history(transactions)
    
    # (15.00 - 10.05) * 100 - 5.00 = 495.00 - 5.00 = 490.00
    expected = Decimal("490.00")
    assert realized_pnl == expected, f"Expected {expected}, got {realized_pnl}"


def test_realized_pnl_multiple_symbols():
    """
    Test realized P&L across multiple symbols.
    
    Scenario:
    - AAPL: BUY 100 @ £10, SELL 100 @ £12
    - MSFT: BUY 50 @ £20, SELL 50 @ £22
    """
    transactions = [
        # AAPL
        MockTransaction(
            symbol="AAPL",
            side="BUY",
            type="FILL",
            qty=Decimal("100"),
            price=Decimal("10.00"),
            commission=Decimal("5.00"),
            fees=Decimal("0"),
            taxes=Decimal("0"),
        ),
        MockTransaction(
            symbol="AAPL",
            side="SELL",
            type="EXIT",
            qty=Decimal("100"),
            price=Decimal("12.00"),
            commission=Decimal("5.00"),
            fees=Decimal("0"),
            taxes=Decimal("0"),
        ),
        # MSFT
        MockTransaction(
            symbol="MSFT",
            side="BUY",
            type="FILL",
            qty=Decimal("50"),
            price=Decimal("20.00"),
            commission=Decimal("5.00"),
            fees=Decimal("0"),
            taxes=Decimal("0"),
        ),
        MockTransaction(
            symbol="MSFT",
            side="SELL",
            type="EXIT",
            qty=Decimal("50"),
            price=Decimal("22.00"),
            commission=Decimal("5.00"),
            fees=Decimal("0"),
            taxes=Decimal("0"),
        ),
    ]
    
    realized_pnl = calculate_realized_pnl_from_transaction_history(transactions)
    
    # AAPL: (12.00 - 10.05) * 100 - 5.00 = 190.00
    # MSFT: (22.00 - 20.10) * 50 - 5.00 = 95.00 - 5.00 = 90.00
    # Total: 190.00 + 90.00 = 280.00
    expected = Decimal("280.00")
    assert realized_pnl == expected, f"Expected {expected}, got {realized_pnl}"


def test_realized_pnl_with_fees_and_taxes():
    """
    Test realized P&L calculation including fees and taxes.
    """
    transactions = [
        MockTransaction(
            symbol="AAPL",
            side="BUY",
            type="FILL",
            qty=Decimal("100"),
            price=Decimal("10.00"),
            commission=Decimal("5.00"),
            fees=Decimal("1.00"),
            taxes=Decimal("0.50"),
        ),
        MockTransaction(
            symbol="AAPL",
            side="SELL",
            type="EXIT",
            qty=Decimal("100"),
            price=Decimal("12.00"),
            commission=Decimal("5.00"),
            fees=Decimal("1.00"),
            taxes=Decimal("0.50"),
        ),
    ]
    
    realized_pnl = calculate_realized_pnl_from_transaction_history(transactions)
    
    # Entry cost: 100 * 10.00 + 5.00 + 1.00 + 0.50 = 1,006.50
    # Avg cost: 1,006.50 / 100 = 10.065
    # Exit proceeds: 100 * 12.00 - 5.00 - 1.00 - 0.50 = 1,193.50
    # Realized P&L: 1,193.50 - 1,006.50 = 187.00
    expected = Decimal("187.00")
    assert realized_pnl == expected, f"Expected {expected}, got {realized_pnl}"


def test_realized_pnl_no_exits():
    """
    Test that realized P&L is zero when there are no exits (only BUY).
    """
    transactions = [
        MockTransaction(
            symbol="AAPL",
            side="BUY",
            type="FILL",
            qty=Decimal("100"),
            price=Decimal("10.00"),
            commission=Decimal("5.00"),
            fees=Decimal("0"),
            taxes=Decimal("0"),
        ),
    ]
    
    realized_pnl = calculate_realized_pnl_from_transaction_history(transactions)
    
    expected = Decimal("0.00")
    assert realized_pnl == expected, f"Expected {expected}, got {realized_pnl}"


def test_realized_pnl_empty_transactions():
    """
    Test that realized P&L is zero for empty transaction list.
    """
    transactions = []
    
    realized_pnl = calculate_realized_pnl_from_transaction_history(transactions)
    
    expected = Decimal("0.00")
    assert realized_pnl == expected, f"Expected {expected}, got {realized_pnl}"


def test_realized_pnl_with_fx_conversion():
    """
    Test realized P&L with FX conversion (USD to GBP).
    
    Scenario:
    - BUY 100 AAPL @ $10.00, FX = 0.8 (USD to GBP) → £8.00 per share
    - SELL 100 AAPL @ $12.00, FX = 0.75 → £9.00 per share
    """
    transactions = [
        MockTransaction(
            symbol="AAPL",
            side="BUY",
            type="FILL",
            qty=Decimal("100"),
            price=Decimal("10.00"),
            commission=Decimal("5.00"),
            fees=Decimal("0"),
            taxes=Decimal("0"),
            fx=Decimal("0.8"),  # $1 = £0.80
        ),
        MockTransaction(
            symbol="AAPL",
            side="SELL",
            type="EXIT",
            qty=Decimal("100"),
            price=Decimal("12.00"),
            commission=Decimal("5.00"),
            fees=Decimal("0"),
            taxes=Decimal("0"),
            fx=Decimal("0.75"),  # $1 = £0.75
        ),
    ]
    
    realized_pnl = calculate_realized_pnl_from_transaction_history(transactions)
    
    # Entry: 100 * 10.00 * 0.8 + 5.00 = 800.00 + 5.00 = 805.00
    # Avg cost: 805.00 / 100 = 8.05
    # Exit: 100 * 12.00 * 0.75 - 5.00 = 900.00 - 5.00 = 895.00
    # Realized P&L: 895.00 - 805.00 = 90.00
    expected = Decimal("90.00")
    assert realized_pnl == expected, f"Expected {expected}, got {realized_pnl}"
