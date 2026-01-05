"""
Script to fix existing positions with zero avg_cost in the database.

This script:
1. Finds all positions with avg_cost <= 0
2. Attempts to recalculate avg_cost from transaction history
3. Updates positions with correct avg_cost
4. Logs all changes

Run this script to fix existing bad data before the validation prevents new bad data.
"""

import sys
import logging
from decimal import Decimal
from pathlib import Path

# Add AMS src to path
_trading_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_trading_root / "accountmanagementservice" / "src"))

from aletrader.ams.infrastructure.persistence.db import transaction
from aletrader.ams.domain.ledger_models import Position, LedgerTransaction
from aletrader.finance.accounting.domain.position_maintenance import (
    calculate_avg_cost_from_transactions,
)
from sqlmodel import select, Session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def recalculate_avg_cost_from_transactions(
    account_id: str,
    symbol: str,
    session: Session,
) -> Decimal | None:
    """
    Recalculate average cost from transaction history.
    
    Args:
        account_id: Account identifier
        symbol: Trading symbol
        session: Database session
        
    Returns:
        Recalculated avg_cost or None if cannot be calculated
    """
    # Get all FILL transactions for this symbol
    stmt = (
        select(LedgerTransaction)
        .where(LedgerTransaction.account_id == account_id)
        .where(LedgerTransaction.symbol == symbol)
        .where(LedgerTransaction.type.in_(["FILL", "SL", "TP"]))
        .order_by(LedgerTransaction.tx_id)
    )
    
    transactions = list(session.exec(stmt).all())
    
    return calculate_avg_cost_from_transactions(transactions)


def fix_zero_avg_cost_positions() -> dict[str, int]:
    """
    Fix all positions with zero or negative avg_cost.
    
    Returns:
        Dictionary with counts of fixed positions
    """
    fixed_count = 0
    error_count = 0
    skipped_count = 0
    
    with transaction() as session:
        # Find all positions with avg_cost <= 0
        stmt = select(Position).where(Position.avg_cost <= 0)
        bad_positions = list(session.exec(stmt).all())
        
        logger.info(f"Found {len(bad_positions)} positions with avg_cost <= 0")
        
        for pos in bad_positions:
            logger.warning(
                f"Position with zero avg_cost: account_id={pos.account_id}, "
                f"symbol={pos.symbol}, qty={pos.qty}, avg_cost={pos.avg_cost}"
            )
            
            # Try to recalculate from transaction history
            recalculated_avg_cost = recalculate_avg_cost_from_transactions(
                pos.account_id,
                pos.symbol,
                session,
            )
            
            if recalculated_avg_cost and recalculated_avg_cost > 0:
                logger.info(
                    f"Recalculated avg_cost for {pos.account_id}/{pos.symbol}: "
                    f"{pos.avg_cost} -> {recalculated_avg_cost}"
                )
                pos.avg_cost = recalculated_avg_cost
                session.add(pos)
                fixed_count += 1
            else:
                logger.error(
                    f"Cannot recalculate avg_cost for {pos.account_id}/{pos.symbol}. "
                    f"Position may need to be deleted or manually fixed."
                )
                error_count += 1
        
        # Also check for positions with very small avg_cost (potential rounding issues)
        stmt = select(Position).where(Position.avg_cost > 0).where(Position.avg_cost < Decimal("0.000001"))
        small_avg_cost_positions = list(session.exec(stmt).all())
        
        if small_avg_cost_positions:
            logger.warning(f"Found {len(small_avg_cost_positions)} positions with very small avg_cost (< 0.000001)")
            for pos in small_avg_cost_positions:
                logger.warning(
                    f"Position with very small avg_cost: account_id={pos.account_id}, "
                    f"symbol={pos.symbol}, qty={pos.qty}, avg_cost={pos.avg_cost}"
                )
                skipped_count += len(small_avg_cost_positions)
    
    return {
        "fixed": fixed_count,
        "errors": error_count,
        "skipped": skipped_count,
        "total_bad": len(bad_positions) if 'bad_positions' in locals() else 0,
    }


if __name__ == "__main__":
    logger.info("Starting fix_zero_avg_cost_positions script...")
    
    try:
        results = fix_zero_avg_cost_positions()
        
        logger.info("=" * 60)
        logger.info("Fix Results:")
        logger.info(f"  Fixed positions: {results['fixed']}")
        logger.info(f"  Errors (cannot fix): {results['errors']}")
        logger.info(f"  Skipped (very small): {results['skipped']}")
        logger.info(f"  Total bad positions found: {results['total_bad']}")
        logger.info("=" * 60)
        
        if results['errors'] > 0:
            logger.warning(
                f"WARNING: {results['errors']} positions could not be fixed. "
                f"These may need manual intervention or deletion."
            )
            sys.exit(1)
        else:
            logger.info("All positions fixed successfully!")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Error fixing positions: {e}", exc_info=True)
        sys.exit(1)
