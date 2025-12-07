# Strategies: Optional Plugins Explained

## Overview

**Yes, strategies are optional plugins.** They're not currently integrated into your orchestrator.

---

## Current Status

⚠️ **Strategies are NOT currently used in `ParallelOrchestrator.py` (engine.py)**

Your orchestrator currently uses **`ReasoningAgent` directly**, not via a strategy plugin.

---

## What is BaseStrategy?

**`BaseStrategy` is NOT a default strategy** - it's an **abstract interface** (template).

- ❌ **Cannot be used directly** - it's just a blueprint
- ✅ **Defines the interface** - all strategies must implement `analyze()`
- ✅ **Abstract class** - you must inherit from it to create a real strategy

```python
# BaseStrategy is abstract - can't instantiate it
strategy = BaseStrategy()  # ❌ ERROR: Can't instantiate abstract class

# You must use a concrete implementation
strategy = LLMStrategy(api_key="...")  # ✅ Works
```

---

## Available Strategy Implementations

### 1. **LLMStrategy** (LLM-Based)
- Uses LLM (via OpenRouter) to analyze and make decisions
- Similar to your ReasoningAgent
- Requires: LLM API key

### 2. **MultiFactorStrategy** (Rule-Based)
- Combines technical + fundamental + sentiment scores
- Uses weighted scoring and rules
- Requires: No LLM (just math)

---

## How Strategies Work

### Strategy Interface

All strategies must implement:

```python
class BaseStrategy(ABC):
    @abstractmethod
    def analyze(self, symbol: str, data: Dict[str, Any], 
                portfolio_state: Dict[str, Any], 
                current_date: str) -> Dict[str, Any]:
        """
        Returns:
            {
                'symbol': symbol,
                'decision': 'BUY' | 'SELL' | 'SHORT' | 'HOLD' | 'NEUTRAL',
                'confidence': 0.0 to 1.0,
                'reasoning': 'explanation',
                'current_price': price
            }
        """
        pass
```

---

## Current Architecture vs Strategy Plugins

### **Current (Your System)**
```
ReasoningAgent (direct)
  ↓
  stock_decisions
  ↓
Orchestrator._convert_to_portfolio_decisions()
  ↓
Waterfall Allocator
```

### **With Strategy Plugin (Alternative)**
```
Strategy Plugin (LLMStrategy or MultiFactorStrategy)
  ↓
  stock_decisions
  ↓
Orchestrator._convert_to_portfolio_decisions()
  ↓
Waterfall Allocator
```

**Your ReasoningAgent = Strategy Plugin** (they do the same thing)

---

## What is the Default Strategy?

**Your default strategy is: ReasoningAgent + Waterfall Allocator**

### **ReasoningAgent** (Decision Logic)
- **LLM-based decision making** using DeepSeek via Chutes API
- **Prompt-based analysis** that integrates:
  - Sentiment analysis
  - Valuation analysis  
  - Fundamental analysis
  - Previous trading decisions
- **Outputs**: BUY/SELL/NEUTRAL/MAINTAIN with confidence scores
- **Decision criteria**: Based on the prompt in `_build_decision_prompt()`

### **Waterfall Allocator** (Allocation Constraints)
- **Sequential cash-constrained allocation**
- **Priority ordering**: CLOSE/SELL/COVER → SHORT → BUY
- **Per-trade caps**: 25% of remaining cash per trade (configurable)
- **Tie-breaking**: Confidence → Sector+Industry Priority → Alphabetical
- **Cash management**: Updates cash after each trade to prevent overspending

### **Together = Your Default Strategy**

```
ReasoningAgent (prompt logic)
  ↓
  Makes BUY/SELL/NEUTRAL/MAINTAIN decisions
  ↓
Waterfall Allocator (constraints)
  ↓
  Applies cash limits, sector priorities, tie-breaking
  ↓
  Final allocated trades
```

**This IS your default strategy** - it's just not implemented as a strategy plugin yet.

---

## How to Use Strategies (If You Want)

### Option 1: Replace ReasoningAgent with LLMStrategy

```python
from plugins.strategies import LLMStrategy

# In ParallelOrchestrator.__init__()
self.strategy = LLMStrategy(
    openrouter_api_key=api_key,
    model_name="deepseek/deepseek-chat"
)

# In _analyze_single_stock()
data = {
    'current_price': price,
    'rsi': rsi_value,
    'pe_ratio': pe_value,
    'sentiment_score': sentiment_value,
    # ... other data
}

decision = self.strategy.analyze(
    symbol=symbol,
    data=data,
    portfolio_state=portfolio_state,
    current_date=current_date
)
```

### Option 2: Use MultiFactorStrategy (No LLM)

```python
from plugins.strategies import MultiFactorStrategy

# In ParallelOrchestrator.__init__()
self.strategy = MultiFactorStrategy(
    technical_weight=0.4,
    fundamental_weight=0.4,
    sentiment_weight=0.2
)

# Same usage as above
decision = self.strategy.analyze(symbol, data, portfolio_state, current_date)
```

### Option 3: Keep Using ReasoningAgent (Current)

```python
# What you're doing now - no strategy plugin needed
reasoning_agent = ReasoningAgent(data_dir=self.data_dir, api_key_override=api_key)
decision = reasoning_agent.make_decision(symbol, current_date, ...)
```

---

## Key Points

1. **Strategies are optional** - you can use them or not
2. **BaseStrategy is NOT a default** - it's just the interface
3. **No default strategy** - you choose which one to use (or use ReasoningAgent directly)
4. **Your ReasoningAgent = Strategy** - it does the same job as a strategy plugin
5. **Currently not integrated** - your orchestrator uses ReasoningAgent directly

---

## Should You Use Strategy Plugins?

### **Keep ReasoningAgent (Current Approach)**
✅ **Pros:**
- Already working
- No refactoring needed
- Direct control

❌ **Cons:**
- Not pluggable
- Harder to swap strategies

### **Switch to Strategy Plugin**
✅ **Pros:**
- Pluggable (easy to swap strategies)
- Standardized interface
- Can use MultiFactorStrategy (no LLM costs)

❌ **Cons:**
- Requires refactoring
- ReasoningAgent would need to be wrapped as LLMStrategy

---

## Recommendation

**Keep using ReasoningAgent directly** for now. It's working and does the same job as a strategy plugin.

**Strategy plugins are useful if:**
- You want to easily swap between LLM and rule-based strategies
- You want to test different decision-making approaches
- You want to open-source a strategy interface

**But they're not required** - your current architecture works fine.

---

## Summary

- ✅ **Your default strategy = ReasoningAgent + Waterfall Allocator**
  - **ReasoningAgent**: LLM-based decision making (prompt logic)
  - **Waterfall Allocator**: Cash constraints, sector priorities, tie-breaking
- ✅ **Strategies are optional plugins** - you can use them or not
- ❌ **BaseStrategy is NOT a default** - it's just the interface
- ✅ **Currently: ReasoningAgent used directly** (not via strategy plugin)
- ✅ **Strategy plugins** (LLMStrategy, MultiFactorStrategy) are alternatives, not defaults

