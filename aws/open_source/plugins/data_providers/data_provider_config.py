"""
Data Provider Configuration

Configuration for data provider plugins, including which provider to use
and what data points to fetch.

Available Providers:
1. Alpha Vantage - Default provider with comprehensive coverage
2. OpenBB - Alternative provider (coming soon)
"""

import os
from typing import Dict, Any, Optional, Type
from dotenv import load_dotenv

load_dotenv()

# Alpha Vantage Capabilities
ALPHA_VANTAGE_CAPABILITIES = {
    "price_data": {
        "daily_time_series": True,
        "adjusted_prices": True,
        "historical_data": "Up to 20 years",
        "real_time_quote": True,
        "intraday": False,  # Premium only
    },
    "fundamental_data": {
        "company_overview": True,
        "income_statement": True,
        "balance_sheet": True,
        "cash_flow": True,
        "earnings": True,
        "ratios": True,  # P/E, P/B, etc.
    },
    "technical_indicators": {
        "rsi": True,
        "macd": True,
        "sma": True,
        "ema": True,
        "bollinger_bands": True,
        "stochastic": True,
        "50+ indicators": True,
    },
    "news_sentiment": {
        "stock_news": True,
        "market_news": True,
        "sentiment_scores": True,
        "article_metadata": True,
        "endpoint": "NEWS_SENTIMENT",
    },
    "rate_limits": {
        "free_tier": "5 calls/min, 500 calls/day",
        "news_free_tier": "25 calls/day",
        "premium": "Higher limits available",
    },
    "coverage": {
        "valuation_agent": "95%",  # All technical indicators, prices, volume
        "fundamental_agent": "90%",  # Financial statements, ratios, company data
        "sentiment_agent": "80%",  # News and sentiment (free tier limited)
    }
}


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
        """
        Get provider class by name.
        
        Available providers:
        - 'alpha_vantage': Alpha Vantage API (default)
          Capabilities: Price data, fundamentals, technical indicators, news/sentiment
          Coverage: ValuationAgent 95%, FundamentalAgent 90%, SentimentAgent 80%
          Rate limits: 5 calls/min, 500 calls/day (free tier)
        
        - 'openbb': OpenBB Platform
          Capabilities: Comprehensive data via unified interface (350+ providers)
          Coverage: ValuationAgent 100%, FundamentalAgent 100%, SentimentAgent 50%
          Rate limits: Managed by OpenBB across providers
          Installation: pip install openbb-platform
        """
        if provider_name == "alpha_vantage":
            from .alpha_vantage_provider import AlphaVantageProvider
            return AlphaVantageProvider
        elif provider_name == "openbb":
            from .openbb_provider import OpenBBProvider
            return OpenBBProvider
        elif provider_name == "fmp":
            # Future: Add FMP provider
            raise ValueError(
                f"Provider '{provider_name}' not yet implemented. "
                "Available providers: 'alpha_vantage', 'openbb'"
            )
        else:
            available = ["alpha_vantage", "openbb"]
            raise ValueError(
                f"Unknown provider: {provider_name}. "
                f"Available providers: {', '.join(available)}"
            )
    
    def _get_api_key_for_provider(self, provider_name: str) -> Optional[str]:
        """
        Get API key from environment variable for provider.
        
        Environment variables:
        - Alpha Vantage: ALPHA_VANTAGE_API_KEY
        - OpenBB: OPENBB_API_KEY (when implemented)
        - FMP: FMP_API_KEY (when implemented)
        """
        env_var_map = {
            "alpha_vantage": "ALPHA_VANTAGE_API_KEY",
            "openbb": "OPENBB_API_KEY",
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
        kwargs = {}
        
        # Alpha Vantage uses 'api_key'
        if self.provider_name == "alpha_vantage":
            kwargs["api_key"] = self.api_key
        
        # OpenBB uses 'api_key' for PAT and 'provider' for preferred provider
        elif self.provider_name == "openbb":
            kwargs["api_key"] = self.api_key
            if "provider" in self.provider_kwargs:
                kwargs["provider"] = self.provider_kwargs["provider"]
        
        # Add any other provider-specific kwargs
        kwargs.update({k: v for k, v in self.provider_kwargs.items() if k != "provider"})
        
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
        """
        Create default configuration (Alpha Vantage).
        
        Alpha Vantage is the default provider with:
        - 95% coverage for ValuationAgent (technical indicators, prices)
        - 90% coverage for FundamentalAgent (financial statements, ratios)
        - 80% coverage for SentimentAgent (news and sentiment)
        - Free tier: 5 calls/min, 500 calls/day
        """
        return cls(
            provider_name="alpha_vantage",
            include_fundamentals=True,
            include_financials=True,
            include_historical_prices=True,
            include_quote=True
        )
    
    @classmethod
    def alpha_vantage(cls, **kwargs) -> 'DataProviderConfig':
        """
        Create Alpha Vantage configuration.
        
        Alpha Vantage Capabilities:
        - Price Data: Daily time series (up to 20 years), adjusted prices, real-time quotes
        - Fundamental Data: Company overview, income statements, balance sheets, cash flow, earnings
        - Technical Indicators: RSI, MACD, SMA, EMA, Bollinger Bands, 50+ indicators
        - News/Sentiment: Stock and market news with sentiment scores (NEWS_SENTIMENT endpoint)
        
        Rate Limits:
        - Free tier: 5 calls/min, 500 calls/day
        - News free tier: 25 calls/day
        - Premium: Higher limits available
        
        Coverage:
        - ValuationAgent: 95% (all technical indicators, prices, volume)
        - FundamentalAgent: 90% (financial statements, ratios, company data)
        - SentimentAgent: 80% (news and sentiment, free tier limited)
        
        Args:
            **kwargs: Additional configuration options
        
        Returns:
            DataProviderConfig configured for Alpha Vantage
        """
        return cls(
            provider_name="alpha_vantage",
            include_fundamentals=kwargs.get('include_fundamentals', True),
            include_financials=kwargs.get('include_financials', True),
            include_historical_prices=kwargs.get('include_historical_prices', True),
            include_quote=kwargs.get('include_quote', True),
            **{k: v for k, v in kwargs.items() if k not in [
                'include_fundamentals', 'include_financials', 
                'include_historical_prices', 'include_quote'
            ]}
        )
    
    @classmethod
    def openbb(cls, provider: str = None, **kwargs) -> 'DataProviderConfig':
        """
        Create OpenBB configuration.
        
        OpenBB Capabilities:
        - Price Data: Historical prices, VWAP, multiple providers
        - Fundamental Data: Complete financial statements via unified interface
        - Technical Indicators: RSI, MACD, Moving Averages, 50+ indicators
        - News: Available via some providers (sentiment needs custom processing)
        
        Coverage:
        - ValuationAgent: 100% (all technical indicators, prices, volume)
        - FundamentalAgent: 100% (financial statements, ratios, company data)
        - SentimentAgent: 50% (news available, sentiment needs processing)
        
        Installation:
        - pip install openbb-platform
        
        Args:
            provider: Preferred OpenBB provider (e.g., 'yahoo', 'alpha_vantage', 'polygon')
                     Default: 'yahoo' (free, no API key needed)
            **kwargs: Additional configuration options
        
        Returns:
            DataProviderConfig configured for OpenBB
        """
        return cls(
            provider_name="openbb",
            include_fundamentals=kwargs.get('include_fundamentals', True),
            include_financials=kwargs.get('include_financials', True),
            include_historical_prices=kwargs.get('include_historical_prices', True),
            include_quote=kwargs.get('include_quote', True),
            provider=provider,  # Pass provider to OpenBBProvider
            **{k: v for k, v in kwargs.items() if k not in [
                'include_fundamentals', 'include_financials', 
                'include_historical_prices', 'include_quote'
            ]}
        )
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get capabilities for the configured provider.
        
        Returns:
            Dictionary with provider capabilities and coverage information
        """
        if self.provider_name == "alpha_vantage":
            return ALPHA_VANTAGE_CAPABILITIES.copy()
        elif self.provider_name == "openbb":
            return {
                "price_data": {
                    "daily_time_series": True,
                    "adjusted_prices": True,
                    "historical_data": "Up to 20+ years",
                    "real_time_quote": True,
                    "vwap": True,
                },
                "fundamental_data": {
                    "company_overview": True,
                    "income_statement": True,
                    "balance_sheet": True,
                    "cash_flow": True,
                    "earnings": True,
                    "ratios": True,
                },
                "technical_indicators": {
                    "rsi": True,
                    "macd": True,
                    "sma": True,
                    "ema": True,
                    "50+ indicators": True,
                },
                "news_sentiment": {
                    "stock_news": "Available via some providers",
                    "market_news": "Available via some providers",
                    "sentiment_scores": "Needs custom processing",
                },
                "rate_limits": {
                    "managed_by_openbb": True,
                    "multiple_providers": "350+ providers available",
                    "free_providers": "Yahoo Finance (no API key needed)",
                },
                "coverage": {
                    "valuation_agent": "100%",
                    "fundamental_agent": "100%",
                    "sentiment_agent": "50%",
                }
            }
        else:
            return {}


# Default configuration instance (Alpha Vantage)
default_config = DataProviderConfig.default()

# OpenBB Capabilities
OPENBB_CAPABILITIES = {
    "price_data": {
        "daily_time_series": True,
        "adjusted_prices": True,
        "historical_data": "Up to 20+ years",
        "real_time_quote": True,
        "vwap": True,
    },
    "fundamental_data": {
        "company_overview": True,
        "income_statement": True,
        "balance_sheet": True,
        "cash_flow": True,
        "earnings": True,
        "ratios": True,
    },
    "technical_indicators": {
        "rsi": True,
        "macd": True,
        "sma": True,
        "ema": True,
        "50+ indicators": True,
    },
    "news_sentiment": {
        "stock_news": "Available via some providers",
        "market_news": "Available via some providers",
        "sentiment_scores": "Needs custom processing",
    },
    "rate_limits": {
        "managed_by_openbb": True,
        "multiple_providers": "350+ providers available",
        "free_providers": "Yahoo Finance (no API key needed)",
    },
    "coverage": {
        "valuation_agent": "100%",
        "fundamental_agent": "100%",
        "sentiment_agent": "50%",
    }
}

# Available provider options
AVAILABLE_PROVIDERS = {
    "alpha_vantage": {
        "name": "Alpha Vantage",
        "status": "available",
        "capabilities": ALPHA_VANTAGE_CAPABILITIES,
        "config_class": DataProviderConfig.alpha_vantage
    },
    "openbb": {
        "name": "OpenBB",
        "status": "available",
        "capabilities": OPENBB_CAPABILITIES,
        "config_class": DataProviderConfig.openbb,
        "installation": "pip install openbb-platform"
    }
}

