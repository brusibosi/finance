"""
Public interfaces for accounting calculations.

Facade pattern for centralized access to pure finance logic.
"""

from decimal import Decimal
from typing import Protocol, Sequence


class PositionStateLike(Protocol):
    """Protocol for position state objects used in aggregation."""

    notional: Decimal
    qty: Decimal
    avg_cost: Decimal
    unrealized_pnl: Decimal


class ApprovedOrderLike(Protocol):
    """Protocol for approved order objects used in aggregation."""

    risk_amount: Decimal | float | int
    final_quantity: Decimal | float | int
    strategy_id: str


class LedgerTransactionLike(Protocol):
    """Protocol for ledger transaction objects used in P&L aggregation."""

    side: str
    realized_pnl_delta: Decimal | float | int | None
    commission: Decimal | float | int | None
    fees: Decimal | float | int | None
    taxes: Decimal | float | int | None


class CashMovementTransactionLike(Protocol):
    """Protocol for transactions that affect cash balance."""

    type: str  # FILL, SL, TP, DEPOSIT, WITHDRAWAL
    side: str | None  # BUY, SELL (None for DEPOSIT/WITHDRAWAL)
    qty: Decimal | None
    price: Decimal | None
    commission: Decimal | None
    fees: Decimal | None
    taxes: Decimal | None
    amount: Decimal | None  # For DEPOSIT/WITHDRAWAL


class PositionTransactionLike(Protocol):
    """Protocol for transactions used in position reconstruction."""

    symbol: str
    timestamp: str  # ISO format datetime
    type: str
    side: str
    qty: Decimal
    price: Decimal
    fx_rate_used: Decimal
    commission: Decimal
    fees: Decimal
    taxes: Decimal
    position_qty_after: Decimal
    position_avg_cost_after: Decimal


