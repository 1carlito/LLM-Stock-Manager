"""
Data Provider Plugins

Available Providers:
1. Alpha Vantage (default) - REST API with comprehensive coverage
2. OpenBB - Unified interface for 350+ providers

Default: Alpha Vantage (REST API)
"""

from .alpha_vantage_provider import AlphaVantageProvider
from .openbb_provider import OpenBBProvider
from .data_provider_config import (
    DataProviderConfig, 
    default_config,
    ALPHA_VANTAGE_CAPABILITIES,
    OPENBB_CAPABILITIES,
    AVAILABLE_PROVIDERS
)

# Default data provider
DefaultDataProvider = AlphaVantageProvider

__all__ = [
    'AlphaVantageProvider',
    'OpenBBProvider',
    'DefaultDataProvider',
    'DataProviderConfig',
    'default_config',
    'ALPHA_VANTAGE_CAPABILITIES',
    'OPENBB_CAPABILITIES',
    'AVAILABLE_PROVIDERS'
]
