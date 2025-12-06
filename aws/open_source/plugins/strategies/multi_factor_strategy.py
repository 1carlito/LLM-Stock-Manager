"""
multi_factor_strategy.py: Multi-factor strategy that combines multiple signals.

This is DIFFERENT from LLMStrategy:
- LLMStrategy: Uses LLM to analyze (AI-based)
- MultiFactorStrategy: Combines technical + fundamental + sentiment signals (rule-based)

Can work with or without LLM.
"""

from typing import Dict, Any
from .base_strategy import BaseStrategy


class MultiFactorStrategy(BaseStrategy):
    """
    Multi-factor strategy that combines multiple signals.
    
    This is a RULE-BASED strategy (not LLM-based):
    - Calculates scores from technical indicators
    - Calculates scores from fundamental metrics
    - Calculates scores from sentiment
    - Combines them with weights
    
    This is DIFFERENT from LLMStrategy:
    - LLMStrategy: Asks LLM "should I buy this?"
    - MultiFactorStrategy: Calculates scores and applies rules
    """
    
    def __init__(self, config: Dict[str, Any] = None,
                 technical_weight: float = 0.4,
                 fundamental_weight: float = 0.4,
                 sentiment_weight: float = 0.2):
        """
        Initialize multi-factor strategy.
        
        Args:
            config: Optional config
            technical_weight: Weight for technical signals (default: 0.4)
            fundamental_weight: Weight for fundamental signals (default: 0.4)
            sentiment_weight: Weight for sentiment signals (default: 0.2)
        """
        super().__init__(config)
        self.technical_weight = technical_weight
        self.fundamental_weight = fundamental_weight
        self.sentiment_weight = sentiment_weight
    
    def _technical_score(self, data: Dict[str, Any]) -> float:
        """
        Calculate technical analysis score (0.0 to 1.0).
        
        Args:
            data: Market data
        
        Returns:
            Technical score (0.0 = bearish, 1.0 = bullish)
        """
        score = 0.5  # Neutral
        
        # RSI signals
        rsi = data.get('rsi', 50)
        if rsi < 30:
            score += 0.3  # Oversold = bullish
        elif rsi > 70:
            score -= 0.3  # Overbought = bearish
        
        # MACD signals
        macd = data.get('macd', 0)
        if macd > 0:
            score += 0.2  # Bullish
        else:
            score -= 0.2  # Bearish
        
        # Price vs moving averages
        price = data.get('current_price', 0)
        sma_20 = data.get('moving_averages', {}).get('sma_20', price)
        if price > sma_20:
            score += 0.1  # Above SMA = bullish
        else:
            score -= 0.1  # Below SMA = bearish
        
        return max(0.0, min(1.0, score))  # Clamp to 0-1
    
    def _fundamental_score(self, data: Dict[str, Any]) -> float:
        """
        Calculate fundamental analysis score (0.0 to 1.0).
        
        Args:
            data: Market data
        
        Returns:
            Fundamental score (0.0 = bearish, 1.0 = bullish)
        """
        score = 0.5  # Neutral
        
        # P/E ratio signals
        pe = data.get('pe_ratio', 0)
        if pe > 0:
            if pe < 15:
                score += 0.3  # Low P/E = undervalued
            elif pe > 40:
                score -= 0.3  # High P/E = overvalued
        
        # Revenue growth
        revenue_growth = data.get('revenue_growth', 0)
        if revenue_growth > 0.20:
            score += 0.2  # Strong growth
        elif revenue_growth < 0:
            score -= 0.2  # Negative growth
        
        return max(0.0, min(1.0, score))  # Clamp to 0-1
    
    def _sentiment_score(self, data: Dict[str, Any]) -> float:
        """
        Get sentiment score (0.0 to 1.0).
        
        Note: This score comes from the data provider, which may have used LLM
        to analyze news/social media. The strategy itself doesn't call LLM.
        
        Args:
            data: Market data (sentiment_score should be provided by data provider)
        
        Returns:
            Sentiment score (0.0 = negative, 1.0 = positive)
        """
        # Use sentiment_score if available (from data provider)
        # Data provider may have used LLM to calculate this, but strategy doesn't know/care
        return data.get('sentiment_score', 0.5)
    
    def analyze(self, symbol: str, data: Dict[str, Any], 
                portfolio_state: Dict[str, Any], 
                current_date: str) -> Dict[str, Any]:
        """
        Analyze stock using multi-factor approach.
        
        This combines technical + fundamental + sentiment signals
        using weighted scores (NOT using LLM).
        
        Args:
            symbol: Stock symbol
            data: Market data
            portfolio_state: Portfolio state (not used)
            current_date: Trading date
        
        Returns:
            Decision dict
        """
        # Calculate individual scores
        technical = self._technical_score(data)
        fundamental = self._fundamental_score(data)
        sentiment = self._sentiment_score(data)
        
        # Weighted combination
        total_score = (
            technical * self.technical_weight +
            fundamental * self.fundamental_weight +
            sentiment * self.sentiment_weight
        )
        
        # Convert score to decision
        if total_score > 0.7:
            decision = 'BUY'
            confidence = total_score
            reasoning = f"Multi-factor score: {total_score:.2f} (Technical: {technical:.2f}, Fundamental: {fundamental:.2f}, Sentiment: {sentiment:.2f})"
        elif total_score < 0.3:
            decision = 'SELL'
            confidence = 1.0 - total_score
            reasoning = f"Multi-factor score: {total_score:.2f} (Technical: {technical:.2f}, Fundamental: {fundamental:.2f}, Sentiment: {sentiment:.2f})"
        else:
            decision = 'HOLD'
            confidence = 0.5
            reasoning = f"Multi-factor score: {total_score:.2f} - neutral signals"
        
        return {
            'symbol': symbol,
            'decision': decision,
            'confidence': confidence,
            'reasoning': reasoning,
            'current_price': data.get('current_price', 0)
        }

