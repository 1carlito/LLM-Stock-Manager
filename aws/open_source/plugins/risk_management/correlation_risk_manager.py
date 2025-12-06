"""
correlation_risk_manager.py: Risk manager that limits correlated positions.

Prevents over-concentration in highly correlated stocks.
"""

from typing import List, Dict, Any
from .base_risk_manager import BaseRiskManager


class CorrelationRiskManager(BaseRiskManager):
    """
    Risk manager that limits positions in highly correlated stocks.
    
    Reduces position sizes if portfolio already has correlated positions.
    """
    
    def __init__(self, portfolio: Dict[str, Any], risk_config=None, logger=None,
                 correlation_threshold: float = 0.70,  # 70% correlation threshold
                 max_correlated_pct: float = 0.40):    # Max 40% in correlated stocks
        """
        Initialize correlation risk manager.
        
        Args:
            portfolio: Portfolio state dictionary
            risk_config: RiskConfig instance
            logger: Optional logger
            correlation_threshold: Correlation above which stocks are considered correlated
            max_correlated_pct: Maximum % of portfolio in correlated stocks
        """
        super().__init__(portfolio, risk_config, logger)
        self.correlation_threshold = correlation_threshold
        self.max_correlated_pct = max_correlated_pct
    
    def _get_correlation(self, symbol1: str, symbol2: str) -> float:
        """
        Get correlation between two symbols.
        
        Args:
            symbol1: First stock symbol
            symbol2: Second stock symbol
        
        Returns:
            Correlation as decimal (0.0 to 1.0)
        """
        # Try to get from portfolio state
        if 'correlations' in self.portfolio:
            corr_matrix = self.portfolio['correlations']
            if symbol1 in corr_matrix and symbol2 in corr_matrix[symbol1]:
                return float(corr_matrix[symbol1][symbol2])
        
        # Fallback: Estimate from sector (same sector = higher correlation)
        # This is a simplified model - real implementation would use historical returns
        sectors = self.portfolio.get('sectors', {})
        if symbol1 in sectors and symbol2 in sectors:
            if sectors[symbol1] == sectors[symbol2]:
                return 0.60  # Same sector = 60% correlation
            else:
                return 0.20  # Different sectors = 20% correlation
        
        # Default: assume moderate correlation
        return 0.30
    
    def _count_correlated_positions(self, symbol: str, portfolio_state: Dict[str, Any]) -> int:
        """
        Count how many existing positions are correlated with the new symbol.
        
        Args:
            symbol: New symbol to check
            portfolio_state: Current portfolio state
        
        Returns:
            Number of correlated positions
        """
        positions = portfolio_state.get('positions', {})
        short_positions = portfolio_state.get('short_positions', {})
        
        all_positions = set(positions.keys()) | set(short_positions.keys())
        correlated_count = 0
        
        for existing_symbol in all_positions:
            if existing_symbol == symbol:
                continue
            
            correlation = self._get_correlation(symbol, existing_symbol)
            if correlation >= self.correlation_threshold:
                correlated_count += 1
        
        return correlated_count
    
    def evaluate(self, decisions: List[Dict[str, Any]], 
                portfolio_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evaluate decisions and adjust for correlation risk.
        
        Args:
            decisions: List of trading decisions
            portfolio_state: Current portfolio state
        
        Returns:
            List of adjusted decisions
        """
        adjusted_decisions = []
        total_value = portfolio_state.get('total_value', portfolio_state.get('cash', 0))
        
        for decision in decisions:
            symbol = decision.get('symbol')
            action = decision.get('action', '').upper()
            
            # Only adjust BUY and SHORT positions
            if action not in ('BUY', 'SHORT'):
                adjusted_decisions.append(decision)
                continue
            
            # Count correlated positions
            correlated_count = self._count_correlated_positions(symbol, portfolio_state)
            
            if correlated_count > 0:
                # Reduce position size based on number of correlated positions
                # More correlated positions = more reduction
                reduction_factor = min(correlated_count * 0.15, 0.50)  # Max 50% reduction
                size_multiplier = 1.0 - reduction_factor
                
                original_amount = decision.get('amount_usd', 0)
                if original_amount > 0:
                    adjusted_amount = original_amount * size_multiplier
                    decision['amount_usd'] = adjusted_amount
                    decision['reasoning'] = (
                        f"{decision.get('reasoning', '')} "
                        f"(correlation risk: {correlated_count} correlated positions → "
                        f"reduced by {reduction_factor*100:.1f}%)"
                    )
                    
                    if self.logger:
                        self.logger.debug(
                            f"   Correlation risk adjustment for {symbol}: "
                            f"{correlated_count} correlated positions → "
                            f"${original_amount:,.2f} → ${adjusted_amount:,.2f}"
                        )
            
            adjusted_decisions.append(decision)
        
        return adjusted_decisions

