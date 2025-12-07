# Combined Sector + Industry (Subsector) Scoring

## Overview

The waterfall allocator now uses **combined scoring** that adds sector priority + industry (subsector) priority for more granular tie-breaking.

---

## How It Works

### Scoring Formula

```
combined_priority = sector_score + industry_score
```

**Example:**
- **NVDA**: Technology (3.0) + Semiconductors (2.5) = **5.5**
- **AAPL**: Technology (3.0) + Consumer Electronics (2.0) = **5.0**
- **MSFT**: Technology (3.0) + Software (1.5) = **4.5**

If all three have the same confidence (0.99), execution order:
1. **NVDA** (5.5 combined priority)
2. **AAPL** (5.0 combined priority)
3. **MSFT** (4.5 combined priority)

---

## Sort Order

Trades are sorted by:
1. **Primary**: `confidence` (higher first)
2. **Secondary**: `combined_priority` = `sector_score + industry_score` (higher first)
3. **Tertiary**: `symbol` (alphabetical A-Z)

---

## Default Scores

### Sector Scores (Main Categories)

```python
DEFAULT_SECTOR_PRIORITY = {
    "Technology": 3.0,
    "Healthcare": 3.0,
    "Financial Services": 2.0,
    "Consumer Defensive": 2.0,
    "Consumer Cyclical": 2.0,
    "Industrials": 2.0,
    "Energy": 1.0,
    "Materials": 1.0,
    "Real Estate": 1.0,
    "Utilities": 1.0,
    "Communication Services": 1.0,
    "Unknown": 0.0,
}
```

### Industry Scores (Subsectors) - Added to Sector

```python
DEFAULT_INDUSTRY_PRIORITY = {
    # Technology subsectors
    "Consumer Electronics": 2.0,
    "Software": 1.5,
    "Semiconductors": 2.5,
    "Internet Content & Information": 1.0,
    "Computer Hardware": 1.0,
    "Telecom Services": 0.5,
    
    # Healthcare subsectors
    "Biotechnology": 2.5,
    "Pharmaceuticals": 2.0,
    "Medical Devices": 1.5,
    "Healthcare Plans": 1.0,
    
    # Financial Services subsectors
    "Banks - Diversified": 1.5,
    "Capital Markets": 1.0,
    "Insurance": 0.5,
    "Credit Services": 0.5,
    
    # Consumer subsectors
    "Auto Manufacturers": 1.5,
    "Retail - Cyclical": 1.0,
    "Packaged Foods": 0.5,
    
    "Unknown": 0.0,
}
```

---

## Example Scenarios

### Scenario 1: Same Sector, Different Industries

**Stocks:**
- **NVDA**: Technology (3.0) + Semiconductors (2.5) = **5.5**
- **AAPL**: Technology (3.0) + Consumer Electronics (2.0) = **5.0**
- **MSFT**: Technology (3.0) + Software (1.5) = **4.5**

**All have 0.99 confidence:**
1. NVDA executes first (5.5)
2. AAPL executes second (5.0)
3. MSFT executes third (4.5)

### Scenario 2: Different Sectors, Same Industry Score

**Stocks:**
- **JPM**: Financial Services (2.0) + Banks - Diversified (1.5) = **3.5**
- **BAC**: Financial Services (2.0) + Banks - Diversified (1.5) = **3.5**

**Both have 0.99 confidence, same combined priority:**
- **BAC** executes first (alphabetical: B before J)
- **JPM** executes second

### Scenario 3: Complete Tie

**Stocks:**
- **AAPL**: Technology (3.0) + Consumer Electronics (2.0) = **5.0**, confidence = 0.99
- **GOOGL**: Technology (3.0) + Internet Content (1.0) = **4.0**, confidence = 0.99

**Different combined priority:**
- **AAPL** executes first (5.0 > 4.0)

---

## Benefits

✅ **More Granular**: Differentiates within the same sector
✅ **Flexible**: Can prioritize specific industries (e.g., Semiconductors > Software)
✅ **Deterministic**: Always produces consistent ordering
✅ **Configurable**: Can override via `portfolio_state['sector_priority']` and `portfolio_state['industry_priority']`

---

## Configuration Override

You can override default scores via `portfolio_state`:

```python
portfolio_state = {
    ...
    'sector_priority': {
        "Technology": 4.0,  # Override default 3.0
        "Healthcare": 3.5,
    },
    'industry_priority': {
        "Semiconductors": 3.0,  # Override default 2.5
        "Software": 2.0,
    }
}
```

---

## Data Flow

1. **FundamentalAgent** → Provides `Sector` and `Industry` in fundamental_data
2. **ReasoningAgent** → Extracts sector/industry from fundamental_data, adds to decision
3. **Orchestrator** → Passes decisions with sector/industry to waterfall
4. **Waterfall Allocator** → Calculates `combined_priority = sector_score + industry_score`
5. **Sorting** → Uses `(confidence, combined_priority, symbol)` for deterministic ordering

---

## Why Combined vs Separate?

**Combined (Current Approach):**
- ✅ Simpler: One number to compare
- ✅ Additive: Sector importance + Industry importance
- ✅ Flexible: Can weight sectors vs industries differently

**Alternative (Separate):**
- Could use `(confidence, sector_score, industry_score, symbol)`
- More complex sorting logic
- Harder to reason about priorities

**Recommendation**: Combined approach is cleaner and easier to configure.

