"""
sector_risk_manager.py: Risk manager that limits sector concentration.

Prevents over-concentration in a single sector.
"""

from typing import List, Dict, Any
from collections import defaultdict
from .base_risk_manager import BaseRiskManager


class SectorRiskManager(BaseRiskManager):
    """
    Risk manager that limits positions in a single sector.
    
    Reduces position sizes if sector allocation exceeds threshold.
    """
    
    def __init__(self, portfolio: Dict[str, Any], risk_config=None, logger=None,
                 max_sector_pct: float = 0.30):  # Max 30% in any sector
        """
        Initialize sector risk manager.
        
        Args:
            portfolio: Portfolio state dictionary
            risk_config: RiskConfig instance
            logger: Optional logger
            max_sector_pct: Maximum % of portfolio in any single sector
        """
        super().__init__(portfolio, risk_config, logger)
        self.max_sector_pct = max_sector_pct
    
    def _get_sector(self, symbol: str) -> str:
        """
        Get sector for a symbol.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Sector name
        """
        sectors = self.portfolio.get('sectors', {})
        if symbol in sectors:
            return sectors[symbol]
        
        # Default: unknown sector
        return 'Unknown'
    
    def _calculate_sector_allocation(self, portfolio_state: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate current sector allocation percentages.
        
        Args:
            portfolio_state: Current portfolio state
        
        Returns:
            Dict of {sector: allocation_pct}
        """
        positions = portfolio_state.get('positions', {})
        last_prices = portfolio_state.get('last_prices', {})
        total_value = portfolio_state.get('total_value', portfolio_state.get('cash', 0))
        
        if total_value <= 0:
            return {}
        
        sector_values = defaultdict(float)
        
        for symbol, pos in positions.items():
            if pos.get('shares', 0) > 0:
                price = last_prices.get(symbol, pos.get('avg_price', 0))
                position_value = pos['shares'] * price
                sector = self._get_sector(symbol)
                sector_values[sector] += position_value
        
        # Convert to percentages
        sector_allocation = {
            sector: (value / total_value) 
            for sector, value in sector_values.items()
        }
        
        return sector_allocation
    
    def evaluate(self, decisions: List[Dict[str, Any]], 
                portfolio_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evaluate decisions and adjust for sector concentration risk.
        
        Args:
            decisions: List of trading decisions
            portfolio_state: Current portfolio state
        
        Returns:
            List of adjusted decisions
        """
        # Calculate current sector allocation
        sector_allocation = self._calculate_sector_allocation(portfolio_state)
        
        adjusted_decisions = []
        total_value = portfolio_state.get('total_value', portfolio_state.get('cash', 0))
        
        for decision in decisions:
            symbol = decision.get('symbol')
            action = decision.get('action', '').upper()
            
            # Only adjust BUY positions (shorts don't add to sector exposure)
            if action != 'BUY':
                adjusted_decisions.append(decision)
                continue
            
            # Get sector for this symbol
            sector = self._get_sector(symbol)
            
            # Check current sector allocation
            current_sector_pct = sector_allocation.get(sector, 0.0)
            
            if current_sector_pct >= self.max_sector_pct:
                # Sector already at limit - block or reduce trade
                original_amount = decision.get('amount_usd', 0)
                if original_amount > 0:
                    # Calculate how much we can add before hitting limit
                    max_additional = (self.max_sector_pct - current_sector_pct) * total_value
                    
                    if max_additional <= 0:
                        # Already at limit - block trade
                        decision['amount_usd'] = 0
                        decision['action'] = 'NEUTRAL'
                        decision['reasoning'] = (
                            f"{decision.get('reasoning', '')} "
                            f"(blocked: {sector} sector at {current_sector_pct*100:.1f}% limit)"
                        )
                        
                        if self.logger:
                            self.logger.info(
                                f"   Sector risk: Blocked BUY {symbol} - "
                                f"{sector} sector at {current_sector_pct*100:.1f}% limit"
                            )
                    else:
                        # Reduce to stay within limit
                        adjusted_amount = min(original_amount, max_additional)
                        decision['amount_usd'] = adjusted_amount
                        decision['reasoning'] = (
                            f"{decision.get('reasoning', '')} "
                            f"(sector risk: {sector} at {current_sector_pct*100:.1f}% → "
                            f"reduced to ${adjusted_amount:,.2f})"
                        )
                        
                        if self.logger:
                            self.logger.debug(
                                f"   Sector risk adjustment for {symbol}: "
                                f"{sector} at {current_sector_pct*100:.1f}% → "
                                f"${original_amount:,.2f} → ${adjusted_amount:,.2f}"
                            )
            
            adjusted_decisions.append(decision)
        
        return adjusted_decisions

