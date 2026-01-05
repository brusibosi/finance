"""
Diagnostic script to check all positions for zero avg_cost.

This script checks all positions across all environments and reports any issues.
"""

import sys
import logging
from decimal import Decimal
from pathlib import Path
from typing import Any

# Add AMS src to path
_trading_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_trading_root / "accountmanagementservice" / "src"))

from aletrader.ams.infrastructure.persistence.db import transaction
from aletrader.ams.domain.ledger_models import Position
from sqlmodel import select

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def check_all_positions() -> dict[str, Any]:
    """Check all positions for zero or negative avg_cost."""
    results = {
        "total_positions": 0,
        "zero_avg_cost": [],
        "negative_avg_cost": [],
        "very_small_avg_cost": [],
        "all_positions": [],
    }
    
    with transaction() as session:
        stmt = select(Position)
        all_positions = list(session.exec(stmt).all())
        
        results["total_positions"] = len(all_positions)
        logger.info(f"Found {len(all_positions)} total positions")
        
        for pos in all_positions:
            pos_info = {
                "account_id": pos.account_id,
                "symbol": pos.symbol,
                "qty": float(pos.qty),
                "avg_cost": float(pos.avg_cost),
                "last_price": float(pos.last_price),
                "fx": float(pos.fx),
            }
            results["all_positions"].append(pos_info)
            
            if pos.avg_cost == 0:
                logger.error(f"ZERO avg_cost: {pos.account_id}/{pos.symbol} - qty={pos.qty}, avg_cost={pos.avg_cost}")
                results["zero_avg_cost"].append(pos_info)
            elif pos.avg_cost < 0:
                logger.error(f"NEGATIVE avg_cost: {pos.account_id}/{pos.symbol} - qty={pos.qty}, avg_cost={pos.avg_cost}")
                results["negative_avg_cost"].append(pos_info)
            elif pos.avg_cost < Decimal("0.000001"):
                logger.warning(f"VERY SMALL avg_cost: {pos.account_id}/{pos.symbol} - qty={pos.qty}, avg_cost={pos.avg_cost}")
                results["very_small_avg_cost"].append(pos_info)
            else:
                logger.debug(f"OK: {pos.account_id}/{pos.symbol} - qty={pos.qty}, avg_cost={pos.avg_cost}")
    
    return results


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Checking all positions for zero avg_cost...")
    logger.info("=" * 60)
    
    try:
        results = check_all_positions()
        
        logger.info("=" * 60)
        logger.info("Results:")
        logger.info(f"  Total positions: {results['total_positions']}")
        logger.info(f"  Zero avg_cost: {len(results['zero_avg_cost'])}")
        logger.info(f"  Negative avg_cost: {len(results['negative_avg_cost'])}")
        logger.info(f"  Very small avg_cost (< 0.000001): {len(results['very_small_avg_cost'])}")
        logger.info("=" * 60)
        
        if results["zero_avg_cost"]:
            logger.error("CRITICAL: Found positions with ZERO avg_cost:")
            for pos in results["zero_avg_cost"]:
                logger.error(f"  {pos['account_id']}/{pos['symbol']}: qty={pos['qty']}, avg_cost={pos['avg_cost']}")
        
        if results["negative_avg_cost"]:
            logger.error("CRITICAL: Found positions with NEGATIVE avg_cost:")
            for pos in results["negative_avg_cost"]:
                logger.error(f"  {pos['account_id']}/{pos['symbol']}: qty={pos['qty']}, avg_cost={pos['avg_cost']}")
        
        if results["zero_avg_cost"] or results["negative_avg_cost"]:
            logger.error("\nACTION REQUIRED: Run fix_zero_avg_cost_positions.py to fix these positions")
            sys.exit(1)
        else:
            logger.info("✓ All positions have valid avg_cost > 0")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Error checking positions: {e}", exc_info=True)
        sys.exit(1)




