# Strategy Types Explained

## Clarification: Base vs Implementations

### **BaseStrategy** = Abstract Interface (Template)
- **NOT a strategy itself** - it's the blueprint
- Defines what all strategies must have: `analyze()` method
- Cannot be used directly - you must inherit from it

### **LLMStrategy** = One Implementation
- Uses LLM (via OpenRouter) to make decisions
- Asks AI: "Should I buy this stock?"
- AI analyzes and responds with decision

### **MultiFactorStrategy** = Different Implementation
- Uses RULES and SCORES (not LLM)
- Calculates technical score + fundamental score + sentiment score
- Combines them with weights
- Applies rules: "If total score > 0.7, then BUY"

---

## They Are NOT The Same

### LLMStrategy (AI-Based)
```python
# Uses LLM to analyze
prompt = "Analyze NVDA: RSI=45, P/E=25, sentiment=positive. Should I buy?"
response = llm.call(prompt)  # "Yes, buy - strong fundamentals"
decision = parse(response)   # BUY
```

**How it works:**
- Sends data to LLM
- LLM thinks and responds
- Parses LLM response

**Requires:** LLM API (OpenRouter)

---

### MultiFactorStrategy (Rule-Based)
```python
# Calculates scores
technical_score = calculate_rsi_score() + calculate_macd_score()  # = 0.6
fundamental_score = calculate_pe_score() + calculate_growth_score()  # = 0.8
sentiment_score = get_sentiment()  # = 0.7

# Combines with weights
total = 0.6*0.4 + 0.8*0.4 + 0.7*0.2  # = 0.70

# Applies rule
if total > 0.7:
    decision = "BUY"
```

**How it works:**
- Calculates scores from data
- Combines scores with weights
- Applies if/then rules

**Requires:** No LLM - just math and rules

---

## Key Differences

| Feature | LLMStrategy | MultiFactorStrategy |
|---------|-------------|---------------------|
| **Method** | AI reasoning | Rule-based scoring |
| **Requires LLM** | ✅ Yes (OpenRouter) | ❌ No |
| **Flexibility** | High (AI adapts) | Medium (fixed rules) |
| **Cost** | API costs | Free |
| **Speed** | Slower (API calls) | Faster (local calculation) |
| **Interpretability** | Lower (AI black box) | Higher (clear rules) |

---

## When to Use Each

### Use LLMStrategy when:
- You want AI to reason about complex situations
- You need flexible analysis that adapts
- You have access to LLM API
- You're okay with API costs

### Use MultiFactorStrategy when:
- You want fast, deterministic decisions
- You have clear rules/signals
- You don't want LLM costs
- You want interpretable logic

---

## Can They Be Combined?

Yes! You could create a hybrid:

```python
class HybridStrategy(BaseStrategy):
    def analyze(self, symbol, data, portfolio_state, current_date):
        # First: Calculate multi-factor score
        multi_factor = MultiFactorStrategy()
        mf_score = multi_factor._calculate_score(data)
        
        # Then: Use LLM only if score is ambiguous
        if 0.4 < mf_score < 0.6:  # Ambiguous
            llm = LLMStrategy(api_key)
            decision = llm.analyze(symbol, data, portfolio_state, current_date)
        else:
            # Clear signal from multi-factor
            decision = multi_factor.analyze(symbol, data, portfolio_state, current_date)
        
        return decision
```

---

## Summary

- **BaseStrategy** = Interface (defines what strategies must have)
- **LLMStrategy** = Uses LLM/AI to make decisions
- **MultiFactorStrategy** = Uses rules/scores to make decisions
- **They're different approaches** - not the same thing
- **Users choose** which one to use (or write their own)

