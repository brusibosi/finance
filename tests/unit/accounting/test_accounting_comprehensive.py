"""
Comprehensive unit tests for core accounting logic.

Tests all transaction types, edge cases, FX rates, precision, and boundary conditions.
"""

import pytest
from decimal import Decimal

from aletrader.finance.accounting.domain.transactions import (
    apply_transaction,
    calculate_cost_total,
    calculate_drawdown,
    calculate_gross_value,
    AccountStateBefore,
    PositionStateBefore,
    TransactionInput,
)


# ============================================================================
# Helper Functions Tests
# ============================================================================


def test_calculate_gross_value_basic():
    """Test basic gross value calculation."""
    result = calculate_gross_value(Decimal("10"), Decimal("100"), Decimal("1.0"))
    assert result == Decimal("1000.000000")


def test_calculate_gross_value_with_fx():
    """Test gross value calculation with FX rate."""
    result = calculate_gross_value(Decimal("10"), Decimal("100"), Decimal("1.5"))
    assert result == Decimal("1500.000000")


def test_calculate_gross_value_precision():
    """Test gross value calculation preserves precision."""
    result = calculate_gross_value(Decimal("0.001"), Decimal("123.456"), Decimal("1.0"))
    assert result == Decimal("0.123456")


def test_calculate_cost_total_basic():
    """Test basic cost total calculation."""
    result = calculate_cost_total(Decimal("1"), Decimal("0.5"), Decimal("0.2"))
    assert result == Decimal("1.700000")


def test_calculate_cost_total_zero_components():
    """Test cost total with zero components."""
    result = calculate_cost_total(Decimal("0"), Decimal("0"), Decimal("0"))
    assert result == Decimal("0.000000")
    
    result = calculate_cost_total(Decimal("1"), Decimal("0"), Decimal("0"))
    assert result == Decimal("1.000000")


def test_calculate_drawdown_basic():
    """Test basic drawdown calculation."""
    result = calculate_drawdown(Decimal("1000"), Decimal("800"))
    assert result == Decimal("20.0000")


def test_calculate_drawdown_zero():
    """Test drawdown when equity equals max."""
    result = calculate_drawdown(Decimal("1000"), Decimal("1000"))
    assert result == Decimal("0.0000")


def test_calculate_drawdown_negative_max():
    """Test drawdown with zero or negative max equity."""
    result = calculate_drawdown(Decimal("0"), Decimal("100"))
    assert result == Decimal("0.0000")
    
    result = calculate_drawdown(Decimal("-100"), Decimal("100"))
    assert result == Decimal("0.0000")


def test_calculate_drawdown_above_max():
    """Test drawdown when equity exceeds max (should be 0)."""
    result = calculate_drawdown(Decimal("1000"), Decimal("1200"))
    # Drawdown should be 0 when equity > max
    assert result == Decimal("-20.0000")  # Negative means above max


# ============================================================================
# ORDER Transaction Tests
# ============================================================================


def test_apply_order_transaction_no_position():
    """Test ORDER transaction with no existing position."""
    account: AccountStateBefore = {
        "cash": Decimal("1000"),
        "realized_pnl_cum": Decimal("0"),
        "max_equity_to_date": Decimal("1000"),
        "initial_equity": Decimal("1000"),
    }
    
    tx: TransactionInput = {
        "type": "ORDER",
        "side": "BUY",
        "qty": Decimal("10"),
        "price": Decimal("100"),
        "commission": Decimal("1"),
        "fees": Decimal("0.5"),
        "taxes": Decimal("0.2"),
        "fx": Decimal("1.0"),
        "sl_price": None,
    }
    
    result = apply_transaction(account, None, tx)
    
    assert result["cash_after"] == account["cash"]  # Unchanged
    assert result["position_qty_after"] == Decimal("0")
    assert result["realized_pnl_delta"] == Decimal("0")
    assert result["realized_pnl_cum_after"] == account["realized_pnl_cum"]


