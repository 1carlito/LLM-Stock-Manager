# Reasoning Agent: Confidence Ranking & Sector Information

## Summary

✅ **Yes, ReasoningAgent ranks decisions by confidence score**
✅ **Yes, OpenBB can get sector information for tickers**

---

## 1. Confidence-Based Ranking

### How It Works

The `ReasoningAgent` returns decisions with a `confidence` field (normalized 0-1):

```python
# From ReasoningAgent._parse_response()
result = {
    'symbol': symbol,
    'date': current_date,
    'decision': decision,  # BUY/SELL/NEUTRAL/MAINTAIN
    'confidence': confidence_normalized,  # 0.0 to 1.0
    'reasoning': reasoning,
    'model_used': MODEL_NAME
}
```

### Ranking Implementation

The `PortfolioManagerAgent` sorts decisions by confidence:

```python
# From PortfolioManagerAgent._waterfall_allocation() (lines 835-837)
# Build confidence map from stock_decisions
confidence_map = {d.get('symbol'): d.get('confidence', 0.5) for d in stock_decisions}
short_confidence_map = {d.get('symbol'): d.get('short_confidence', d.get('confidence', 0.5)) for d in stock_decisions}

# Sort BUY and SHORT by confidence (higher first)
buy_decisions.sort(key=lambda x: confidence_map.get(x.get('symbol'), 0.5), reverse=True)
short_decisions.sort(key=lambda x: short_confidence_map.get(x.get('symbol'), 0.5), reverse=True)
```

**Key Points:**
- BUY decisions are sorted by `confidence` (highest first)
- SHORT decisions are sorted by `short_confidence` (or `confidence` if `short_confidence` not available)
- Higher confidence = higher priority in allocation

---

## 2. Sector Information from OpenBB

### ✅ Already Implemented

OpenBB can get sector information via the `get_company_overview()` method:

```python
# From openbb_provider.py (lines 143-189)
def get_company_overview(self, symbol: str) -> Dict[str, Any]:
    """
    Get company overview and fundamental data.
    
    Returns:
        Dictionary with company fundamentals including:
        - Sector
        - Industry
        - Company Name
        - Description
        - Market Cap
        - P/E, P/B ratios
        - Beta
    """
    profile = obb.equity.profile(symbol, provider=self.provider)
    
    if not profile.empty:
        row = profile.iloc[0] if len(profile) > 0 else profile
        overview = {
            'Symbol': symbol,
            'Name': row.get('name', ''),
            'Sector': row.get('sector', ''),      # ✅ Sector available
            'Industry': row.get('industry', ''),  # ✅ Industry available
            'Description': row.get('description', ''),
            'MarketCapitalization': row.get('market_cap', None),
            # ... other fields
        }
    
    return overview
```

### Usage Example

```python
from aws.open_source.plugins.data_providers import OpenBBProvider

# Initialize provider
provider = OpenBBProvider()

# Get company overview (includes sector)
overview = provider.get_company_overview("AAPL")

# Access sector
sector = overview.get('Sector', '')  # e.g., "Technology"
industry = overview.get('Industry', '')  # e.g., "Consumer Electronics"
```

### Via Main `get_data()` Method

```python
# Get all data including sector
data = provider.get_data("AAPL", include_fundamentals=True)

# Access sector from company_overview
sector = data['company_overview'].get('Sector', '')
industry = data['company_overview'].get('Industry', '')
```

---

## 3. Adding Sector to Reasoning Agent

### Option 1: Include in Decision Prompt

Add sector information to the reasoning prompt to help the agent make sector-aware decisions:

```python
def _build_decision_prompt(self, symbol, current_date, valuation_data, fundamental_data, sentiment_data, previous_decisions=None, sector=None, industry=None):
    """Build a prompt that integrates sentiment and valuation analyses for decision making"""
    
    prompt = f"""
You are the highest level market trader in existence, you constantly make extremely good returns. Analyze {symbol} on {date_str} and make a trading decision based on the analysis data provided below.

COMPANY INFORMATION:
- Symbol: {symbol}
- Sector: {sector or 'Unknown'}
- Industry: {industry or 'Unknown'}

SENTIMENT ANALYSIS:
{json.dumps(sentiment_data, indent=2) if sentiment_data else "No sentiment data available"}

VALUATION ANALYSIS:
{json.dumps(valuation_data, indent=2) if valuation_data else "No valuation data available"}
...
"""
```

### Option 2: Include in Decision Result

Add sector to the decision result for downstream analysis:

