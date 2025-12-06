# Strategy Plugin Explained

## What is a Strategy Plugin?

A **strategy plugin** is what replaces your `ReasoningAgent` in the open-source framework. It's the component that makes trading decisions (BUY/SELL/SHORT/HOLD) based on data.

---

## Strategy Plugin Contents

### 1. **Base Interface** (`base_strategy.py`)

```python
class BaseStrategy(ABC):
    @abstractmethod
    def analyze(self, symbol: str, data: Dict[str, Any], 
                portfolio_state: Dict[str, Any], 
                current_date: str) -> Dict[str, Any]:
        """
        Analyze a stock and make a trading decision.
        
        Args:
            symbol: Stock symbol to analyze
            data: Market data (prices, indicators, news, etc.)
            portfolio_state: Current portfolio state (optional, for portfolio-aware strategies)
            current_date: Trading date
        
        Returns:
            Decision dict with:
            - symbol: Stock symbol
            - decision: "BUY", "SELL", "SHORT", "HOLD", or "NEUTRAL"
            - confidence: 0.0 to 1.0 (or 0-100)
            - reasoning: Explanation of the decision
            - current_price: Current stock price
            - amount_usd: Optional suggested allocation (before waterfall)
        """
        pass
```

### 2. **What Data Does It Receive?**

The strategy receives market data from data provider plugins:

```python
data = {
    # Price data
    'current_price': 150.50,
    'historical_prices': [...],  # OHLCV data
    
    # Technical indicators (from data provider)
    'rsi': 45.2,
    'macd': 1.5,
    'moving_averages': {'sma_20': 148.0, 'sma_50': 145.0},
    
    # Fundamental data (optional, from data provider)
    'pe_ratio': 25.3,
    'market_cap': 500_000_000_000,
    'revenue_growth': 0.15,
    
    # Sentiment data (optional, from data provider)
    'sentiment_score': 0.65,
    'news_sentiment': 'positive',
    
    # Additional data
    'volume': 10_000_000,
    'volatility': 0.25,
}
```

### 3. **What Does It Output?**

The strategy returns a decision:

```python
{
    'symbol': 'NVDA',
    'date': '2025-01-15',
    'decision': 'BUY',           # BUY, SELL, SHORT, HOLD, NEUTRAL
    'confidence': 0.85,          # 0.0 to 1.0 (or 0-100)
    'reasoning': 'Strong fundamentals, positive sentiment, RSI oversold',
    'current_price': 150.50,
    'amount_usd': 10000,          # Optional: suggested allocation (before waterfall)
    'short_confidence': None     # Optional: for SELL decisions, confidence in shorting
}
```

---

## Types of Strategy Plugins

### 1. **LLM-Based Strategy** (Your ReasoningAgent)

```python
# plugins/strategies/llm_strategy.py
class LLMStrategy(BaseStrategy):
    def __init__(self, api_key, model_name="deepseek-ai/DeepSeek-V3.1"):
        self.api_key = api_key
        self.model = model_name
    
    def analyze(self, symbol, data, portfolio_state, current_date):
        # Build prompt with data
        prompt = self._build_prompt(symbol, data)
        
        # Call LLM
        response = self._call_llm(prompt)
        
        # Parse response
        decision = self._parse_llm_response(response)
        
        return decision
```

**Inputs:**
- Valuation data
- Fundamental data
- Sentiment data
- Previous decisions

**Outputs:**
- BUY/SELL/SHORT/HOLD decision
- Confidence score
- Reasoning

---

### 2. **Technical Analysis Strategy**

```python
# plugins/strategies/technical_strategy.py
class TechnicalStrategy(BaseStrategy):
    def analyze(self, symbol, data, portfolio_state, current_date):
        rsi = data.get('rsi', 50)
        macd = data.get('macd', 0)
        price = data.get('current_price', 0)
        sma_20 = data.get('moving_averages', {}).get('sma_20', price)
        
        decision = 'HOLD'
        confidence = 0.5
        
        # RSI oversold + MACD bullish = BUY
        if rsi < 30 and macd > 0:
            decision = 'BUY'
            confidence = 0.75
            reasoning = f"RSI oversold ({rsi:.1f}), MACD bullish"
        
        # RSI overbought + price above SMA = SELL
        elif rsi > 70 and price > sma_20:
            decision = 'SELL'
            confidence = 0.70
            reasoning = f"RSI overbought ({rsi:.1f}), price above SMA"
        
        return {
            'symbol': symbol,
            'decision': decision,
            'confidence': confidence,
            'reasoning': reasoning,
            'current_price': price
        }
```

**Inputs:**
- Price data
- Technical indicators (RSI, MACD, moving averages)
- Volume

**Outputs:**
- BUY/SELL based on technical signals

---

### 3. **Fundamental Strategy**