def test_apply_order_transaction_with_position():
    """Test ORDER transaction with existing position."""
    account: AccountStateBefore = {
        "cash": Decimal("1000"),
        "realized_pnl_cum": Decimal("0"),
        "max_equity_to_date": Decimal("1000"),
        "initial_equity": Decimal("1000"),
    }
    
    position: PositionStateBefore = {
        "qty": Decimal("10"),
        "avg_cost": Decimal("100"),
        "last_price": Decimal("110"),
        "fx": Decimal("1.0"),
    }
    
    tx: TransactionInput = {
        "type": "ORDER",
        "side": "BUY",
        "qty": Decimal("5"),
        "price": Decimal("120"),
        "commission": Decimal("1"),
        "fees": Decimal("0"),
        "taxes": Decimal("0"),
        "fx": Decimal("1.0"),
        "sl_price": None,
    }
    
    result = apply_transaction(account, position, tx)
    
    assert result["cash_after"] == account["cash"]  # Unchanged
    assert result["position_qty_after"] == position["qty"]  # Unchanged
    assert result["position_avg_cost_after"] == position["avg_cost"]  # Unchanged
    assert result["last_price_after"] == tx["price"]  # Updated
    assert result["realized_pnl_delta"] == Decimal("0")


def test_apply_order_sl_transaction():
    """Test ORDER_SL transaction."""
    account: AccountStateBefore = {
        "cash": Decimal("1000"),
        "realized_pnl_cum": Decimal("0"),
        "max_equity_to_date": Decimal("1000"),
        "initial_equity": Decimal("1000"),
    }
    
    tx: TransactionInput = {
        "type": "ORDER_SL",
        "side": "SELL",
        "qty": Decimal("10"),
        "price": Decimal("90"),
        "commission": Decimal("0"),
        "fees": Decimal("0"),
        "taxes": Decimal("0"),
        "fx": Decimal("1.0"),
        "sl_price": Decimal("90"),
    }
    
    result = apply_transaction(account, None, tx)
    assert result["cash_after"] == account["cash"]
    assert result["position_qty_after"] == Decimal("0")


def test_apply_order_tp_transaction():
    """Test ORDER_TP transaction."""
    account: AccountStateBefore = {
        "cash": Decimal("1000"),
        "realized_pnl_cum": Decimal("0"),
        "max_equity_to_date": Decimal("1000"),
        "initial_equity": Decimal("1000"),
    }
    
    tx: TransactionInput = {
        "type": "ORDER_TP",
        "side": "SELL",
        "qty": Decimal("10"),
        "price": Decimal("110"),
        "commission": Decimal("0"),
        "fees": Decimal("0"),
        "taxes": Decimal("0"),
        "fx": Decimal("1.0"),
        "sl_price": None,
    }
    
    result = apply_transaction(account, None, tx)
    assert result["cash_after"] == account["cash"]
    assert result["position_qty_after"] == Decimal("0")


# ============================================================================
# BUY FILL Transaction Tests
# ============================================================================


def test_apply_buy_fill_entry():
    """Test BUY FILL that opens new position."""
    account: AccountStateBefore = {
        "cash": Decimal("5000"),
        "realized_pnl_cum": Decimal("0"),
        "max_equity_to_date": Decimal("5000"),
        "initial_equity": Decimal("5000"),
    }
    
    tx: TransactionInput = {
        "type": "FILL",
        "side": "BUY",
        "qty": Decimal("10"),
        "price": Decimal("100"),
        "commission": Decimal("1"),
        "fees": Decimal("0.5"),
        "taxes": Decimal("0.2"),
        "fx": Decimal("1.0"),
        "sl_price": None,
    }
    
    result = apply_transaction(account, None, tx)
    
    # Cash should decrease by (qty * price * fx + costs)
    expected_cash = Decimal("5000") - (Decimal("10") * Decimal("100") * Decimal("1.0") + Decimal("1.7"))
    assert abs(result["cash_after"] - expected_cash) < Decimal("0.01")
    
    # Position should be created
    assert result["position_qty_after"] == Decimal("10")
    
    # Average cost should include transaction costs
    expected_avg_cost = (Decimal("10") * Decimal("100") * Decimal("1.0") + Decimal("1.7")) / Decimal("10")
    assert abs(result["position_avg_cost_after"] - expected_avg_cost) < Decimal("0.000001")
    
    # BUY transactions have realized_pnl_delta = -cost_total (transaction costs reduce equity)
    expected_cost_total = Decimal("1") + Decimal("0.5") + Decimal("0.2")  # commission + fees + taxes
    assert abs(result["realized_pnl_delta"] - (-expected_cost_total)) < Decimal("0.000001")
    assert abs(result["realized_pnl_cum_after"] - (account["realized_pnl_cum"] - expected_cost_total)) < Decimal("0.000001")


