"""
realistic_simulator.py: Realistic execution simulator (default).

Wraps base_executor and adds spread fees for shorts.
This matches your current implementation.
"""

from typing import Dict, Any, Tuple, Optional
from .base_executor import BaseExecutor


class RealisticSimulator(BaseExecutor):
    """
    Realistic execution simulator (default).
    
    Wraps base_executor and adds:
    - Spread fees for short positions (based on market cap)
    - Perfect execution for long positions (no slippage)
    
    This matches your current backtest implementation.
    """
    
    def __init__(self, portfolio: Dict[str, Any], logger=None):
        """Initialize realistic executor."""
        super().__init__(portfolio, logger)
    
    def execute_buy(self, symbol: str, amount_usd: float, current_price: float,
                   current_date: str, reasoning: str = "") -> Tuple[bool, Dict[str, Any]]:
        """Execute BUY (perfect execution, no slippage)."""
        return super().execute_buy(symbol, amount_usd, current_price, current_date, reasoning)
    
    def execute_sell(self, symbol: str, current_price: float, current_date: str,
                    reasoning: str = "", shares_to_sell: Optional[int] = None) -> Tuple[bool, Dict[str, Any]]:
        """Execute SELL (perfect execution, no slippage)."""
        return super().execute_sell(symbol, current_price, current_date, reasoning, shares_to_sell)
    
    def execute_short(self, symbol: str, amount_usd: float, current_price: float,
                     current_date: str, reasoning: str = "") -> Tuple[bool, Dict[str, Any]]:
        """Execute SHORT (with spread fees based on market cap)."""
        # Calculate spread fee
        spread_rate = self._get_short_spread_rate(symbol)
        shares = int(amount_usd / current_price)
        notional = shares * current_price
        spread_fee = notional * spread_rate
        
        # Use base executor with spread fee
        return super().execute_short(symbol, amount_usd, current_price, current_date, reasoning, spread_fee)
    
    def execute_cover(self, symbol: str, current_price: float, current_date: str,
                     reasoning: str = "", shares_to_cover: Optional[int] = None) -> Tuple[bool, Dict[str, Any]]:
        """Execute COVER (with exit spread fees)."""
        # Calculate exit spread fee
        spread_rate = self._get_short_spread_rate(symbol)
        short_positions = self.portfolio.get('short_positions', {})
        if symbol in short_positions:
            shares = shares_to_cover if shares_to_cover else short_positions[symbol].get('shares', 0)
        else:
            shares = 0
        exit_spread_fee = (shares * current_price) * spread_rate
        
        # Use base executor with exit spread fee
        return super().execute_cover(symbol, current_price, current_date, reasoning, shares_to_cover, exit_spread_fee)

