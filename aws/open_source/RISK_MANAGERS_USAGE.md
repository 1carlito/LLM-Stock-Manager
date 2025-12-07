# Risk Managers: How to Initialize and Use

## Overview

**Yes, risk managers are initialized independently.** Each risk manager is a separate class instance that you create and use as needed.

---

## Current Status

⚠️ **Risk managers are NOT currently integrated into `ParallelOrchestrator.py` (engine.py)**

They exist as **optional plugins** that you can add to your workflow if needed.

---

## How to Initialize

### Option 1: Initialize Independently (Recommended)

```python
from plugins.risk_management import (
    CorrelationRiskManager,
    SectorRiskManager,
    RiskConfig,
    RiskLevel
)

# Initialize risk config (optional, but recommended)
risk_config = RiskConfig(risk_level=RiskLevel.MODERATE)

# Initialize each risk manager independently
correlation_rm = CorrelationRiskManager(
    portfolio=self.portfolio,
    risk_config=risk_config,
    logger=self.logger,
    correlation_threshold=0.70,  # Optional: override default
    max_correlated_pct=0.40       # Optional: override default
)

sector_rm = SectorRiskManager(
    portfolio=self.portfolio,
    risk_config=risk_config,
    logger=self.logger,
    max_sector_pct=0.30  # Optional: override default
)
```

### Option 2: Initialize with Custom Settings

```python
# Custom correlation manager
correlation_rm = CorrelationRiskManager(
    portfolio=self.portfolio,
    risk_config=None,  # No risk config
    logger=self.logger,
    correlation_threshold=0.80,  # Stricter: 80% correlation
    max_correlated_pct=0.30      # Lower limit: 30%
)

# Custom sector manager
sector_rm = SectorRiskManager(
    portfolio=self.portfolio,
    risk_config=None,
    logger=self.logger,
    max_sector_pct=0.25  # Stricter: 25% max per sector
)
```

### Option 3: Use Only One

```python
# Only use sector risk manager
sector_rm = SectorRiskManager(
    portfolio=self.portfolio,
    risk_config=None,
    logger=self.logger
)

# Don't initialize correlation manager at all
```

---

## How to Use in Orchestrator

### Integration Point

Add risk managers **after** converting decisions but **before** waterfall allocation:

```python
# In ParallelOrchestrator.run_backtest() or similar

# 1. Get stock decisions from ReasoningAgent
stock_decisions = [...]  # From ReasoningAgent

# 2. Convert to portfolio_decisions format
portfolio_decisions = self._convert_to_portfolio_decisions(stock_decisions)

# 3. Apply risk managers (if enabled)
if self.use_risk_managers:
    # Initialize risk managers (if not already done)
    if not hasattr(self, 'correlation_rm'):
        self.correlation_rm = CorrelationRiskManager(
            portfolio=self.portfolio,
            risk_config=self.risk_config,
            logger=self.logger
        )
    if not hasattr(self, 'sector_rm'):
        self.sector_rm = SectorRiskManager(
            portfolio=self.portfolio,
            risk_config=self.risk_config,
            logger=self.logger
        )
    
    # Apply risk managers (in sequence)
    portfolio_decisions = self.correlation_rm.evaluate(
        portfolio_decisions, 
        portfolio_state
    )
    portfolio_decisions = self.sector_rm.evaluate(
        portfolio_decisions, 
        portfolio_state
    )

# 4. Apply waterfall allocation
allocated_decisions = allocate_decisions(
    decisions_list=portfolio_decisions,
    portfolio_state=portfolio_state,
    stock_decisions=stock_decisions,
    ...
)
```

---

## Initialization Parameters

### BaseRiskManager (All risk managers inherit this)

```python
def __init__(self, 
             portfolio: Dict[str, Any],  # Required: Portfolio state
             risk_config=None,            # Optional: RiskConfig instance
             logger=None):                # Optional: Logger
```

### CorrelationRiskManager

```python
def __init__(self, 
             portfolio: Dict[str, Any],
             risk_config=None,
             logger=None,
             correlation_threshold: float = 0.70,  # 70% correlation
             max_correlated_pct: float = 0.40):    # Max 40% correlated
```

### SectorRiskManager

```python
def __init__(self, 
             portfolio: Dict[str, Any],
             risk_config=None,
             logger=None,
             max_sector_pct: float = 0.30):  # Max 30% per sector
```

---

## Usage Patterns

### Pattern 1: Use Both (Recommended for Diversification)

