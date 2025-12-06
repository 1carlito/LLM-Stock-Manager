# Data Fetching Architecture: Engine vs Data Provider

## Question: Where Should Data Fetching Configuration Live?

**Answer: Both levels, but different responsibilities:**

1. **Engine/Orchestrator** (`engine.py` or `ParallelOrchestrator.py`):
   - **Selects** which data provider to use
   - **Creates** the data provider with configuration
   - **Coordinates** data fetching workflow

2. **Data Provider Plugin**:
   - **Defines** what data points are available
   - **Implements** the configuration for those data points
   - **Handles** provider-specific settings

---

## Architecture Layers

### Layer 1: Engine/Orchestrator (High-Level)

```python
# engine.py or ParallelOrchestrator.py
class BacktestEngine:
    def __init__(self, data_provider_config=None):
        # Engine selects and creates data provider
        if data_provider_config is None:
            data_provider_config = DataProviderConfig.default()
        
        self.data_provider = data_provider_config.create_provider()
        self.data_config = data_provider_config.get_data_config()
    
    def fetch_data(self, symbol, current_date):
        # Engine calls data provider with config
        return self.data_provider.get_data(
            symbol, 
            current_date,
            **self.data_config  # Config from engine
        )
```

**Engine Responsibilities:**
- ✅ Select which provider to use (Alpha Vantage, FMP, etc.)
- ✅ Create provider instance
- ✅ Pass configuration to provider
- ✅ Coordinate data fetching workflow

### Layer 2: Data Provider Plugin (Low-Level)

```python
# plugins/data_providers/data_provider_config.py
class DataProviderConfig:
    def __init__(
        self,
        provider_name="alpha_vantage",
        include_fundamentals=True,  # Data point config
        include_financials=True,    # Data point config
        ...
    ):
        # Provider-specific configuration
        pass
```

**Data Provider Responsibilities:**
- ✅ Define available data points
- ✅ Implement configuration for data points
- ✅ Handle provider-specific settings (API keys, rate limits)

---

## Recommended Architecture

### Option 1: Engine Handles Provider Selection (Recommended)

```python
# engine.py
from plugins.data_providers import DataProviderConfig, DefaultDataProvider

class BacktestEngine:
    def __init__(self, 
                 data_provider_name="alpha_vantage",
                 include_fundamentals=True,
                 include_financials=True):
        # Engine creates config
        self.data_provider_config = DataProviderConfig(
            provider_name=data_provider_name,
            include_fundamentals=include_fundamentals,
            include_financials=include_financials
        )
        
        # Engine creates provider
        self.data_provider = self.data_provider_config.create_provider()
    
    def fetch_stock_data(self, symbol, current_date):
        # Engine calls provider with config
        return self.data_provider.get_data(
            symbol,
            current_date,
            **self.data_provider_config.get_data_config()
        )
```

**Benefits:**
- ✅ Engine controls which provider to use
- ✅ Engine controls what data to fetch
- ✅ Easy to switch providers
- ✅ Configuration in one place (engine)

### Option 2: Data Provider Self-Configures (Current)

```python
# Current approach - data provider has its own config
from plugins.data_providers import DataProviderConfig

config = DataProviderConfig(
    provider_name="alpha_vantage",
    include_fundamentals=True
)
provider = config.create_provider()
data = provider.get_data("NVDA", "2025-01-15", **config.get_data_config())
```

**Benefits:**
- ✅ Data provider is self-contained
- ✅ Can be used standalone
- ✅ Configuration lives with provider

**Drawbacks:**
- ❌ Engine doesn't control configuration
- ❌ Harder to switch providers from engine

---

## Recommended: Hybrid Approach

**Engine selects provider, Data Provider defines data points:**

```python
# engine.py
class BacktestEngine:
    def __init__(self, 
                 data_provider_name="alpha_vantage",  # Engine selects
                 data_config=None):                   # Engine controls
        # Engine creates provider config
        if data_config is None:
            data_config = {
                "include_fundamentals": True,
                "include_financials": True
            }
        
        provider_config = DataProviderConfig(
            provider_name=data_provider_name,  # Engine decides
            **data_config                      # Engine controls
        )
        
        self.data_provider = provider_config.create_provider()
        self.data_config = provider_config.get_data_config()
    
    def fetch_data(self, symbol, current_date):
        return self.data_provider.get_data(
            symbol, 
            current_date,
            **self.data_config
        )
```

**Usage:**
```python
# Engine controls everything
engine = BacktestEngine(
    data_provider_name="alpha_vantage",  # Select provider
    data_config={
        "include_fundamentals": True,    # Control data points
        "include_financials": False
    }
)

data = engine.fetch_data("NVDA", "2025-01-15")
```

---

## Answer to Your Question

**You were correct** to have data fetching linked to the data provider plugin, **BUT**:

1. ✅ **Data Provider Plugin** should define data point configuration (what we have)
2. ✅ **Engine/Orchestrator** should select provider and pass config (what we need)

**Best Practice:**
- **Data Provider**: Defines available data points and config structure
- **Engine**: Selects provider and controls which data points to fetch

This gives you:
- **Flexibility**: Engine can switch providers
- **Modularity**: Data provider is self-contained
- **Control**: Engine controls what data to fetch

---

## Implementation

The current `DataProviderConfig` is correct. Now we need:

1. **Engine/Orchestrator** to use it:
   ```python
   # In ParallelOrchestrator.py or engine.py
   from plugins.data_providers import DataProviderConfig
   
   class ParallelBacktest:
       def __init__(self, ..., data_provider_config=None):
           if data_provider_config is None:
               data_provider_config = DataProviderConfig.default()
           self.data_provider = data_provider_config.create_provider()
   ```

2. **Engine** controls data fetching:
   ```python
   def fetch_stock_data(self, symbol, current_date):
       return self.data_provider.get_data(
           symbol,
           current_date,
           **self.data_provider_config.get_data_config()
       )
   ```

---

## Summary

- ✅ **Data Provider Plugin**: Defines data point configuration (correct as-is)
- ✅ **Engine/Orchestrator**: Should select provider and control config (needs integration)
- ✅ **Both are needed**: Provider defines, Engine controls