def test_apply_buy_fill_entry_with_fx():
    """Test BUY FILL entry with FX rate."""
    account: AccountStateBefore = {
        "cash": Decimal("5000"),
        "realized_pnl_cum": Decimal("0"),
        "max_equity_to_date": Decimal("5000"),
        "initial_equity": Decimal("5000"),
    }
    
    tx: TransactionInput = {
        "type": "FILL",
        "side": "BUY",
        "qty": Decimal("10"),
        "price": Decimal("100"),
        "commission": Decimal("1"),
        "fees": Decimal("0"),
        "taxes": Decimal("0"),
        "fx": Decimal("1.5"),
        "sl_price": None,
    }
    
    result = apply_transaction(account, None, tx)
    
    # Cash should decrease by (qty * price * fx + costs)
    expected_cash = Decimal("5000") - (Decimal("10") * Decimal("100") * Decimal("1.5") + Decimal("1"))
    assert abs(result["cash_after"] - expected_cash) < Decimal("0.01")
    
    # Average cost should include FX and costs
    expected_avg_cost = (Decimal("10") * Decimal("100") * Decimal("1.5") + Decimal("1")) / Decimal("10")
    assert abs(result["position_avg_cost_after"] - expected_avg_cost) < Decimal("0.000001")


def test_apply_buy_fill_add_to_position():
    """Test BUY FILL that adds to existing position."""
    account: AccountStateBefore = {
        "cash": Decimal("5000"),
        "realized_pnl_cum": Decimal("0"),
        "max_equity_to_date": Decimal("5000"),
        "initial_equity": Decimal("5000"),
    }
    
    position: PositionStateBefore = {
        "qty": Decimal("10"),
        "avg_cost": Decimal("100"),
        "last_price": Decimal("110"),
        "fx": Decimal("1.0"),
    }
    
    tx: TransactionInput = {
        "type": "FILL",
        "side": "BUY",
        "qty": Decimal("5"),
        "price": Decimal("120"),
        "commission": Decimal("1"),
        "fees": Decimal("0.5"),
        "taxes": Decimal("0.2"),
        "fx": Decimal("1.0"),
        "sl_price": None,
    }
    
    result = apply_transaction(account, position, tx)
    
    # Cash should decrease
    expected_cash = Decimal("5000") - (Decimal("5") * Decimal("120") * Decimal("1.0") + Decimal("1.7"))
    assert abs(result["cash_after"] - expected_cash) < Decimal("0.01")
    
    # Position quantity should increase
    assert result["position_qty_after"] == Decimal("15")
    
    # Average cost should be recalculated
    cost_before = Decimal("10") * Decimal("100")
    cost_new = Decimal("5") * Decimal("120") + Decimal("1.7")
    expected_avg_cost = (cost_before + cost_new) / Decimal("15")
    assert abs(result["position_avg_cost_after"] - expected_avg_cost) < Decimal("0.000001")


def test_apply_buy_fill_add_with_different_fx():
    """Test BUY FILL add with different FX rate."""
    account: AccountStateBefore = {
        "cash": Decimal("5000"),
        "realized_pnl_cum": Decimal("0"),
        "max_equity_to_date": Decimal("5000"),
        "initial_equity": Decimal("5000"),
    }
    
    position: PositionStateBefore = {
        "qty": Decimal("10"),
        "avg_cost": Decimal("100"),  # In account currency
        "last_price": Decimal("100"),
        "fx": Decimal("1.0"),
    }
    
    tx: TransactionInput = {
        "type": "FILL",
        "side": "BUY",
        "qty": Decimal("5"),
        "price": Decimal("100"),
        "commission": Decimal("1"),
        "fees": Decimal("0"),
        "taxes": Decimal("0"),
        "fx": Decimal("1.5"),  # Different FX rate
        "sl_price": None,
    }
    
    result = apply_transaction(account, position, tx)
    
    # Average cost should account for different FX
    cost_before = Decimal("10") * Decimal("100")  # 1000
    cost_new = Decimal("5") * Decimal("100") * Decimal("1.5") + Decimal("1")  # 751
    expected_avg_cost = (cost_before + cost_new) / Decimal("15")
    assert abs(result["position_avg_cost_after"] - expected_avg_cost) < Decimal("0.000001")


