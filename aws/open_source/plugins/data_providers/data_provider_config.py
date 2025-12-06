"""
Data Provider Configuration

Configuration for data provider plugins, including which provider to use
and what data points to fetch.
"""

import os
from typing import Dict, Any, Optional, Type
from dotenv import load_dotenv

load_dotenv()


class DataProviderConfig:
    """
    Configuration for data provider plugins.
    
    Controls which provider to use and what data points to fetch.
    """
    
    def __init__(
        self,
        provider_class: Optional[Type] = None,
        provider_name: str = "alpha_vantage",
        api_key: Optional[str] = None,
        include_fundamentals: bool = True,
        include_financials: bool = True,
        include_historical_prices: bool = True,
        include_quote: bool = True,
        **provider_kwargs
    ):
        """
        Initialize data provider configuration.
        
        Args:
            provider_class: Data provider class to use. If None, uses default from provider_name.
            provider_name: Name of provider ('alpha_vantage', 'fmp', etc.). Used if provider_class is None.
            api_key: API key for the provider. If None, loads from env var.
            include_fundamentals: Whether to fetch company fundamentals
            include_financials: Whether to fetch financial statements
            include_historical_prices: Whether to fetch historical prices
            include_quote: Whether to fetch real-time quote
            **provider_kwargs: Additional kwargs to pass to provider initialization
        """
        self.provider_name = provider_name
        self.provider_class = provider_class
        self.api_key = api_key
        self.include_fundamentals = include_fundamentals
        self.include_financials = include_financials
        self.include_historical_prices = include_historical_prices
        self.include_quote = include_quote
        self.provider_kwargs = provider_kwargs
        
        # Initialize provider if class not provided
        if self.provider_class is None:
            self.provider_class = self._get_provider_class(provider_name)
        
        # Get API key if not provided
        if self.api_key is None:
            self.api_key = self._get_api_key_for_provider(provider_name)
    
    def _get_provider_class(self, provider_name: str) -> Type:
        """Get provider class by name."""
        if provider_name == "alpha_vantage":
            from .alpha_vantage_provider import AlphaVantageProvider
            return AlphaVantageProvider
        elif provider_name == "fmp":
            # Future: Add FMP provider
            raise ValueError(f"Provider '{provider_name}' not yet implemented")
        else:
            raise ValueError(f"Unknown provider: {provider_name}")
    
    def _get_api_key_for_provider(self, provider_name: str) -> Optional[str]:
        """Get API key from environment variable for provider."""
        env_var_map = {
            "alpha_vantage": "ALPHA_VANTAGE_API_KEY",
            "fmp": "FMP_API_KEY"
        }
        
        env_var = env_var_map.get(provider_name)
        if env_var:
            return os.getenv(env_var)
        return None
    
    def create_provider(self):
        """
        Create and return a configured data provider instance.
        
        Returns:
            Initialized data provider instance
        """
        kwargs = {"api_key": self.api_key}
        kwargs.update(self.provider_kwargs)
        
        return self.provider_class(**kwargs)
    
    def get_data_config(self) -> Dict[str, Any]:
        """
        Get configuration dict for get_data() call.
        
        Returns:
            Dictionary with parameters for provider.get_data()
        """
        return {
            "include_fundamentals": self.include_fundamentals,
            "include_financials": self.include_financials
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "provider_name": self.provider_name,
            "include_fundamentals": self.include_fundamentals,
            "include_financials": self.include_financials,
            "include_historical_prices": self.include_historical_prices,
            "include_quote": self.include_quote,
            "provider_kwargs": self.provider_kwargs
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'DataProviderConfig':
        """Create config from dictionary."""
        return cls(**config_dict)
    
    @classmethod
    def default(cls) -> 'DataProviderConfig':
        """Create default configuration (Alpha Vantage)."""
        return cls(
            provider_name="alpha_vantage",
            include_fundamentals=True,
            include_financials=True,
            include_historical_prices=True,
            include_quote=True
        )


# Default configuration instance
default_config = DataProviderConfig.default()

