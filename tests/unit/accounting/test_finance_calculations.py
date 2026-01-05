"""
Unit tests for finance calculation helpers.
"""

from decimal import Decimal

from aletrader.finance.accounting.domain.calculations import (
    calculate_equity,
    calculate_total_pnl,
    calculate_total_pnl_pct,
)
from aletrader.finance.accounting.domain.position_calculations import (
    calculate_unrealized_pnl,
)


def test_calculate_equity_basic() -> None:
    """Test basic equity calculation."""
    result = calculate_equity(Decimal("1000"), Decimal("500"))
    assert result == Decimal("1500.000000")


def test_calculate_equity_zero_positions() -> None:
    """Test equity with zero positions."""
    result = calculate_equity(Decimal("1000"), Decimal("0"))
    assert result == Decimal("1000.000000")


def test_calculate_equity_negative_cash() -> None:
    """Test equity with negative cash (should be allowed for calculation)."""
    result = calculate_equity(Decimal("-100"), Decimal("500"))
    assert result == Decimal("400.000000")


def test_calculate_total_pnl_basic() -> None:
    """Test basic total P&L calculation."""
    result = calculate_total_pnl(Decimal("10000"), Decimal("11000"))
    assert result == Decimal("1000.000000")


def test_calculate_total_pnl_loss() -> None:
    """Test total P&L with loss."""
    result = calculate_total_pnl(Decimal("10000"), Decimal("9000"))
    assert result == Decimal("-1000.000000")


def test_calculate_total_pnl_no_change() -> None:
    """Test total P&L when equity equals initial equity."""
    result = calculate_total_pnl(Decimal("10000"), Decimal("10000"))
    assert result == Decimal("0.000000")


def test_calculate_total_pnl_precision() -> None:
    """Test total P&L calculation preserves precision."""
    result = calculate_total_pnl(Decimal("10000.123456"), Decimal("10050.789012"))
    assert result == Decimal("50.665556")


def test_calculate_total_pnl_pct_basic() -> None:
    """Test basic total P&L percentage calculation using initial_equity as denominator."""
    result = calculate_total_pnl_pct(Decimal("1000"), Decimal("10000"))
    assert result == Decimal("10.0000")


def test_calculate_total_pnl_pct_loss() -> None:
    """Test total P&L percentage with loss."""
    result = calculate_total_pnl_pct(Decimal("-1000"), Decimal("10000"))
    assert result == Decimal("-10.0000")


def test_calculate_total_pnl_pct_zero_initial_equity() -> None:
    """Test total P&L percentage with zero initial equity (should return 0)."""
    result = calculate_total_pnl_pct(Decimal("1000"), Decimal("0"))
    assert result == Decimal("0.0000")


def test_calculate_total_pnl_pct_negative_initial_equity() -> None:
    """Test total P&L percentage with negative initial equity (should return 0)."""
    result = calculate_total_pnl_pct(Decimal("1000"), Decimal("-1000"))
    assert result == Decimal("0.0000")


def test_calculate_total_pnl_pct_no_change() -> None:
    """Test total P&L percentage when P&L is zero."""
    result = calculate_total_pnl_pct(Decimal("0"), Decimal("10000"))
    assert result == Decimal("0.0000")


def test_calculate_total_pnl_pct_precision() -> None:
    """Test total P&L percentage calculation preserves precision."""
    result = calculate_total_pnl_pct(Decimal("137.25"), Decimal("5000"))
    assert result == Decimal("2.7450")


def test_calculate_unrealized_pnl_basic() -> None:
    """Test basic unrealized P&L calculation."""
    result = calculate_unrealized_pnl(Decimal("10"), Decimal("110"), Decimal("1.0"), Decimal("100"))
    assert result == Decimal("100.000000")


def test_calculate_unrealized_pnl_loss() -> None:
    """Test unrealized P&L with loss."""
    result = calculate_unrealized_pnl(Decimal("10"), Decimal("90"), Decimal("1.0"), Decimal("100"))
    assert result == Decimal("-100.000000")


def test_calculate_unrealized_pnl_with_fx() -> None:
    """Test unrealized P&L with FX rate."""
    result = calculate_unrealized_pnl(Decimal("10"), Decimal("100"), Decimal("1.5"), Decimal("100"))
    assert result == Decimal("500.000000")


def test_calculate_unrealized_pnl_zero_qty() -> None:
    """Test unrealized P&L with zero quantity."""
    result = calculate_unrealized_pnl(Decimal("0"), Decimal("100"), Decimal("1.0"), Decimal("100"))
    assert result == Decimal("0.000000")