```python
correlation_rm = CorrelationRiskManager(portfolio, risk_config, logger)
sector_rm = SectorRiskManager(portfolio, risk_config, logger)

decisions = correlation_rm.evaluate(decisions, portfolio_state)
decisions = sector_rm.evaluate(decisions, portfolio_state)
```

### Pattern 2: Use Only One

```python
# Only correlation risk
correlation_rm = CorrelationRiskManager(portfolio, risk_config, logger)
decisions = correlation_rm.evaluate(decisions, portfolio_state)

# OR only sector risk
sector_rm = SectorRiskManager(portfolio, risk_config, logger)
decisions = sector_rm.evaluate(decisions, portfolio_state)
```

### Pattern 3: Conditional (Based on Strategy)

```python
if strategy_type == "diversified":
    correlation_rm = CorrelationRiskManager(portfolio, risk_config, logger)
    sector_rm = SectorRiskManager(portfolio, risk_config, logger)
    decisions = correlation_rm.evaluate(decisions, portfolio_state)
    decisions = sector_rm.evaluate(decisions, portfolio_state)
elif strategy_type == "sector_focused":
    # Only use sector risk (allows correlation)
    sector_rm = SectorRiskManager(portfolio, risk_config, logger)
    decisions = sector_rm.evaluate(decisions, portfolio_state)
else:
    # No risk managers
    pass
```

---

## Where to Initialize

### Option A: In `__init__` (Persistent)

```python
class ParallelBacktest:
    def __init__(self, ...):
        # ... existing init code ...
        
        # Initialize risk managers (optional)
        self.use_risk_managers = True  # Flag to enable/disable
        if self.use_risk_managers:
            risk_config = RiskConfig(risk_level=RiskLevel.MODERATE)
            self.correlation_rm = CorrelationRiskManager(
                portfolio=self.portfolio,
                risk_config=risk_config,
                logger=self.logger
            )
            self.sector_rm = SectorRiskManager(
                portfolio=self.portfolio,
                risk_config=risk_config,
                logger=self.logger
            )
```

### Option B: Lazy Initialization (On-Demand)

```python
def _get_risk_managers(self):
    """Lazy initialization of risk managers."""
    if not hasattr(self, '_risk_managers_initialized'):
        risk_config = RiskConfig(risk_level=RiskLevel.MODERATE)
        self.correlation_rm = CorrelationRiskManager(
            portfolio=self.portfolio,
            risk_config=risk_config,
            logger=self.logger
        )
        self.sector_rm = SectorRiskManager(
            portfolio=self.portfolio,
            risk_config=risk_config,
            logger=self.logger
        )
        self._risk_managers_initialized = True
    return self.correlation_rm, self.sector_rm
```

---

## Complete Integration Example

```python
# In ParallelOrchestrator.py

def __init__(self, ..., use_risk_managers=False):
    # ... existing init ...
    self.use_risk_managers = use_risk_managers
    
    if self.use_risk_managers:
        from plugins.risk_management import (
            CorrelationRiskManager,
            SectorRiskManager,
            RiskConfig,
            RiskLevel
        )
        risk_config = RiskConfig(risk_level=RiskLevel.MODERATE)
        self.correlation_rm = CorrelationRiskManager(
            portfolio=self.portfolio,
            risk_config=risk_config,
            logger=self.logger
        )
        self.sector_rm = SectorRiskManager(
            portfolio=self.portfolio,
            risk_config=risk_config,
            logger=self.logger
        )

def run_backtest(self, symbols):
    # ... existing code ...
    
    # After converting to portfolio_decisions
    portfolio_decisions = self._convert_to_portfolio_decisions(stock_decisions)
    
    # Apply risk managers if enabled
    if self.use_risk_managers:
        portfolio_decisions = self.correlation_rm.evaluate(
            portfolio_decisions, 
            portfolio_state
        )
        portfolio_decisions = self.sector_rm.evaluate(
            portfolio_decisions, 
            portfolio_state
        )
    
    # Then waterfall allocation
    allocated_decisions = allocate_decisions(...)
```

---

## Summary

✅ **Yes, risk managers are initialized independently**
- Each is a separate class instance
- You can initialize one, both, or neither
- They're optional plugins (not currently integrated)

✅ **Initialization is simple**:
```python
rm = RiskManager(portfolio, risk_config, logger)
```

✅ **Usage is straightforward**:
```python
decisions = rm.evaluate(decisions, portfolio_state)
```

✅ **Can be chained**:
```python
decisions = correlation_rm.evaluate(decisions, state)
decisions = sector_rm.evaluate(decisions, state)
```

**They're currently NOT integrated into your orchestrator** - you'd need to add them if you want to use them.

