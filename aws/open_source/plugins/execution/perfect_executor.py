"""
perfect_executor.py: Perfect execution simulator (no slippage, no fees).

Wraps base_executor with no fees - for comparison purposes.
"""

from typing import Dict, Any, Tuple, Optional
from .base_executor import BaseExecutor


class PerfectExecutor(BaseExecutor):
    """
    Perfect execution simulator - no fees, no slippage.
    
    Wraps base_executor but skips spread fees for shorts.
    For comparison purposes - shows performance without execution costs.
    """
    
    def __init__(self, portfolio: Dict[str, Any], logger=None):
        """Initialize perfect executor."""
        super().__init__(portfolio, logger)
    
    def execute_buy(self, symbol: str, amount_usd: float, current_price: float,
                   current_date: str, reasoning: str = "") -> Tuple[bool, Dict[str, Any]]:
        """Execute BUY at exact quoted price (no slippage, no fees)."""
        return super().execute_buy(symbol, amount_usd, current_price, current_date, reasoning)
    
    def execute_sell(self, symbol: str, current_price: float, current_date: str,
                    reasoning: str = "", shares_to_sell: Optional[int] = None) -> Tuple[bool, Dict[str, Any]]:
        """Execute SELL at exact quoted price (no slippage, no fees)."""
        return super().execute_sell(symbol, current_price, current_date, reasoning, shares_to_sell)
    
    def execute_short(self, symbol: str, amount_usd: float, current_price: float,
                     current_date: str, reasoning: str = "") -> Tuple[bool, Dict[str, Any]]:
        """Execute SHORT at exact quoted price (no spread fees)."""
        # Pass spread_fee=0 to skip fees
        return super().execute_short(symbol, amount_usd, current_price, current_date, reasoning, spread_fee=0.0)
    
    def execute_cover(self, symbol: str, current_price: float, current_date: str,
                     reasoning: str = "", shares_to_cover: Optional[int] = None) -> Tuple[bool, Dict[str, Any]]:
        """Execute COVER at exact quoted price (no spread fees)."""
        # Pass exit_spread_fee=0 to skip fees
        return super().execute_cover(symbol, current_price, current_date, reasoning, shares_to_cover, exit_spread_fee=0.0)

