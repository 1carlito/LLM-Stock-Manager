"""
slippage_simulator.py: Execution simulator with slippage modeling.

Wraps base_executor and adds slippage (bid-ask spread, volatility-based).
"""

import random
from typing import Dict, Any, Tuple, Optional
from .base_executor import BaseExecutor


class SlippageSimulator(BaseExecutor):
    """
    Execution simulator that models slippage.
    
    Slippage factors:
    - Bid-ask spread: Fixed percentage (default 0.1%)
    - Volatility-based: Additional slippage based on price volatility
    - Random component: Small random variation
    """
    
    def __init__(self, portfolio: Dict[str, Any], logger=None,
                 bid_ask_spread_pct: float = 0.001,  # 0.1% default
                 volatility_factor: float = 0.5,      # How much volatility affects slippage
                 random_slippage_pct: float = 0.0005): # 0.05% random component
        super().__init__(portfolio, logger)
        self.bid_ask_spread_pct = bid_ask_spread_pct
        self.volatility_factor = volatility_factor
        self.random_slippage_pct = random_slippage_pct
    
    def _calculate_slippage(self, symbol: str, action: str, amount_usd: float) -> float:
        """
        Calculate slippage percentage for a trade.
        
        Args:
            symbol: Stock symbol
            action: 'BUY' or 'SELL' or 'SHORT' or 'COVER'
            amount_usd: Trade size in dollars
        
        Returns:
            Slippage as a decimal (e.g., 0.001 = 0.1%)
        """
        # Base bid-ask spread
        slippage = self.bid_ask_spread_pct
        
        # Volatility-based slippage (if we have price history)
        # For now, use a simple estimate based on market cap
        # Lower market cap = higher volatility = more slippage
        market_caps = self.portfolio.get('market_caps', {})
        if symbol in market_caps:
            market_cap_bil = market_caps[symbol]
            # Smaller caps have higher volatility
            volatility_estimate = max(0.0005, 1.0 / (market_cap_bil ** 0.5)) * self.volatility_factor
            slippage += volatility_estimate
        
        # Random component
        random_component = random.uniform(-self.random_slippage_pct, self.random_slippage_pct)
        slippage += random_component
        
        # Direction: BUY pays more (positive slippage), SELL gets less (negative slippage)
        if action in ('BUY', 'COVER'):
            # Pay more when buying
            slippage = abs(slippage)
        elif action in ('SELL', 'SHORT'):
            # Get less when selling
            slippage = -abs(slippage)
        
        return slippage
    
    def execute_buy(self, symbol: str, amount_usd: float, current_price: float,
                   current_date: str, reasoning: str = "") -> Tuple[bool, Dict[str, Any]]:
        """Execute BUY with slippage."""
        slippage = self._calculate_slippage(symbol, 'BUY', amount_usd)
        execution_price = current_price * (1 + slippage)
        
        if self.logger:
            self.logger.debug(f"   Slippage for BUY {symbol}: {slippage*100:.3f}% (${current_price:.2f} → ${execution_price:.2f})")
        
        return super().execute_buy(symbol, amount_usd, execution_price, current_date, reasoning)
    
    def execute_sell(self, symbol: str, current_price: float, current_date: str,
                    reasoning: str = "", shares_to_sell: Optional[int] = None) -> Tuple[bool, Dict[str, Any]]:
        """Execute SELL with slippage."""
        # Estimate amount_usd for slippage calculation
        positions = self.portfolio.get('positions', {})
        if symbol in positions:
            shares = shares_to_sell if shares_to_sell else positions[symbol].get('shares', 0)
            amount_usd = shares * current_price
        else:
            amount_usd = 0
        
        slippage = self._calculate_slippage(symbol, 'SELL', amount_usd)
        execution_price = current_price * (1 + slippage)  # Negative slippage = get less
        
        if self.logger:
            self.logger.debug(f"   Slippage for SELL {symbol}: {slippage*100:.3f}% (${current_price:.2f} → ${execution_price:.2f})")
        
        return super().execute_sell(symbol, execution_price, current_date, reasoning, shares_to_sell)
    
    def execute_short(self, symbol: str, amount_usd: float, current_price: float,
                     current_date: str, reasoning: str = "") -> Tuple[bool, Dict[str, Any]]:
        """Execute SHORT with slippage."""
        slippage = self._calculate_slippage(symbol, 'SHORT', amount_usd)
        execution_price = current_price * (1 + slippage)  # Negative slippage = short at lower price (better)
        
        if self.logger:
            self.logger.debug(f"   Slippage for SHORT {symbol}: {slippage*100:.3f}% (${current_price:.2f} → ${execution_price:.2f})")
        
        # Calculate spread fee (slippage simulator still uses spread fees)
        spread_rate = self._get_short_spread_rate(symbol)
        shares = int(amount_usd / execution_price)
        notional = shares * execution_price
        spread_fee = notional * spread_rate
        
        return super().execute_short(symbol, amount_usd, execution_price, current_date, reasoning, spread_fee)
    
    def execute_cover(self, symbol: str, current_price: float, current_date: str,
                     reasoning: str = "", shares_to_cover: Optional[int] = None) -> Tuple[bool, Dict[str, Any]]:
        """Execute COVER with slippage."""
        # Estimate amount_usd for slippage calculation
        short_positions = self.portfolio.get('short_positions', {})
        if symbol in short_positions:
            shares = shares_to_cover if shares_to_cover else short_positions[symbol].get('shares', 0)
            amount_usd = shares * current_price
        else:
            amount_usd = 0
        
        slippage = self._calculate_slippage(symbol, 'COVER', amount_usd)
        execution_price = current_price * (1 + slippage)  # Positive slippage = pay more to cover (worse)
        
        if self.logger:
            self.logger.debug(f"   Slippage for COVER {symbol}: {slippage*100:.3f}% (${current_price:.2f} → ${execution_price:.2f})")
        
        # Calculate exit spread fee
        spread_rate = self._get_short_spread_rate(symbol)
        short_positions = self.portfolio.get('short_positions', {})
        if symbol in short_positions:
            shares = shares_to_cover if shares_to_cover else short_positions[symbol].get('shares', 0)
        else:
            shares = 0
        exit_spread_fee = (shares * execution_price) * spread_rate
        
        return super().execute_cover(symbol, execution_price, current_date, reasoning, shares_to_cover, exit_spread_fee)

