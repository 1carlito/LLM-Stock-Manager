# Risk Managers Explained

## Overview

The risk management folder contains **2 specialized risk managers** that adjust trading decisions based on different risk factors. All inherit from `BaseRiskManager` and can be used independently or together.

---

## 1. **CorrelationRiskManager**

### Purpose
**Prevents over-concentration in highly correlated stocks** to avoid portfolio-wide risk.

### How It Works
- **Measures**: Correlation between new position and existing positions
- **Action**: Reduces position size if portfolio already has correlated positions
- **Formula**:
  ```
  correlated_count = count of existing positions with correlation >= 0.70
  reduction_factor = min(correlated_count × 0.15, 0.50)
  size_multiplier = 1.0 - reduction_factor
  adjusted_amount = original_amount * size_multiplier
  ```

### Example
- **New trade**: AAPL (Technology)
- **Existing positions**: NVDA, MSFT, GOOGL (all Technology, correlated)
- **Correlated count**: 3
- **Reduction**: 3 × 15% = 45% reduction
- **Original allocation**: $30k
- **After adjustment**: $30k × 0.55 = **$16.5k**

### Configuration
- `correlation_threshold`: 0.70 (70% correlation - default)
- `max_correlated_pct`: 0.40 (max 40% in correlated stocks)

### When to Use
✅ **Use when**: Building diversified portfolios
✅ **Protects against**: Sector-wide crashes (e.g., all tech stocks drop together)
❌ **Not needed for**: Single-stock strategies or uncorrelated assets

---

## 2. **SectorRiskManager**

### Purpose
**Limits sector concentration** to prevent over-exposure to a single sector.

### How It Works
- **Measures**: Current portfolio allocation per sector
- **Action**: Blocks or reduces trades if sector allocation exceeds limit
- **Formula**:
  ```
  current_sector_pct = (sector_value / total_portfolio_value)
  
  If current_sector_pct >= max_sector_pct (30%):
    If adding would exceed limit:
      max_additional = (max_sector_pct - current_sector_pct) × total_value
      adjusted_amount = min(original_amount, max_additional)
    Else:
      Block trade (amount_usd = 0)
  ```

### Example
- **Current portfolio**: 35% Technology (exceeds 30% limit)
- **New trade**: AAPL (Technology) - $30k
- **Result**: **Blocked** (sector already over limit)

**OR**

- **Current portfolio**: 28% Technology
- **New trade**: AAPL (Technology) - $30k
- **Max additional**: (30% - 28%) × $100k = $2k
- **After adjustment**: min($30k, $2k) = **$2k**

### Configuration
- `max_sector_pct`: 0.30 (max 30% in any sector - default)

### When to Use
✅ **Use when**: Building diversified portfolios across sectors
✅ **Protects against**: Sector-specific crashes (e.g., tech bubble burst)
❌ **Not needed for**: Sector-focused strategies (e.g., tech-only portfolio)

---

## Comparison Table

| Risk Manager | What It Measures | What It Does | When to Use |
|-------------|------------------|--------------|-------------|
| **CorrelationRiskManager** | Correlation between stocks | Reduces position size if correlated positions exist | Building diversified portfolios |
| **SectorRiskManager** | Sector allocation % | Blocks/reduces trades if sector over limit | Sector diversification |

---

## How They Work Together

### Example: Both Risk Managers Applied

**Trade**: Buy $30k of NVDA (tech stock)

1. **CorrelationRiskManager**:
   - Existing: AAPL, MSFT (correlated tech stocks)
   - Reduction: 30% (2 correlated × 15%)
   - After: $30k × 0.70 = **$21k**

2. **SectorRiskManager**:
   - Current tech allocation: 28%
   - Max additional: (30% - 28%) × $100k = $2k
   - After: min($21k, $2k) = **$2k**

**Final allocation**: $2k (down from $30k)

---

## BaseRiskManager

All risk managers inherit from `BaseRiskManager`, which provides:

- **`evaluate()`**: Main method - evaluates and adjusts decisions
- **`should_block_trade()`**: Check if trade should be blocked
- **`adjust_position_size()`**: Adjust position size

### Interface

```python
class BaseRiskManager(ABC):
    def evaluate(self, decisions: List[Dict], 
                 portfolio_state: Dict) -> List[Dict]:
        """Evaluate and adjust trading decisions."""
        pass
```

---

## RiskConfig

`RiskConfig` provides **risk level presets**:

### Conservative
- 15% per trade
- 15% max per stock
- Max 15 positions
- 15% max drawdown

### Moderate (Default)
- 25% per trade
- 25% max per stock
- Max 20 positions
- 25% max drawdown

### Aggressive
- 35% per trade
- 35% max per stock
- Max 25 positions
- 35% max drawdown

---

## Usage Example

```python
from plugins.risk_management import (
    CorrelationRiskManager,
    SectorRiskManager,
    RiskConfig
)

# Initialize risk managers
risk_config = RiskConfig(risk_level=RiskLevel.MODERATE)
correlation_rm = CorrelationRiskManager(portfolio, risk_config)
sector_rm = SectorRiskManager(portfolio, risk_config)

# Apply risk managers (in sequence)
decisions = correlation_rm.evaluate(decisions, portfolio_state)
decisions = sector_rm.evaluate(decisions, portfolio_state)

# Now pass to waterfall allocator
allocated = waterfall_allocator.allocate(decisions, portfolio_state)
```

---

## Key Differences Summary

1. **CorrelationRiskManager**: **Portfolio-level** risk (correlation between stocks)
2. **SectorRiskManager**: **Sector-level** risk (sector concentration)

**Both work together** to create a comprehensive risk management system that protects at portfolio and sector levels.

