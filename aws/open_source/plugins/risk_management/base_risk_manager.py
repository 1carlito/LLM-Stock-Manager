"""
base_risk_manager.py: Base class for risk management plugins.

Risk managers evaluate and adjust trading decisions based on risk rules.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseRiskManager(ABC):
    """
    Base class for risk management plugins.
    
    Risk managers can:
    - Evaluate decisions before allocation
    - Adjust position sizes
    - Block trades that violate risk rules
    - Modify portfolio state
    """
    
    def __init__(self, portfolio: Dict[str, Any], risk_config=None, logger=None):
        """
        Initialize risk manager.
        
        Args:
            portfolio: Portfolio state dictionary
            risk_config: RiskConfig instance
            logger: Optional logger
        """
        self.portfolio = portfolio
        self.risk_config = risk_config
        self.logger = logger
    
    @abstractmethod
    def evaluate(self, decisions: List[Dict[str, Any]], 
                portfolio_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evaluate and adjust trading decisions based on risk rules.
        
        Args:
            decisions: List of trading decisions to evaluate
            portfolio_state: Current portfolio state
        
        Returns:
            List of adjusted decisions (may have modified amounts, blocked trades, etc.)
        """
        pass
    
    def should_block_trade(self, decision: Dict[str, Any], 
                          portfolio_state: Dict[str, Any]) -> bool:
        """
        Check if a trade should be blocked.
        
        Override this for custom blocking logic.
        
        Args:
            decision: Trading decision
            portfolio_state: Current portfolio state
        
        Returns:
            True if trade should be blocked
        """
        return False
    
    def adjust_position_size(self, decision: Dict[str, Any],
                            portfolio_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adjust position size based on risk rules.
        
        Override this for custom sizing logic.
        
        Args:
            decision: Trading decision
            portfolio_state: Current portfolio state
        
        Returns:
            Modified decision with adjusted amount_usd
        """
        return decision