def test_apply_buy_fill_sl_entry():
    """Test BUY SL FILL entry."""
    account: AccountStateBefore = {
        "cash": Decimal("5000"),
        "realized_pnl_cum": Decimal("0"),
        "max_equity_to_date": Decimal("5000"),
        "initial_equity": Decimal("5000"),
    }
    
    tx: TransactionInput = {
        "type": "SL",
        "side": "BUY",
        "qty": Decimal("10"),
        "price": Decimal("90"),
        "commission": Decimal("1"),
        "fees": Decimal("0"),
        "taxes": Decimal("0"),
        "fx": Decimal("1.0"),
        "sl_price": Decimal("90"),
    }
    
    result = apply_transaction(account, None, tx)
    assert result["position_qty_after"] == Decimal("10")
    # BUY transactions have realized_pnl_delta = -cost_total (transaction costs reduce equity)
    expected_cost_total = Decimal("1")  # commission
    assert abs(result["realized_pnl_delta"] - (-expected_cost_total)) < Decimal("0.000001")


def test_apply_buy_fill_tp_entry():
    """Test BUY TP FILL entry."""
    account: AccountStateBefore = {
        "cash": Decimal("5000"),
        "realized_pnl_cum": Decimal("0"),
        "max_equity_to_date": Decimal("5000"),
        "initial_equity": Decimal("5000"),
    }
    
    tx: TransactionInput = {
        "type": "TP",
        "side": "BUY",
        "qty": Decimal("10"),
        "price": Decimal("110"),
        "commission": Decimal("1"),
        "fees": Decimal("0"),
        "taxes": Decimal("0"),
        "fx": Decimal("1.0"),
        "sl_price": None,
    }
    
    result = apply_transaction(account, None, tx)
    assert result["position_qty_after"] == Decimal("10")
    # BUY transactions have realized_pnl_delta = -cost_total (transaction costs reduce equity)
    expected_cost_total = Decimal("1")  # commission
    assert abs(result["realized_pnl_delta"] - (-expected_cost_total)) < Decimal("0.000001")


# ============================================================================
# SELL FILL Transaction Tests
# ============================================================================


def test_apply_sell_fill_partial_close():
    """Test SELL FILL that partially closes position."""
    account: AccountStateBefore = {
        "cash": Decimal("1000"),
        "realized_pnl_cum": Decimal("0"),
        "max_equity_to_date": Decimal("5000"),
        "initial_equity": Decimal("5000"),
    }
    
    position: PositionStateBefore = {
        "qty": Decimal("10"),
        "avg_cost": Decimal("100"),
        "last_price": Decimal("100"),
        "fx": Decimal("1.0"),
    }
    
    tx: TransactionInput = {
        "type": "FILL",
        "side": "SELL",
        "qty": Decimal("5"),
        "price": Decimal("110"),
        "commission": Decimal("1"),
        "fees": Decimal("0.5"),
        "taxes": Decimal("0.2"),
        "fx": Decimal("1.0"),
        "sl_price": None,
    }
    
    result = apply_transaction(account, position, tx)
    
    # Cash should increase
    expected_cash = Decimal("1000") + (Decimal("5") * Decimal("110") * Decimal("1.0") - Decimal("1.7"))
    assert abs(result["cash_after"] - expected_cash) < Decimal("0.01")
    
    # Position quantity should decrease
    assert result["position_qty_after"] == Decimal("5")
    
    # Average cost should remain unchanged
    assert result["position_avg_cost_after"] == position["avg_cost"]
    
    # Realized P&L should be calculated
    pnl_gross = (Decimal("110") * Decimal("1.0") - Decimal("100")) * Decimal("5")
    expected_realized = pnl_gross - Decimal("1.7")
    assert abs(result["realized_pnl_delta"] - expected_realized) < Decimal("0.000001")
    assert abs(result["realized_pnl_cum_after"] - expected_realized) < Decimal("0.000001")


