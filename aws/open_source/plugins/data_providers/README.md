# Data Provider Plugins

## Default: Alpha Vantage

**Alpha Vantage** is the default data provider for the backtesting infrastructure.

### Setup

1. Get a free API key: https://www.alphavantage.co/support/#api-key
2. Set environment variable:
   ```bash
   export ALPHA_VANTAGE_API_KEY=your_api_key_here
   ```
3. Or pass directly:
   ```python
   from plugins.data_providers import AlphaVantageProvider
   
   provider = AlphaVantageProvider(api_key="your_key")
   data = provider.get_data("NVDA", current_date="2025-01-15")
   ```

### Features

- ✅ Daily time series (historical prices)
- ✅ Company overview (fundamentals)
- ✅ Financial statements (income, balance sheet, cash flow)
- ✅ Real-time quotes
- ✅ Rate limiting (respects free tier: 5 calls/min, 500/day)

### Usage

```python
from plugins.data_providers import DefaultDataProvider

# Initialize (uses ALPHA_VANTAGE_API_KEY env var)
provider = DefaultDataProvider()

# Get comprehensive data
data = provider.get_data(
    symbol="NVDA",
    current_date="2025-01-15",
    include_fundamentals=True,
    include_financials=True
)

# Access data
print(data['current_price'])
print(data['historical_prices'])
print(data['company_overview'])
```

### API Reference

See `alpha_vantage_provider.py` for full API documentation.

## Adding Custom Data Providers

To add a custom data provider:

1. Create a new provider class:
   ```python
   class CustomDataProvider:
       def get_data(self, symbol: str, current_date: str) -> Dict:
           # Your implementation
           pass
   ```

2. Register in `__init__.py`:
   ```python
   from .custom_provider import CustomDataProvider
   ```

3. Use in strategies:
   ```python
   from plugins.data_providers import CustomDataProvider
   provider = CustomDataProvider()
   data = provider.get_data(symbol, current_date)
   ```

