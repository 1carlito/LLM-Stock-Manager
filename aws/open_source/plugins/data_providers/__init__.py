"""
Data Provider Plugins

Default: Alpha Vantage (REST API)
"""

from .alpha_vantage_provider import AlphaVantageProvider
from .data_provider_config import DataProviderConfig, default_config

# Default data provider
DefaultDataProvider = AlphaVantageProvider

__all__ = [
    'AlphaVantageProvider', 
    'DefaultDataProvider',
    'DataProviderConfig',
    'default_config'
]