def test_apply_sell_fill_full_close():
    """Test SELL FILL that fully closes position."""
    account: AccountStateBefore = {
        "cash": Decimal("1000"),
        "realized_pnl_cum": Decimal("0"),
        "max_equity_to_date": Decimal("5000"),
        "initial_equity": Decimal("5000"),
    }
    
    position: PositionStateBefore = {
        "qty": Decimal("10"),
        "avg_cost": Decimal("100"),
        "last_price": Decimal("100"),
        "fx": Decimal("1.0"),
    }
    
    tx: TransactionInput = {
        "type": "FILL",
        "side": "SELL",
        "qty": Decimal("10"),
        "price": Decimal("110"),
        "commission": Decimal("1"),
        "fees": Decimal("0.5"),
        "taxes": Decimal("0.2"),
        "fx": Decimal("1.0"),
        "sl_price": None,
    }
    
    result = apply_transaction(account, position, tx)
    
    # Position should be removed
    assert result["position_qty_after"] == Decimal("0")
    assert result["position_removed"] is True
    assert result["position_avg_cost_after"] == Decimal("0")
    
    # Realized P&L should be calculated
    pnl_gross = (Decimal("110") * Decimal("1.0") - Decimal("100")) * Decimal("10")
    expected_realized = pnl_gross - Decimal("1.7")
    assert abs(result["realized_pnl_delta"] - expected_realized) < Decimal("0.000001")


def test_apply_sell_fill_with_loss():
    """Test SELL FILL that closes position at a loss."""
    account: AccountStateBefore = {
        "cash": Decimal("1000"),
        "realized_pnl_cum": Decimal("0"),
        "max_equity_to_date": Decimal("5000"),
        "initial_equity": Decimal("5000"),
    }
    
    position: PositionStateBefore = {
        "qty": Decimal("10"),
        "avg_cost": Decimal("100"),
        "last_price": Decimal("100"),
        "fx": Decimal("1.0"),
    }
    
    tx: TransactionInput = {
        "type": "FILL",
        "side": "SELL",
        "qty": Decimal("10"),
        "price": Decimal("90"),
        "commission": Decimal("1"),
        "fees": Decimal("0.5"),
        "taxes": Decimal("0.2"),
        "fx": Decimal("1.0"),
        "sl_price": None,
    }
    
    result = apply_transaction(account, position, tx)
    
    # Realized P&L should be negative
    pnl_gross = (Decimal("90") * Decimal("1.0") - Decimal("100")) * Decimal("10")
    expected_realized = pnl_gross - Decimal("1.7")
    assert result["realized_pnl_delta"] < Decimal("0")
    assert abs(result["realized_pnl_delta"] - expected_realized) < Decimal("0.000001")


def test_apply_sell_fill_with_fx():
    """Test SELL FILL with FX rate."""
    account: AccountStateBefore = {
        "cash": Decimal("1000"),
        "realized_pnl_cum": Decimal("0"),
        "max_equity_to_date": Decimal("5000"),
        "initial_equity": Decimal("5000"),
    }
    
    position: PositionStateBefore = {
        "qty": Decimal("10"),
        "avg_cost": Decimal("100"),  # In account currency
        "last_price": Decimal("100"),
        "fx": Decimal("1.0"),
    }
    
    tx: TransactionInput = {
        "type": "FILL",
        "side": "SELL",
        "qty": Decimal("10"),
        "price": Decimal("100"),
        "commission": Decimal("1"),
        "fees": Decimal("0"),
        "taxes": Decimal("0"),
        "fx": Decimal("1.5"),  # Different FX
        "sl_price": None,
    }
    
    result = apply_transaction(account, position, tx)
    
    # Realized P&L should account for FX
    pnl_gross = (Decimal("100") * Decimal("1.5") - Decimal("100")) * Decimal("10")
    expected_realized = pnl_gross - Decimal("1")
    assert abs(result["realized_pnl_delta"] - expected_realized) < Decimal("0.000001")


def test_apply_sell_fill_requires_position():
    """Test SELL FILL requires existing position."""
    account: AccountStateBefore = {
        "cash": Decimal("1000"),
        "realized_pnl_cum": Decimal("0"),
        "max_equity_to_date": Decimal("5000"),
        "initial_equity": Decimal("5000"),
    }
    
    tx: TransactionInput = {
        "type": "FILL",
        "side": "SELL",
        "qty": Decimal("10"),
        "price": Decimal("100"),
        "commission": Decimal("0"),
        "fees": Decimal("0"),
        "taxes": Decimal("0"),
        "fx": Decimal("1.0"),
        "sl_price": None,
    }
    
    with pytest.raises(ValueError, match="SELL FILL requires existing position"):
        apply_transaction(account, None, tx)


