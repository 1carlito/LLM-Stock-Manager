"""
Data Provider Plugins

Default: Alpha Vantage (REST API)
"""

from .alpha_vantage_provider import AlphaVantageProvider

# Default data provider
DefaultDataProvider = AlphaVantageProvider

__all__ = ['AlphaVantageProvider', 'DefaultDataProvider']
