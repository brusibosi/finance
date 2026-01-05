"""
Unit tests for finance aggregation helpers.
"""

from dataclasses import dataclass
from decimal import Decimal

from aletrader.finance.accounting.interfaces import AccountFinancialCalculator


@dataclass(frozen=True)
class PositionStub:
    """Simple position stub for aggregation tests."""

    notional: Decimal
    qty: Decimal
    avg_cost: Decimal
    unrealized_pnl: Decimal


@dataclass(frozen=True)
class ApprovedOrderStub:
    """Simple approved order stub for aggregation tests."""

    risk_amount: Decimal
    final_quantity: Decimal
    strategy_id: str


def test_aggregate_positions_value_sums_notional() -> None:
    positions = [
        PositionStub(
            notional=Decimal("100.50"),
            qty=Decimal("2"),
            avg_cost=Decimal("50.25"),
            unrealized_pnl=Decimal("1.00"),
        ),
        PositionStub(
            notional=Decimal("200.25"),
            qty=Decimal("1"),
            avg_cost=Decimal("200.25"),
            unrealized_pnl=Decimal("-2.00"),
        ),
    ]

    total = AccountFinancialCalculator.aggregate_positions_value(positions)

    assert total == Decimal("300.75")


def test_aggregate_positions_cost_uses_qty_times_avg_cost() -> None:
    positions = [
        PositionStub(
            notional=Decimal("0"),
            qty=Decimal("3"),
            avg_cost=Decimal("10.00"),
            unrealized_pnl=Decimal("0"),
        ),
        PositionStub(
            notional=Decimal("0"),
            qty=Decimal("2"),
            avg_cost=Decimal("7.50"),
            unrealized_pnl=Decimal("0"),
        ),
    ]

    total = AccountFinancialCalculator.aggregate_positions_cost(positions)

    assert total == Decimal("45.00")


def test_aggregate_unrealized_pnl_sums_values() -> None:
    positions = [
        PositionStub(
            notional=Decimal("0"),
            qty=Decimal("1"),
            avg_cost=Decimal("0"),
            unrealized_pnl=Decimal("5.25"),
        ),
        PositionStub(
            notional=Decimal("0"),
            qty=Decimal("1"),
            avg_cost=Decimal("0"),
            unrealized_pnl=Decimal("-1.25"),
        ),
    ]

    total = AccountFinancialCalculator.aggregate_unrealized_pnl(positions)

    assert total == Decimal("4.00")


def test_aggregate_order_risk_respects_filters() -> None:
    orders = [
        ApprovedOrderStub(
            risk_amount=Decimal("10.00"),
            final_quantity=Decimal("5"),
            strategy_id="STRAT_A",
        ),
        ApprovedOrderStub(
            risk_amount=Decimal("0"),
            final_quantity=Decimal("7"),
            strategy_id="STRAT_A",
        ),
        ApprovedOrderStub(
            risk_amount=Decimal("3.25"),
            final_quantity=Decimal("-1"),
            strategy_id="STRAT_B",
        ),
    ]

    total_risk, total_quantity = AccountFinancialCalculator.aggregate_order_risk(orders)

    assert total_risk == Decimal("13.25")
    assert total_quantity == Decimal("12")


def test_aggregate_strategy_metrics_groups_by_strategy() -> None:
    orders = [
        ApprovedOrderStub(
            risk_amount=Decimal("1.00"),
            final_quantity=Decimal("2"),
            strategy_id="STRAT_A",
        ),
        ApprovedOrderStub(
            risk_amount=Decimal("0"),
            final_quantity=Decimal("3"),
            strategy_id="STRAT_A",
        ),
        ApprovedOrderStub(
            risk_amount=Decimal("2.50"),
            final_quantity=Decimal("4"),
            strategy_id="STRAT_B",
        ),
    ]

    metrics = AccountFinancialCalculator.aggregate_strategy_metrics(orders)

    assert metrics["STRAT_A"]["count"] == 2
    assert metrics["STRAT_A"]["risk"] == Decimal("1.00")
    assert metrics["STRAT_A"]["quantity"] == Decimal("5")
    assert metrics["STRAT_B"]["count"] == 1
    assert metrics["STRAT_B"]["risk"] == Decimal("2.50")
    assert metrics["STRAT_B"]["quantity"] == Decimal("4")


def test_calculate_average_metrics_filters_none() -> None:
    values = [Decimal("1"), None, Decimal("3")]

    average = AccountFinancialCalculator.calculate_average_metrics(values)

    assert average == Decimal("2")


def test_calculate_average_metrics_returns_none_for_empty() -> None:
    values: list[Decimal | None] = [None, None]

    average = AccountFinancialCalculator.calculate_average_metrics(values)

    assert average is None