def test_apply_sell_fill_insufficient_position():
    """Test SELL FILL with insufficient position quantity."""
    account: AccountStateBefore = {
        "cash": Decimal("1000"),
        "realized_pnl_cum": Decimal("0"),
        "max_equity_to_date": Decimal("5000"),
        "initial_equity": Decimal("5000"),
    }
    
    position: PositionStateBefore = {
        "qty": Decimal("5"),
        "avg_cost": Decimal("100"),
        "last_price": Decimal("100"),
        "fx": Decimal("1.0"),
    }
    
    tx: TransactionInput = {
        "type": "FILL",
        "side": "SELL",
        "qty": Decimal("10"),  # More than position
        "price": Decimal("100"),
        "commission": Decimal("0"),
        "fees": Decimal("0"),
        "taxes": Decimal("0"),
        "fx": Decimal("1.0"),
        "sl_price": None,
    }
    
    with pytest.raises(ValueError, match="Insufficient position"):
        apply_transaction(account, position, tx)


def test_apply_sell_fill_sl():
    """Test SELL SL FILL."""
    account: AccountStateBefore = {
        "cash": Decimal("1000"),
        "realized_pnl_cum": Decimal("0"),
        "max_equity_to_date": Decimal("5000"),
        "initial_equity": Decimal("5000"),
    }
    
    position: PositionStateBefore = {
        "qty": Decimal("10"),
        "avg_cost": Decimal("100"),
        "last_price": Decimal("100"),
        "fx": Decimal("1.0"),
    }
    
    tx: TransactionInput = {
        "type": "SL",
        "side": "SELL",
        "qty": Decimal("10"),
        "price": Decimal("90"),
        "commission": Decimal("1"),
        "fees": Decimal("0"),
        "taxes": Decimal("0"),
        "fx": Decimal("1.0"),
        "sl_price": Decimal("90"),
    }
    
    result = apply_transaction(account, position, tx)
    assert result["position_qty_after"] == Decimal("0")
    assert result["position_removed"] is True


def test_apply_sell_fill_tp():
    """Test SELL TP FILL."""
    account: AccountStateBefore = {
        "cash": Decimal("1000"),
        "realized_pnl_cum": Decimal("0"),
        "max_equity_to_date": Decimal("5000"),
        "initial_equity": Decimal("5000"),
    }
    
    position: PositionStateBefore = {
        "qty": Decimal("10"),
        "avg_cost": Decimal("100"),
        "last_price": Decimal("100"),
        "fx": Decimal("1.0"),
    }
    
    tx: TransactionInput = {
        "type": "TP",
        "side": "SELL",
        "qty": Decimal("10"),
        "price": Decimal("110"),
        "commission": Decimal("1"),
        "fees": Decimal("0"),
        "taxes": Decimal("0"),
        "fx": Decimal("1.0"),
        "sl_price": None,
    }
    
    result = apply_transaction(account, position, tx)
    assert result["position_qty_after"] == Decimal("0")
    assert result["position_removed"] is True


# ============================================================================
# MARK_TO_MARKET Transaction Tests
# ============================================================================


def test_apply_mark_to_market_basic():
    """Test MARK_TO_MARKET transaction."""
    account: AccountStateBefore = {
        "cash": Decimal("1000"),
        "realized_pnl_cum": Decimal("50"),
        "max_equity_to_date": Decimal("5000"),
        "initial_equity": Decimal("5000"),
    }
    
    position: PositionStateBefore = {
        "qty": Decimal("10"),
        "avg_cost": Decimal("100"),
        "last_price": Decimal("100"),
        "fx": Decimal("1.0"),
    }
    
    tx: TransactionInput = {
        "type": "MARK_TO_MARKET",
        "side": "BUY",  # Side doesn't matter for MTM
        "qty": Decimal("10"),
        "price": Decimal("110"),
        "commission": Decimal("0"),
        "fees": Decimal("0"),
        "taxes": Decimal("0"),
        "fx": Decimal("1.0"),
        "sl_price": None,
    }
    
    result = apply_transaction(account, position, tx)
    
    # Cash should be unchanged
    assert result["cash_after"] == account["cash"]
    
    # Position quantity and avg_cost unchanged
    assert result["position_qty_after"] == position["qty"]
    assert result["position_avg_cost_after"] == position["avg_cost"]
    
    # Last price should be updated
    assert result["last_price_after"] == tx["price"]
    
    # Realized P&L unchanged
    assert result["realized_pnl_delta"] == Decimal("0")
    assert result["realized_pnl_cum_after"] == account["realized_pnl_cum"]