class AccountFinancialCalculator:
    """
    Facade for all accounting calculations.

    Provides a single entry point for finance-related domain logic.
    """

    @staticmethod
    def calculate_position_notional(
        qty: Decimal,
        last_price: Decimal,
        fx_rate: Decimal,
        currency: str,
        base_currency: str,
        stored_notional: Decimal | None = None,
    ) -> Decimal:
        """Calculate position notional value."""
        from aletrader.finance.accounting.domain.calculations import (
            calculate_position_notional,
        )

        return calculate_position_notional(
            qty=qty,
            last_price=last_price,
            fx_rate=fx_rate,
            currency=currency,
            base_currency=base_currency,
            stored_notional=stored_notional,
        )

    @staticmethod
    def calculate_equity(
        cash: Decimal,
        position_notional_sum: Decimal,
    ) -> Decimal:
        """Calculate equity (cash + positions)."""
        from aletrader.finance.accounting.domain.calculations import calculate_equity

        return calculate_equity(cash=cash, position_notional_sum=position_notional_sum)

    @staticmethod
    def calculate_equity_canonical(
        cash: Decimal,
        positions_market_value: Decimal,
    ) -> Decimal:
        """Calculate equity using canonical formula."""
        from aletrader.finance.accounting.domain.calculations import (
            calculate_equity_canonical,
        )

        return calculate_equity_canonical(
            cash=cash,
            positions_market_value=positions_market_value,
        )

    @staticmethod
    def calculate_total_pnl(
        initial_equity: Decimal,
        current_equity: Decimal,
    ) -> Decimal:
        """Calculate total P&L."""
        from aletrader.finance.accounting.domain.calculations import calculate_total_pnl

        return calculate_total_pnl(
            initial_equity=initial_equity,
            current_equity=current_equity,
        )

    @staticmethod
    def calculate_total_pnl_pct(
        total_pnl: Decimal,
        initial_equity: Decimal,
    ) -> Decimal:
        """Calculate total P&L percentage."""
        from aletrader.finance.accounting.domain.calculations import (
            calculate_total_pnl_pct,
        )

        return calculate_total_pnl_pct(
            total_pnl=total_pnl,
            initial_equity=initial_equity,
        )

    @staticmethod
    def calculate_total_pnl_metrics(
        initial_equity: Decimal,
        current_equity: Decimal,
    ) -> tuple[Decimal, Decimal]:
        """Calculate total P&L and percentage."""
        from aletrader.finance.accounting.domain.calculations import (
            calculate_total_pnl_metrics,
        )

        return calculate_total_pnl_metrics(
            initial_equity=initial_equity,
            current_equity=current_equity,
        )

    @staticmethod
    def calculate_gross_value(
        qty: Decimal,
        price: Decimal,
        fx: Decimal,
    ) -> Decimal:
        """Calculate gross value."""
        from aletrader.finance.accounting.domain.transactions import calculate_gross_value

        return calculate_gross_value(qty=qty, price=price, fx=fx)

    @staticmethod
    def calculate_cost_total(
        commission: Decimal,
        fees: Decimal,
        taxes: Decimal,
    ) -> Decimal:
        """Calculate total transaction costs."""
        from aletrader.finance.accounting.domain.transactions import calculate_cost_total

        return calculate_cost_total(commission=commission, fees=fees, taxes=taxes)

    @staticmethod
    def apply_transaction(
        account_before: "AccountStateBefore",
        position_before: "PositionStateBefore | None",
        tx_input: "TransactionInput",
    ) -> "TransactionResult":
        """Apply transaction and calculate new state."""
        from aletrader.finance.accounting.domain.transactions import apply_transaction

        return apply_transaction(
            account_before=account_before,
            position_before=position_before,
            tx_input=tx_input,
        )

    @staticmethod
    def calculate_drawdown(
        max_equity_to_date: Decimal,
        current_equity: Decimal,
    ) -> Decimal:
        """Calculate drawdown percentage."""
        from aletrader.finance.accounting.domain.transactions import calculate_drawdown

        return calculate_drawdown(
            max_equity_to_date=max_equity_to_date,
            current_equity=current_equity,
        )

    @staticmethod
    def calculate_unrealized_pnl(
        qty: Decimal,
        last_price: Decimal,
        fx: Decimal,
        avg_cost: Decimal,
    ) -> Decimal:
        """Calculate unrealized P&L."""
        from aletrader.finance.accounting.domain.position_calculations import (
            calculate_unrealized_pnl,
        )

        return calculate_unrealized_pnl(
            qty=qty,
            last_price=last_price,
            fx=fx,
            avg_cost=avg_cost,
        )

    @staticmethod
    def calculate_unrealized_pnl_canonical(
        last_price: Decimal,
        entry_price: Decimal,
        qty: Decimal,
        fx: Decimal,
        entry_fx: Decimal | None = None,
    ) -> Decimal:
        """Calculate unrealized P&L using canonical formula."""
        from aletrader.finance.accounting.domain.position_calculations import (
            calculate_unrealized_pnl_canonical,
        )

        return calculate_unrealized_pnl_canonical(
            last_price=last_price,
            entry_price=entry_price,
            qty=qty,
            fx=fx,
            entry_fx=entry_fx,
        )

    @staticmethod
    def calculate_avg_entry_price_and_fx_from_transactions(
        transactions: Sequence["AvgCostTransactionLike"],
    ) -> tuple[Decimal, Decimal] | None:
        """Calculate average entry price and FX for open position."""
        from aletrader.finance.accounting.domain.position_maintenance import (
            calculate_avg_entry_price_and_fx_from_transactions,
        )

        return calculate_avg_entry_price_and_fx_from_transactions(transactions)

    @staticmethod
    def validate_position_notional(
        notional: Decimal,
        qty: Decimal,
        last_price: Decimal,
        fx_rate: Decimal,
        tolerance: Decimal = Decimal("0.01"),
    ) -> Decimal:
        """Validate and correct position notional."""
        from aletrader.finance.accounting.domain.position_calculations import (
            validate_position_notional,
        )

        return validate_position_notional(
            notional=notional,
            qty=qty,
            last_price=last_price,
            fx_rate=fx_rate,
            tolerance=tolerance,
        )

    @staticmethod
    def aggregate_unrealized_pnl(
        positions: Sequence[PositionStateLike],
    ) -> Decimal:
        """Aggregate unrealized P&L across positions."""
        from aletrader.finance.accounting.domain.aggregations import (
            aggregate_unrealized_pnl,
        )

        return aggregate_unrealized_pnl(positions)

    @staticmethod
    def aggregate_positions_value(
        positions: Sequence[PositionStateLike],
    ) -> Decimal:
        """Aggregate total positions value."""
        from aletrader.finance.accounting.domain.aggregations import (
            aggregate_positions_value,
        )

        return aggregate_positions_value(positions)

    @staticmethod
    def aggregate_positions_cost(
        positions: Sequence[PositionStateLike],
    ) -> Decimal:
        """Aggregate total positions cost basis."""
        from aletrader.finance.accounting.domain.aggregations import (
            aggregate_positions_cost,
        )

        return aggregate_positions_cost(positions)

    @staticmethod
    def aggregate_order_risk(
        orders: Sequence[ApprovedOrderLike],
    ) -> tuple[Decimal, Decimal]:
        """Aggregate total risk amount and quantity."""
        from aletrader.finance.accounting.domain.aggregations import (
            aggregate_order_risk,
        )

        return aggregate_order_risk(orders)

    @staticmethod
    def aggregate_strategy_metrics(
        orders: Sequence[ApprovedOrderLike],
    ) -> dict[str, dict[str, int | Decimal]]:
        """Aggregate metrics by strategy."""
        from aletrader.finance.accounting.domain.aggregations import (
            aggregate_strategy_metrics,
        )

        return aggregate_strategy_metrics(orders)

    @staticmethod
    def calculate_average_metrics(
        values: Sequence[Decimal | float | None],
    ) -> Decimal | None:
        """Calculate average of numeric values."""
        from aletrader.finance.accounting.domain.aggregations import (
            calculate_average_metrics,
        )

        return calculate_average_metrics(values)

    @staticmethod
    def calculate_cash_from_initial_and_transactions(
        initial_equity: Decimal,
        transactions: list,
    ) -> Decimal:
        """Calculate current cash from initial equity and transactions."""
        from aletrader.finance.accounting.domain.calculations import (
            calculate_cash_from_initial_and_transactions,
        )

        return calculate_cash_from_initial_and_transactions(initial_equity, transactions)

    @staticmethod
    def calculate_realized_pnl_from_exit_transactions(
        transactions: Sequence[LedgerTransactionLike],
    ) -> Decimal:
        """Calculate realized P&L from exit transactions only."""
        from aletrader.finance.accounting.domain.aggregations import (
            calculate_realized_pnl_from_exit_transactions,
        )

        return calculate_realized_pnl_from_exit_transactions(transactions)

    @staticmethod
    def reconstruct_positions_from_transactions(
        transactions: list,
        market_prices: dict[str, Decimal],
        fx_rates: dict[str, Decimal],
    ) -> list[dict]:
        """Reconstruct open positions from transaction history."""
        from aletrader.finance.accounting.domain.position_maintenance import (
            reconstruct_positions_from_transactions,
        )

        return reconstruct_positions_from_transactions(transactions, market_prices, fx_rates)


    @staticmethod
    def validate_balance_invariant(
        cash: Decimal,
        position_notional_sum: Decimal,
        equity: Decimal,
        tolerance: Decimal,
    ) -> None:
        """Validate balance invariant."""
        from aletrader.finance.accounting.domain.invariants import (
            validate_balance_invariant,
        )

        validate_balance_invariant(
            cash=cash,
            position_notional_sum=position_notional_sum,
            equity=equity,
            tolerance=tolerance,
        )

    @staticmethod
    def validate_pnl_consistency(
        initial_equity: Decimal,
        equity: Decimal,
        realized_pnl_cum: Decimal,
        unrealized_pnl_cum: Decimal,
        tolerance: Decimal,
    ) -> None:
        """Validate P&L consistency."""
        from aletrader.finance.accounting.domain.invariants import (
            validate_pnl_consistency,
        )

        validate_pnl_consistency(
            initial_equity=initial_equity,
            equity=equity,
            realized_pnl_cum=realized_pnl_cum,
            unrealized_pnl_cum=unrealized_pnl_cum,
            tolerance=tolerance,
        )