```python
def _parse_response(self, response_text, symbol, current_date, sector=None, industry=None):
    """Parse the LLM response to extract decision, confidence, and reasoning."""
    result = {
        'symbol': symbol,
        'date': current_date,
        'decision': decision,
        'confidence': confidence_normalized,
        'reasoning': reasoning,
        'model_used': MODEL_NAME,
        'sector': sector,      # ✅ Add sector
        'industry': industry,  # ✅ Add industry
        'raw_response': response_text
    }
    return result
```

### Option 3: Sector-Based Grouping

Group decisions by sector for portfolio diversification:

```python
def group_decisions_by_sector(decisions: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Group decisions by sector for portfolio analysis.
    
    Args:
        decisions: List of decision dicts with 'sector' field
    
    Returns:
        Dictionary mapping sector -> list of decisions
    """
    sector_groups = {}
    for decision in decisions:
        sector = decision.get('sector', 'Unknown')
        if sector not in sector_groups:
            sector_groups[sector] = []
        sector_groups[sector].append(decision)
    
    return sector_groups
```

---

## 4. Integration with Reasoning Agent

### Updated `make_decision()` Method

```python
def make_decision(
    self, 
    symbol="NVO", 
    current_date=None, 
    valuation_data=None, 
    fundamental_data=None, 
    sentiment_data=None, 
    previous_decisions=None,
    company_data=None  # ✅ New parameter
):
    """
    Make a trading decision based on the provided analysis data.
    
    Args:
        company_data: Optional dict with 'sector', 'industry', etc.
                     Can be fetched from OpenBB provider
    """
    # Extract sector/industry from company_data or fundamental_data
    sector = None
    industry = None
    
    if company_data:
        sector = company_data.get('Sector') or company_data.get('sector')
        industry = company_data.get('Industry') or company_data.get('industry')
    elif fundamental_data:
        sector = fundamental_data.get('Sector') or fundamental_data.get('sector')
        industry = fundamental_data.get('Industry') or fundamental_data.get('industry')
    
    # Build prompt with sector info
    prompt = self._build_decision_prompt(
        symbol, current_date, valuation_data, fundamental_data, 
        sentiment_data, previous_decisions, sector=sector, industry=industry
    )
    
    # ... rest of method
    
    # Parse response with sector info
    decision_result = self._parse_response(
        response, symbol, current_date, sector=sector, industry=industry
    )
    
    return decision_result
```

---

## 5. Example: Full Integration

```python
from aws.open_source.plugins.data_providers import OpenBBProvider
from aws.open_source.ReasoningAgent import ReasoningAgent

# Initialize providers
data_provider = OpenBBProvider()
reasoning_agent = ReasoningAgent()

# Get company data (including sector)
company_data = data_provider.get_company_overview("AAPL")
sector = company_data.get('Sector', '')
industry = company_data.get('Industry', '')

# Get other analysis data
valuation_data = {...}  # From ValuationAgent
fundamental_data = {...}  # From FundamentalAgent
sentiment_data = {...}  # From SentimentAgent

# Make decision with sector info
decision = reasoning_agent.make_decision(
    symbol="AAPL",
    current_date="2024-01-15",
    valuation_data=valuation_data,
    fundamental_data=fundamental_data,
    sentiment_data=sentiment_data,
    company_data=company_data  # ✅ Includes sector
)

# Decision now includes sector
print(f"Decision: {decision['decision']}")
print(f"Confidence: {decision['confidence']}")
print(f"Sector: {decision.get('sector', 'Unknown')}")
print(f"Industry: {decision.get('industry', 'Unknown')}")
```

---

## 6. Benefits of Sector Information

### Portfolio Diversification
- Track sector exposure across all decisions
- Ensure diversification across sectors
- Avoid over-concentration in one sector

### Sector-Aware Analysis
- Compare stocks within the same sector
- Understand sector-specific risks
- Make relative value decisions

### Risk Management
- Monitor sector-level risk
- Identify sector rotation opportunities
- Adjust allocations based on sector trends

---

## Summary

✅ **Confidence Ranking**: ReasoningAgent returns `confidence` (0-1), PortfolioManager sorts by it
✅ **Sector Information**: OpenBB provides sector via `get_company_overview()` → `'Sector'` field
✅ **Already Implemented**: Sector fetching is already in `openbb_provider.py`
✅ **Ready to Use**: Just need to pass sector data to ReasoningAgent methods

**Next Steps:**
1. Update `ReasoningAgent.make_decision()` to accept `company_data` parameter
2. Extract sector/industry from `company_data` or `fundamental_data`
3. Include sector in decision prompt (optional, for better context)
4. Include sector in decision result (for downstream analysis)
5. Use sector for portfolio diversification analysis