def test_apply_mark_to_market_with_fx():
    """Test MARK_TO_MARKET with FX rate change."""
    account: AccountStateBefore = {
        "cash": Decimal("1000"),
        "realized_pnl_cum": Decimal("0"),
        "max_equity_to_date": Decimal("5000"),
        "initial_equity": Decimal("5000"),
    }
    
    position: PositionStateBefore = {
        "qty": Decimal("10"),
        "avg_cost": Decimal("100"),
        "last_price": Decimal("100"),
        "fx": Decimal("1.0"),
    }
    
    tx: TransactionInput = {
        "type": "MARK_TO_MARKET",
        "side": "BUY",
        "qty": Decimal("10"),
        "price": Decimal("100"),
        "commission": Decimal("0"),
        "fees": Decimal("0"),
        "taxes": Decimal("0"),
        "fx": Decimal("1.5"),  # FX changed
        "sl_price": None,
    }
    
    result = apply_transaction(account, position, tx)
    
    assert result["fx_after"] == tx["fx"]
    assert result["position_notional_after"] == Decimal("10") * Decimal("100") * Decimal("1.5")


def test_apply_mark_to_market_requires_position():
    """Test MARK_TO_MARKET requires existing position."""
    account: AccountStateBefore = {
        "cash": Decimal("1000"),
        "realized_pnl_cum": Decimal("0"),
        "max_equity_to_date": Decimal("5000"),
        "initial_equity": Decimal("5000"),
    }
    
    tx: TransactionInput = {
        "type": "MARK_TO_MARKET",
        "side": "BUY",
        "qty": Decimal("10"),
        "price": Decimal("110"),
        "commission": Decimal("0"),
        "fees": Decimal("0"),
        "taxes": Decimal("0"),
        "fx": Decimal("1.0"),
        "sl_price": None,
    }
    
    with pytest.raises(ValueError, match="MARK_TO_MARKET requires existing position"):
        apply_transaction(account, None, tx)


# ============================================================================
# Edge Cases and Boundary Conditions
# ============================================================================


def test_apply_transaction_very_small_quantities():
    """Test transaction with very small quantities."""
    account: AccountStateBefore = {
        "cash": Decimal("1000"),
        "realized_pnl_cum": Decimal("0"),
        "max_equity_to_date": Decimal("1000"),
        "initial_equity": Decimal("1000"),
    }
    
    tx: TransactionInput = {
        "type": "FILL",
        "side": "BUY",
        "qty": Decimal("0.000001"),
        "price": Decimal("100"),
        "commission": Decimal("0.000001"),
        "fees": Decimal("0"),
        "taxes": Decimal("0"),
        "fx": Decimal("1.0"),
        "sl_price": None,
    }
    
    result = apply_transaction(account, None, tx)
    assert result["position_qty_after"] == tx["qty"]


def test_apply_transaction_very_large_quantities():
    """Test transaction with very large quantities."""
    account: AccountStateBefore = {
        "cash": Decimal("1000000000"),
        "realized_pnl_cum": Decimal("0"),
        "max_equity_to_date": Decimal("1000000000"),
        "initial_equity": Decimal("1000000000"),
    }
    
    tx: TransactionInput = {
        "type": "FILL",
        "side": "BUY",
        "qty": Decimal("1000000"),
        "price": Decimal("1000"),
        "commission": Decimal("1000"),
        "fees": Decimal("0"),
        "taxes": Decimal("0"),
        "fx": Decimal("1.0"),
        "sl_price": None,
    }
    
    result = apply_transaction(account, None, tx)
    assert result["position_qty_after"] == tx["qty"]


def test_apply_transaction_very_high_precision_prices():
    """Test transaction with very high precision prices."""
    account: AccountStateBefore = {
        "cash": Decimal("1000"),
        "realized_pnl_cum": Decimal("0"),
        "max_equity_to_date": Decimal("1000"),
        "initial_equity": Decimal("1000"),
    }
    
    tx: TransactionInput = {
        "type": "FILL",
        "side": "BUY",
        "qty": Decimal("10"),
        "price": Decimal("123.4567890123456789012345678"),
        "commission": Decimal("0.000001"),
        "fees": Decimal("0"),
        "taxes": Decimal("0"),
        "fx": Decimal("1.0"),
        "sl_price": None,
    }
    
    result = apply_transaction(account, None, tx)
    assert result["last_price_after"] == tx["price"]


