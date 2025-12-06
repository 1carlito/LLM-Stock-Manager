"""
risk_config.py: Risk level configuration.

Defines risk profiles (conservative, moderate, aggressive) with different limits.
"""

from typing import Dict, Any, Optional
from enum import Enum


class RiskLevel(Enum):
    """Risk tolerance levels."""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class RiskConfig:
    """
    Risk configuration settings.
    
    Defines position limits, leverage limits, and other risk constraints
    based on risk tolerance level.
    """
    
    # Risk level presets
    PRESETS = {
        RiskLevel.CONSERVATIVE: {
            'per_trade_cap_pct': 0.15,      # 15% per trade
            'max_short_pct': 0.15,          # 15% short exposure
            'max_position_pct': 0.15,       # 15% max per stock
            'max_positions': 15,             # Max 15 positions
            'max_drawdown_pct': 0.15,       # Stop at 15% drawdown
            'cash_threshold_pct': 0.30,     # Block shorts at 30% cash
            'volatility_limit': 0.30,        # Max 30% volatility
        },
        RiskLevel.MODERATE: {
            'per_trade_cap_pct': 0.25,      # 25% per trade
            'max_short_pct': 0.25,          # 25% short exposure
            'max_position_pct': 0.25,        # 25% max per stock
            'max_positions': 20,             # Max 20 positions
            'max_drawdown_pct': 0.25,       # Stop at 25% drawdown
            'cash_threshold_pct': 0.25,     # Block shorts at 25% cash
            'volatility_limit': 0.50,        # Max 50% volatility
        },
        RiskLevel.AGGRESSIVE: {
            'per_trade_cap_pct': 0.35,      # 35% per trade
            'max_short_pct': 0.35,          # 35% short exposure
            'max_position_pct': 0.35,        # 35% max per stock
            'max_positions': 25,             # Max 25 positions
            'max_drawdown_pct': 0.35,       # Stop at 35% drawdown
            'cash_threshold_pct': 0.20,     # Block shorts at 20% cash
            'volatility_limit': 0.70,        # Max 70% volatility
        }
    }
    
    def __init__(self, risk_level: RiskLevel = RiskLevel.MODERATE, 
                 custom_settings: Optional[Dict[str, Any]] = None):
        """
        Initialize risk configuration.
        
        Args:
            risk_level: Risk tolerance level (conservative, moderate, aggressive)
            custom_settings: Optional dict to override preset values
        """
        self.risk_level = risk_level
        preset = self.PRESETS[risk_level].copy()
        
        # Override with custom settings if provided
        if custom_settings:
            preset.update(custom_settings)
        
        # Set all config values
        self.per_trade_cap_pct = preset.get('per_trade_cap_pct', 0.25)
        self.max_short_pct = preset.get('max_short_pct', 0.25)
        self.max_position_pct = preset.get('max_position_pct', 0.25)
        self.max_positions = preset.get('max_positions', 20)
        self.max_drawdown_pct = preset.get('max_drawdown_pct', 0.25)
        self.cash_threshold_pct = preset.get('cash_threshold_pct', 0.25)
        self.volatility_limit = preset.get('volatility_limit', 0.50)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            'risk_level': self.risk_level.value,
            'per_trade_cap_pct': self.per_trade_cap_pct,
            'max_short_pct': self.max_short_pct,
            'max_position_pct': self.max_position_pct,
            'max_positions': self.max_positions,
            'max_drawdown_pct': self.max_drawdown_pct,
            'cash_threshold_pct': self.cash_threshold_pct,
            'volatility_limit': self.volatility_limit,
        }
    
    def apply_to_portfolio_state(self, portfolio_state: Dict[str, Any], 
                                 initial_value: float) -> Dict[str, Any]:
        """
        Apply risk config to portfolio state for use by allocator.
        
        Args:
            portfolio_state: Portfolio state dictionary
            initial_value: Initial portfolio value
        
        Returns:
            Updated portfolio state with risk limits
        """
        portfolio_state['max_short_per_stock_pct'] = self.max_short_pct * 100
        portfolio_state['initial_value'] = initial_value
        portfolio_state['max_positions'] = self.max_positions
        portfolio_state['max_drawdown_pct'] = self.max_drawdown_pct
        
        return portfolio_state


def get_risk_config(risk_level: str = "moderate", 
                   custom_settings: Optional[Dict[str, Any]] = None) -> RiskConfig:
    """
    Convenience function to get risk configuration.
    
    Args:
        risk_level: "conservative", "moderate", or "aggressive"
        custom_settings: Optional dict to override preset values
    
    Returns:
        RiskConfig instance
    """
    try:
        level = RiskLevel(risk_level.lower())
    except ValueError:
        level = RiskLevel.MODERATE  # Default to moderate
    
    return RiskConfig(level, custom_settings)

