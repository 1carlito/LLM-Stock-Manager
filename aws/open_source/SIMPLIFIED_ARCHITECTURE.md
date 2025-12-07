# Simplified Architecture: ReasoningAgent → Waterfall (No PortfolioManagerAgent)

## Overview

**PortfolioManagerAgent has been removed.** The architecture is now:

```
ReasoningAgent (per stock)
  ↓
  stock_decisions: [{symbol, decision, confidence, sector, ...}]
  ↓
Orchestrator._convert_to_portfolio_decisions()
  ├─ Action conversion: SELL → SHORT, BUY → COVER+BUY, etc.
  └─ portfolio_decisions: [{symbol, action, confidence, sector, ...}]
  ↓
Waterfall Allocator
  ├─ Sort by (confidence, sector_priority)
  ├─ Calculate: amount_usd = confidence * max_allocation
  └─ Enforce cash constraints (30% max per position, 25% per trade)
  ↓
Exchange (execute trades)
```

---

## Key Changes

### 1. **Removed PortfolioManagerAgent**
- ❌ No more LLM call for portfolio allocation
- ❌ No more portfolio-level reasoning
- ✅ Direct confidence-based allocation

### 2. **Confidence-Based Allocation**

**Formula:**
```
max_allocation = min(
    portfolio_value * max_allocation_pct,  # e.g., 30% of $100k = $30k
    remaining_cash * per_trade_cap_pct     # e.g., 25% of remaining cash
)

amount_usd = max_allocation * confidence
```

**Example:**
- NVDA: 0.99 confidence, $100k portfolio, 30% max allocation
- max_allocation = min($30k, 25% of remaining cash)
- amount_usd = $30k * 0.99 = **$29.7k**

### 3. **Action Conversion in Orchestrator**

`_convert_to_portfolio_decisions()` handles:
- **SELL** on unowned stock → **SHORT**
- **BUY** when short exists → **COVER** + **BUY**
- **NEUTRAL**/**MAINTAIN** → Skip if not owned

### 4. **Sector-Based Tie-Breaking**

Waterfall allocator still uses sector priority for tie-breaking:
- Primary sort: **confidence** (higher first)
- Secondary sort: **sector_priority** (higher first)
- Sector info passed through from ReasoningAgent decisions

---

## Configuration

### Max Allocation Per Position
```python
portfolio_state = {
    ...
    'max_allocation_pct': 0.30  # 30% max per position
}
```

### Per-Trade Cap
```python
allocate_decisions(
    ...
    per_trade_cap_pct=0.25,  # 25% of remaining cash per trade
    ...
)
```

---

## Benefits

✅ **Simpler**: One less LLM call, less complexity
✅ **Faster**: Direct allocation, no portfolio manager delay
✅ **Transparent**: Confidence directly drives allocation
✅ **Deterministic**: No LLM variability in allocation amounts
✅ **Still uses sector priority**: Tie-breaking preserved

---

## Trade-offs

❌ **No portfolio-level reasoning**: Can't consider diversification holistically
❌ **No LLM allocation decisions**: Position sizes based only on confidence
❌ **No sector scoring**: Sector priority uses defaults (not LLM-scored)

---

## Example Flow

1. **ReasoningAgent** analyzes NVDA:
   - Decision: **BUY**
   - Confidence: **0.99**
   - Sector: **Technology**

2. **Orchestrator** converts:
   - Action: **BUY**
   - Confidence: **0.99**
   - Sector: **Technology**

3. **Waterfall Allocator**:
   - Sorts by confidence (0.99 = highest)
   - Calculates: $30k max * 0.99 = **$29.7k**
   - Enforces: min($29.7k, 25% of remaining cash)
   - Allocates: **$29.7k** (or less if cash constrained)

4. **Exchange** executes: Buys $29.7k worth of NVDA

---

## Files Modified

1. **`ParallelOrchestrator.py`**:
   - Removed `PortfolioManagerAgent` import
   - Added `_convert_to_portfolio_decisions()` method
   - Replaced PM call with direct waterfall allocation

2. **`waterfall_allocator.py`**:
   - Updated BUY allocation to use `confidence * max_allocation`
   - Updated SHORT allocation to use `short_confidence * max_allocation`
   - Added `max_allocation_pct` support (default 30%)

---

## Next Steps (Optional)

If you want to add back sector scoring without PortfolioManagerAgent:
1. Create lightweight `SectorScorer` class
2. Takes stock_decisions + portfolio state
3. Makes single LLM call to score sectors
4. Returns `sector_priority` map
5. Pass to waterfall allocator

But for now, the simplified architecture works with default sector priorities.

