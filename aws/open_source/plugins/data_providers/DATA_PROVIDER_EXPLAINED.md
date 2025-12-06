# Data Provider Plugins Explained

## Architecture: Data Provider vs Strategy

### Key Distinction:
- **Data Provider** = Gets and processes raw data (may use LLM for sentiment)
- **Strategy** = Uses processed data to make trading decisions

---

## Data Flow

```
Raw Sources (News, Social Media, Financial Data)
         ↓
Data Provider Plugin (processes data, may use LLM)
         ↓
Processed Data (sentiment_score, technical indicators, etc.)
         ↓
Strategy Plugin (uses processed data to make decisions)
```

---

## Example: Sentiment Analysis

### Data Provider Does the LLM Work:

```python
# plugins/data_providers/sentiment_data_provider.py
class SentimentDataProvider:
    def __init__(self, openrouter_api_key):
        self.api_key = openrouter_api_key
    
    def get_sentiment(self, symbol, current_date):
        # 1. Get raw news articles
        news_articles = self._fetch_news(symbol, current_date)
        
        # 2. Use LLM to analyze sentiment (THIS is where LLM is used)
        sentiment_score = self._analyze_with_llm(news_articles)
        
        # 3. Return processed score (not raw articles)
        return {
            'sentiment_score': 0.75,  # Processed score
            'sentiment_label': 'positive',
            'key_themes': ['earnings beat', 'product launch']
        }
```

### Strategy Just Uses the Score:

```python
# plugins/strategies/multi_factor_strategy.py
class MultiFactorStrategy:
    def analyze(self, symbol, data, portfolio_state, current_date):
        # Data provider already did the LLM analysis
        # Strategy just uses the processed score
        sentiment_score = data.get('sentiment_score', 0.5)  # Already calculated!
        
        # No LLM call here - just use the score
        technical_score = self._technical_score(data)
        fundamental_score = self._fundamental_score(data)
        
        total = technical_score * 0.4 + fundamental_score * 0.4 + sentiment_score * 0.2
        # ... make decision
```

---

## Where LLM is Used

### Option 1: In Data Provider (Recommended)
```
News Articles → Data Provider (uses LLM) → sentiment_score → Strategy (no LLM)
```

**Benefits:**
- Strategy stays fast (no API calls)
- Sentiment can be cached/reused
- Multiple strategies can use same sentiment data

### Option 2: In Strategy (LLMStrategy)
```
Raw Data → Strategy (uses LLM) → Decision
```

**When to use:**
- Need LLM to reason about the entire decision
- Want AI to synthesize all signals
- Complex, context-dependent decisions

---

## Data Provider Examples

### 1. Sentiment Data Provider (Uses LLM)

```python
# plugins/data_providers/sentiment_provider.py
class SentimentDataProvider:
    def get_data(self, symbol, current_date):
        # Fetch news
        news = self._fetch_news(symbol)
        
        # Use LLM to analyze (THIS is where LLM is used)
        prompt = f"Analyze sentiment of these news articles about {symbol}: {news}"
        sentiment = self._call_llm(prompt)
        
        return {
            'sentiment_score': sentiment,  # Processed result
            'news_count': len(news)
        }
```

### 2. Technical Data Provider (No LLM)

```python
# plugins/data_providers/technical_provider.py
class TechnicalDataProvider:
    def get_data(self, symbol, current_date):
        # Calculate indicators (no LLM needed)
        prices = self._get_prices(symbol)
        rsi = self._calculate_rsi(prices)
        macd = self._calculate_macd(prices)
        
        return {
            'rsi': rsi,
            'macd': macd,
            'current_price': prices[-1]
        }
```

### 3. Fundamental Data Provider (No LLM)

```python
# plugins/data_providers/fundamental_provider.py
class FundamentalDataProvider:
    def get_data(self, symbol, current_date):
        # Fetch financial data (no LLM needed)
        financials = self._fetch_financials(symbol)
        
        return {
            'pe_ratio': financials['pe'],
            'revenue_growth': financials['revenue_growth'],
            'market_cap': financials['market_cap']
        }
```

---

## Complete Flow Example

```python
# 1. Data Providers process data (one uses LLM for sentiment)
sentiment_provider = SentimentDataProvider(openrouter_api_key)
technical_provider = TechnicalDataProvider()
fundamental_provider = FundamentalDataProvider()

# 2. Get processed data
sentiment_data = sentiment_provider.get_data('NVDA', '2025-01-15')  
# → Uses LLM internally, returns sentiment_score: 0.75

technical_data = technical_provider.get_data('NVDA', '2025-01-15')
# → No LLM, returns rsi: 45, macd: 1.5

fundamental_data = fundamental_provider.get_data('NVDA', '2025-01-15')
# → No LLM, returns pe_ratio: 25, revenue_growth: 0.15

# 3. Combine data
combined_data = {
    **sentiment_data,    # sentiment_score: 0.75 (already processed by LLM)
    **technical_data,    # rsi, macd, etc.
    **fundamental_data   # pe_ratio, etc.
}

# 4. Strategy uses processed data (no LLM call)
strategy = MultiFactorStrategy()
decision = strategy.analyze('NVDA', combined_data, portfolio_state, '2025-01-15')
# → Uses sentiment_score: 0.75 (doesn't know LLM was used)
```

---

## Key Points

1. **Data Provider** = Does the LLM work (if needed for sentiment)
2. **Strategy** = Uses processed data (sentiment_score is just a number)
3. **MultiFactorStrategy** = No LLM calls (uses pre-calculated scores)
4. **LLMStrategy** = Makes LLM calls (for decision-making, not data processing)

---

## Architecture Benefits

- **Separation of concerns**: Data processing vs decision making
- **Reusability**: Multiple strategies can use same sentiment data
- **Performance**: Sentiment can be cached, strategies stay fast
- **Flexibility**: Can swap data providers without changing strategies

So MultiFactorStrategy gets sentiment_score from the data provider (which may have used LLM), but the strategy itself doesn't call LLM.