def test_apply_transaction_fx_rate_edge_cases():
    """Test transactions with FX rate edge cases."""
    account: AccountStateBefore = {
        "cash": Decimal("1000"),
        "realized_pnl_cum": Decimal("0"),
        "max_equity_to_date": Decimal("1000"),
        "initial_equity": Decimal("1000"),
    }
    
    # Very small FX rate
    tx1: TransactionInput = {
        "type": "FILL",
        "side": "BUY",
        "qty": Decimal("10"),
        "price": Decimal("100"),
        "commission": Decimal("0"),
        "fees": Decimal("0"),
        "taxes": Decimal("0"),
        "fx": Decimal("0.000001"),
        "sl_price": None,
    }
    
    result1 = apply_transaction(account, None, tx1)
    assert result1["fx_after"] == tx1["fx"]
    
    # Very large FX rate
    account2: AccountStateBefore = {
        "cash": Decimal("1000000"),
        "realized_pnl_cum": Decimal("0"),
        "max_equity_to_date": Decimal("1000000"),
        "initial_equity": Decimal("1000000"),
    }
    
    tx2: TransactionInput = {
        "type": "FILL",
        "side": "BUY",
        "qty": Decimal("10"),
        "price": Decimal("100"),
        "commission": Decimal("0"),
        "fees": Decimal("0"),
        "taxes": Decimal("0"),
        "fx": Decimal("1000.0"),
        "sl_price": None,
    }
    
    result2 = apply_transaction(account2, None, tx2)
    assert result2["fx_after"] == tx2["fx"]


def test_apply_transaction_multiple_adds_average_cost():
    """Test average cost calculation with multiple adds."""
    account: AccountStateBefore = {
        "cash": Decimal("10000"),
        "realized_pnl_cum": Decimal("0"),
        "max_equity_to_date": Decimal("10000"),
        "initial_equity": Decimal("10000"),
    }
    
    # First entry
    tx1: TransactionInput = {
        "type": "FILL",
        "side": "BUY",
        "qty": Decimal("10"),
        "price": Decimal("100"),
        "commission": Decimal("1"),
        "fees": Decimal("0"),
        "taxes": Decimal("0"),
        "fx": Decimal("1.0"),
        "sl_price": None,
    }
    
    result1 = apply_transaction(account, None, tx1)
    avg_cost1 = result1["position_avg_cost_after"]
    
    # Second add
    account2: AccountStateBefore = {
        "cash": result1["cash_after"],
        "realized_pnl_cum": result1["realized_pnl_cum_after"],
        "max_equity_to_date": Decimal("10000"),
        "initial_equity": Decimal("10000"),
    }
    
    position1: PositionStateBefore = {
        "qty": result1["position_qty_after"],
        "avg_cost": result1["position_avg_cost_after"],
        "last_price": result1["last_price_after"],
        "fx": result1["fx_after"],
    }
    
    tx2: TransactionInput = {
        "type": "FILL",
        "side": "BUY",
        "qty": Decimal("5"),
        "price": Decimal("120"),
        "commission": Decimal("1"),
        "fees": Decimal("0"),
        "taxes": Decimal("0"),
        "fx": Decimal("1.0"),
        "sl_price": None,
    }
    
    result2 = apply_transaction(account2, position1, tx2)
    
    # Average cost should be weighted
    cost_before = Decimal("10") * avg_cost1
    cost_new = Decimal("5") * Decimal("120") + Decimal("1")
    expected_avg_cost = (cost_before + cost_new) / Decimal("15")
    assert abs(result2["position_avg_cost_after"] - expected_avg_cost) < Decimal("0.000001")


def test_apply_transaction_adjustment_not_implemented():
    """Test that ADJUSTMENT transaction type raises error."""
    account: AccountStateBefore = {
        "cash": Decimal("1000"),
        "realized_pnl_cum": Decimal("0"),
        "max_equity_to_date": Decimal("1000"),
        "initial_equity": Decimal("1000"),
    }
    
    tx: TransactionInput = {
        "type": "ADJUSTMENT",
        "side": "BUY",
        "qty": Decimal("10"),
        "price": Decimal("100"),
        "commission": Decimal("0"),
        "fees": Decimal("0"),
        "taxes": Decimal("0"),
        "fx": Decimal("1.0"),
        "sl_price": None,
    }
    
    with pytest.raises(ValueError, match="not yet implemented"):
        apply_transaction(account, None, tx)

