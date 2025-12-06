"""
Risk management plugins for backtesting.

Provides:
- Risk level configuration (conservative, moderate, aggressive)
- Risk management plugins (custom risk rules)
"""

from .base_risk_manager import BaseRiskManager
from .risk_config import RiskConfig, get_risk_config
from .volatility_risk_manager import VolatilityRiskManager
from .correlation_risk_manager import CorrelationRiskManager
from .sector_risk_manager import SectorRiskManager

__all__ = [
    'BaseRiskManager',
    'RiskConfig',
    'get_risk_config',
    'VolatilityRiskManager',
    'CorrelationRiskManager',
    'SectorRiskManager'
]