class AccountStateBefore(Protocol):
    """Protocol for account state before transaction."""

    cash: Decimal
    realized_pnl_cum: Decimal
    max_equity_to_date: Decimal
    initial_equity: Decimal


class PositionStateBefore(Protocol):
    """Protocol for position state before transaction."""

    qty: Decimal
    avg_cost: Decimal
    last_price: Decimal
    fx: Decimal


class TransactionInput(Protocol):
    """Protocol for transaction input parameters."""

    type: str
    side: str
    qty: Decimal
    price: Decimal
    commission: Decimal
    fees: Decimal
    taxes: Decimal
    fx: Decimal
    sl_price: Decimal | None


class TransactionResult(Protocol):
    """Protocol for transaction result parameters."""

    gross_value: Decimal
    cost_total: Decimal
    net_value: Decimal
    cash_after: Decimal
    position_qty_after: Decimal
    position_avg_cost_after: Decimal
    position_notional_after: Decimal
    realized_pnl_delta: Decimal
    realized_pnl_cum_after: Decimal
    last_price_after: Decimal
    fx_after: Decimal
    position_removed: bool


class StrategyPerformanceLike(Protocol):
    """Protocol for strategy performance summaries."""

    signals_generated: int
    signals_approved: int
    signals_rejected: int
    winning_trades: int
    losing_trades: int
    realized_pnl: Decimal


class AvgCostTransactionLike(Protocol):
    """Protocol for transactions used in avg_cost recalculation."""

    side: str
    qty: Decimal
    price: Decimal
    fx: Decimal
    commission: Decimal
    fees: Decimal
    taxes: Decimal
