from dataclasses import dataclass
from decimal import Decimal

from aletrader.finance.accounting.domain.position_maintenance import (
    calculate_avg_entry_price_and_fx_from_transactions,
)


@dataclass(frozen=True)
class Tx:
    side: str
    qty: Decimal
    price: Decimal
    fx: Decimal
    commission: Decimal
    fees: Decimal
    taxes: Decimal


def test_avg_entry_price_and_fx_from_transactions_buy_only() -> None:
    transactions = [
        Tx(
            side="BUY",
            qty=Decimal("2"),
            price=Decimal("547.8"),
            fx=Decimal("1.0"),
            commission=Decimal("6"),
            fees=Decimal("0"),
            taxes=Decimal("0"),
        ),
        Tx(
            side="BUY",
            qty=Decimal("2"),
            price=Decimal("545.8"),
            fx=Decimal("1.0"),
            commission=Decimal("6"),
            fees=Decimal("0"),
            taxes=Decimal("0"),
        ),
    ]

    result = calculate_avg_entry_price_and_fx_from_transactions(transactions)
    assert result is not None
    avg_price, avg_fx = result
    assert avg_price == Decimal("546.8")
    assert avg_fx == Decimal("1")


def test_avg_entry_price_and_fx_from_transactions_sell_reduces_position() -> None:
    transactions = [
        Tx(
            side="BUY",
            qty=Decimal("10"),
            price=Decimal("100"),
            fx=Decimal("1.0"),
            commission=Decimal("0"),
            fees=Decimal("0"),
            taxes=Decimal("0"),
        ),
        Tx(
            side="BUY",
            qty=Decimal("10"),
            price=Decimal("110"),
            fx=Decimal("1.0"),
            commission=Decimal("0"),
            fees=Decimal("0"),
            taxes=Decimal("0"),
        ),
        Tx(
            side="SELL",
            qty=Decimal("10"),
            price=Decimal("120"),
            fx=Decimal("1.0"),
            commission=Decimal("0"),
            fees=Decimal("0"),
            taxes=Decimal("0"),
        ),
    ]

    result = calculate_avg_entry_price_and_fx_from_transactions(transactions)
    assert result is not None
    avg_price, avg_fx = result
    assert avg_price == Decimal("105")
    assert avg_fx == Decimal("1")


def test_avg_entry_price_and_fx_from_transactions_closed_position() -> None:
    transactions = [
        Tx(
            side="BUY",
            qty=Decimal("5"),
            price=Decimal("50"),
            fx=Decimal("1.0"),
            commission=Decimal("0"),
            fees=Decimal("0"),
            taxes=Decimal("0"),
        ),
        Tx(
            side="SELL",
            qty=Decimal("5"),
            price=Decimal("55"),
            fx=Decimal("1.0"),
            commission=Decimal("0"),
            fees=Decimal("0"),
            taxes=Decimal("0"),
        ),
    ]

    assert calculate_avg_entry_price_and_fx_from_transactions(transactions) is None
