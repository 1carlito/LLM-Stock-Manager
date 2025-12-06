"""
base_strategy.py: Base class for all trading strategies.

This is an abstract interface - all strategies must implement analyze().
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseStrategy(ABC):
    """
    Base class for all trading strategies.
    
    This is an interface - it defines what all strategies must implement.
    Different strategies (LLM, technical, fundamental, etc.) inherit from this.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize strategy.
        
        Args:
            config: Optional configuration dict (API keys, parameters, etc.)
        """
        self.config = config or {}
    
    @abstractmethod
    def analyze(self, symbol: str, data: Dict[str, Any], 
                portfolio_state: Dict[str, Any], 
                current_date: str) -> Dict[str, Any]:
        """
        Analyze a stock and make a trading decision.
        
        This is the main method all strategies must implement.
        Different strategies implement this differently:
        - LLMStrategy: Uses LLM to analyze
        - TechnicalStrategy: Uses technical indicators
        - FundamentalStrategy: Uses financial metrics
        - MultiFactorStrategy: Combines multiple signals
        
        Args:
            symbol: Stock symbol to analyze
            data: Market data from data provider (prices, indicators, news, etc.)
            portfolio_state: Current portfolio state (optional, for portfolio-aware strategies)
            current_date: Trading date
        
        Returns:
            Decision dict with:
            - symbol: Stock symbol
            - decision: "BUY", "SELL", "SHORT", "HOLD", or "NEUTRAL"
            - confidence: 0.0 to 1.0 (or 0-100)
            - reasoning: Explanation of the decision
            - current_price: Current stock price
            - amount_usd: Optional suggested allocation (before waterfall)
        """
        pass

