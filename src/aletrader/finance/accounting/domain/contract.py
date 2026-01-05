"""
Accounting Contract - Phase 0.

Defines the fundamental rules and invariants for account valuation and accounting.
This contract MUST be enforced before any code fixes are applied.

Without this contract, bugs will reappear even after all fixes.

All components must adhere to these rules. Violations must cause immediate failure.
"""

from datetime import date
from decimal import Decimal
from typing import Protocol


class ValuationSnapshot(Protocol):
    """
    Single valuation snapshot for a trading day.
    
    All valuations must use this snapshot to ensure consistency.
    """
    trading_date: date
    price_snapshot: dict[str, Decimal]  # symbol -> price
    fx_snapshot: dict[str, Decimal]  # currency -> FX rate to base currency


# ============================================================================
# PHASE 0.1: VALUATION MOMENT (SINGLE SNAPSHOT RULE)
# ============================================================================

VALUATION_MOMENT = "EOD"  # End of trading day

"""
Rule 0.1: Each account is valued once per trading day, at a single agreed moment.

Chosen moment: End of trading day (EOD) after:
- all executions
- all exits
- all journal entries

This produces one immutable:
- price snapshot
- FX snapshot
- account valuation

No component may use a different time reference.
"""


# ============================================================================
# PHASE 0.2: VALUATION OWNERSHIP (SINGLE SOURCE OF TRUTH)
# ============================================================================

"""
Rule 0.2: There is exactly one Account Valuation per account per day.

Components:
- Equity
- Cash
- Positions value
- Realised P&L
- Unrealised P&L

All reports, journals, risk, and dashboards must reconcile to this valuation.
"""


# ============================================================================
# PHASE 0.3: CAPITAL CONSERVATION RULES
# ============================================================================

"""
Rule 0.3: Capital conservation invariants (non-negotiable).

BUY transactions:
- Cash decreases
- Position value increases
- Equity MUST NOT change (ignoring fees)

SELL transactions:
- Position value decreases
- Cash increases
- Equity changes only by realised P&L

If these rules are violated, the run must fail.
"""


def validate_buy_transaction_equity_invariant(
    cash_before: Decimal,
    cash_after: Decimal,
    position_value_before: Decimal,
    position_value_after: Decimal,
    equity_before: Decimal,
    equity_after: Decimal,
    fees: Decimal,
) -> None:
    """
    Validate that BUY transaction does not change equity (ignoring fees).
    
    Rule 0.3: BUY transactions must not change equity (ignoring fees).
    
    Args:
        cash_before: Cash before transaction
        cash_after: Cash after transaction
        position_value_before: Position value before transaction
        position_value_after: Position value after transaction
        equity_before: Equity before transaction
        equity_after: Equity after transaction
        fees: Transaction fees
        
    Raises:
        ValueError: If equity changes beyond fees (violates capital conservation)
    """
    # Equity change should equal -fees (equity decreases by fees)
    # Cash decrease = position increase, net effect = -fees
    expected_equity_change = -fees
    actual_equity_change = equity_after - equity_before
    
    # Allow small rounding differences
    difference = abs(actual_equity_change - expected_equity_change)
    if difference > Decimal("0.01"):
        raise ValueError(
            f"BUY transaction equity invariant violated (Rule 0.3): "
            f"equity_before={equity_before}, equity_after={equity_after}, "
            f"expected_change={expected_equity_change} (-fees only), "
            f"actual_change={actual_equity_change}, difference={difference}. "
            f"BUY transactions must not change equity (ignoring fees)."
        )


def validate_sell_transaction_equity_invariant(
    cash_before: Decimal,
    cash_after: Decimal,
    position_value_before: Decimal,
    position_value_after: Decimal,
    equity_before: Decimal,
    equity_after: Decimal,
    realized_pnl: Decimal,
) -> None:
    """
    Validate that SELL transaction changes equity only by realised P&L.
    
    Rule 0.3: SELL transactions change equity only by realised P&L.
    
    Args:
        cash_before: Cash before transaction
        cash_after: Cash after transaction
        position_value_before: Position value before transaction
        position_value_after: Position value after transaction
        equity_before: Equity before transaction
        equity_after: Equity after transaction
        realized_pnl: Realised P&L from transaction
        
    Raises:
        ValueError: If equity change doesn't match realised P&L
    """
    # Equity change should equal realised P&L
    expected_equity_change = realized_pnl
    actual_equity_change = equity_after - equity_before
    
    # Allow small rounding differences
    difference = abs(actual_equity_change - expected_equity_change)
    if difference > Decimal("0.01"):
        raise ValueError(
            f"SELL transaction equity invariant violated (Rule 0.3): "
            f"equity_before={equity_before}, equity_after={equity_after}, "
            f"expected_change={expected_equity_change} (realised P&L), "
            f"actual_change={actual_equity_change}, difference={difference}. "
            f"SELL transactions must change equity only by realised P&L."
        )


# ============================================================================
# PHASE 0.4: PRICE & FX RULES
# ============================================================================

"""
Rule 0.4: Price and FX consistency.

All open positions are valued using:
- the same EOD price snapshot
- the same FX snapshot

No mixing of:
- entry-day FX
- exit-day FX
- live FX

FX rate is fixed per symbol per valuation day.
FX comes from the valuation snapshot, not recalculated.
"""


# ============================================================================
# PHASE 0.5: OUT-OF-HOURS TRADING & JOURNALING
# ============================================================================

"""
Rule 0.5: Out-of-hours trading and journaling.

- Trades executed intraday are journaled immediately
- Valuation happens only at EOD
- No intraday revaluation unless explicitly enabled

Journal entries are factual history. Valuation is a derived result.
"""


# ============================================================================
# CANONICAL FORMULAS
# ============================================================================

# Canonical formulas live in aletrader.finance.accounting.domain.
