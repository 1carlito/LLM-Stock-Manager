"""
volatility_risk_manager.py: Risk manager that adjusts position sizes based on volatility.

Reduces position sizes for high-volatility stocks.
"""

from typing import List, Dict, Any
from .base_risk_manager import BaseRiskManager


class VolatilityRiskManager(BaseRiskManager):
    """
    Risk manager that adjusts position sizes based on stock volatility.
    
    High volatility = smaller positions
    Low volatility = normal positions
    """
    
    def __init__(self, portfolio: Dict[str, Any], risk_config=None, logger=None,
                 volatility_threshold: float = 0.30,  # 30% volatility threshold
                 max_reduction_pct: float = 0.50):   # Max 50% reduction
        """
        Initialize volatility risk manager.
        
        Args:
            portfolio: Portfolio state dictionary
            risk_config: RiskConfig instance
            logger: Optional logger
            volatility_threshold: Volatility above which to reduce positions
            max_reduction_pct: Maximum position size reduction (0.5 = 50% reduction)
        """
        super().__init__(portfolio, risk_config, logger)
        self.volatility_threshold = volatility_threshold
        self.max_reduction_pct = max_reduction_pct
    
    def _get_volatility(self, symbol: str) -> float:
        """
        Get volatility estimate for a symbol.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Volatility as decimal (e.g., 0.30 = 30%)
        """
        # Try to get from portfolio state
        if 'volatilities' in self.portfolio:
            vols = self.portfolio['volatilities']
            if symbol in vols:
                return float(vols[symbol])
        
        # Fallback: Estimate from market cap (smaller = more volatile)
        market_caps = self.portfolio.get('market_caps', {})
        if symbol in market_caps:
            market_cap_bil = market_caps[symbol]
            # Rough estimate: smaller caps = higher volatility
            if market_cap_bil < 5:
                return 0.40  # High volatility
            elif market_cap_bil < 10:
                return 0.30  # Medium-high
            else:
                return 0.20  # Lower volatility
        
        # Default: assume moderate volatility
        return 0.25
    
    def evaluate(self, decisions: List[Dict[str, Any]], 
                portfolio_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evaluate decisions and adjust position sizes based on volatility.
        
        Args:
            decisions: List of trading decisions
            portfolio_state: Current portfolio state
        
        Returns:
            List of adjusted decisions
        """
        adjusted_decisions = []
        
        for decision in decisions:
            symbol = decision.get('symbol')
            action = decision.get('action', '').upper()
            
            # Only adjust BUY and SHORT positions
            if action not in ('BUY', 'SHORT'):
                adjusted_decisions.append(decision)
                continue
            
            # Get volatility
            volatility = self._get_volatility(symbol)
            
            # Check if volatility exceeds threshold
            if volatility > self.volatility_threshold:
                # Calculate reduction factor
                excess_vol = volatility - self.volatility_threshold
                reduction_factor = min(excess_vol / self.volatility_threshold, self.max_reduction_pct)
                size_multiplier = 1.0 - reduction_factor
                
                # Adjust amount
                original_amount = decision.get('amount_usd', 0)
                if original_amount > 0:
                    adjusted_amount = original_amount * size_multiplier
                    decision['amount_usd'] = adjusted_amount
                    decision['reasoning'] = (
                        f"{decision.get('reasoning', '')} "
                        f"(volatility risk: {volatility*100:.1f}% → "
                        f"reduced by {reduction_factor*100:.1f}%)"
                    )
                    
                    if self.logger:
                        self.logger.debug(
                            f"   Volatility risk adjustment for {symbol}: "
                            f"{volatility*100:.1f}% volatility → "
                            f"${original_amount:,.2f} → ${adjusted_amount:,.2f}"
                        )
            
            adjusted_decisions.append(decision)
        
        return adjusted_decisions