```python
# plugins/strategies/fundamental_strategy.py
class FundamentalStrategy(BaseStrategy):
    def analyze(self, symbol, data, portfolio_state, current_date):
        pe = data.get('pe_ratio', 0)
        revenue_growth = data.get('revenue_growth', 0)
        market_cap = data.get('market_cap', 0)
        price = data.get('current_price', 0)
        
        decision = 'HOLD'
        confidence = 0.5
        
        # Value investing: Low P/E + high growth = BUY
        if pe < 15 and revenue_growth > 0.20:
            decision = 'BUY'
            confidence = 0.80
            reasoning = f"Undervalued (P/E: {pe:.1f}), strong growth ({revenue_growth*100:.1f}%)"
        
        # Overvalued: High P/E + low growth = SELL
        elif pe > 40 and revenue_growth < 0.05:
            decision = 'SELL'
            confidence = 0.70
            reasoning = f"Overvalued (P/E: {pe:.1f}), weak growth"
        
        return {
            'symbol': symbol,
            'decision': decision,
            'confidence': confidence,
            'reasoning': reasoning,
            'current_price': price
        }
```

**Inputs:**
- Financial metrics (P/E, P/B, revenue growth)
- Market cap
- Earnings data

**Outputs:**
- BUY/SELL based on valuation

---

### 4. **Momentum Strategy**

```python
# plugins/strategies/momentum_strategy.py
class MomentumStrategy(BaseStrategy):
    def analyze(self, symbol, data, portfolio_state, current_date):
        prices = data.get('historical_prices', [])
        current_price = data.get('current_price', 0)
        
        # Calculate momentum (price change over last 20 days)
        if len(prices) >= 20:
            price_20_days_ago = prices[-20]['close']
            momentum = (current_price - price_20_days_ago) / price_20_days_ago
            
            if momentum > 0.10:  # 10% gain
                return {
                    'symbol': symbol,
                    'decision': 'BUY',
                    'confidence': 0.70,
                    'reasoning': f'Strong momentum: {momentum*100:.1f}%',
                    'current_price': current_price
                }
            elif momentum < -0.10:  # 10% loss
                return {
                    'symbol': symbol,
                    'decision': 'SELL',
                    'confidence': 0.65,
                    'reasoning': f'Negative momentum: {momentum*100:.1f}%',
                    'current_price': current_price
                }
        
        return {
            'symbol': symbol,
            'decision': 'HOLD',
            'confidence': 0.5,
            'reasoning': 'No clear momentum',
            'current_price': current_price
        }
```

**Inputs:**
- Historical prices
- Price changes over time

**Outputs:**
- BUY/SELL based on momentum

---

### 5. **Multi-Factor Strategy** (Combines Multiple Signals)

```python
# plugins/strategies/multi_factor_strategy.py
class MultiFactorStrategy(BaseStrategy):
    def analyze(self, symbol, data, portfolio_state, current_date):
        # Get multiple signals
        technical_signal = self._technical_score(data)
        fundamental_signal = self._fundamental_score(data)
        sentiment_signal = data.get('sentiment_score', 0.5)
        
        # Weighted combination
        total_score = (
            technical_signal * 0.4 +
            fundamental_signal * 0.4 +
            sentiment_signal * 0.2
        )
        
        if total_score > 0.7:
            decision = 'BUY'
            confidence = total_score
        elif total_score < 0.3:
            decision = 'SELL'
            confidence = 1.0 - total_score
        else:
            decision = 'HOLD'
            confidence = 0.5
        
        return {
            'symbol': symbol,
            'decision': decision,
            'confidence': confidence,
            'reasoning': f'Multi-factor score: {total_score:.2f}',
            'current_price': data.get('current_price', 0)
        }
```

---

## How Strategy Plugins Work in the Framework

### Flow:

```
1. Data Provider → Gets market data
2. Strategy Plugin → Analyzes data → Makes decision
3. Risk Manager (optional) → Adjusts decision
4. Waterfall Allocator → Allocates capital
5. Executor → Executes trade
```

### Example Usage:

```python
from plugins.strategies import LLMStrategy, TechnicalStrategy

# User selects strategy
strategy = LLMStrategy(api_key="...")

# Engine calls strategy
for symbol in symbols:
    data = data_provider.get_data(symbol, current_date)
    decision = strategy.analyze(symbol, data, portfolio_state, current_date)
    decisions.append(decision)

# Then waterfall allocator processes decisions
allocated = waterfall_allocator.allocate(decisions, portfolio_state)
```

---

## Key Points

1. **Strategy = Decision Maker**: Takes data, returns BUY/SELL/SHORT/HOLD
2. **Portfolio-Agnostic (usually)**: Strategy doesn't know about cash/positions
3. **Data-Driven**: Receives market data from data providers
4. **Flexible**: Can be LLM-based, technical, fundamental, or custom
5. **User-Defined**: Users write their own strategies

---

## Your ReasoningAgent as a Strategy

Your `ReasoningAgent` would become:

```python
# plugins/strategies/reasoning_strategy.py
class ReasoningStrategy(BaseStrategy):
    def __init__(self, api_key, model_name):
        # Your ReasoningAgent initialization
    
    def analyze(self, symbol, data, portfolio_state, current_date):
        # Your ReasoningAgent.make_decision() logic
        # Returns: {symbol, decision, confidence, reasoning, current_price}
```

The strategy plugin is the "brain" that decides what to trade - everything else (allocation, execution) happens after.

