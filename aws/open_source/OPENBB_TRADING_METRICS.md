# OpenBB Coverage: Trading Position Metrics

Analysis of which metrics from your live trading positions can be provided by OpenBB.

---

## Your Trading Data Structure

```python
# Current Prices
{'xyz:TSLA': 455.065, 'xyz:XYZ100': 25663.5, 'xyz:NVDA': 182.26, ...}

# Live Positions
{
    'symbol': 'xyz:XYZ100',
    'quantity': 0.91,
    'entry_price': 25626.49,
    'current_price': 25663.5,
    'liquidation_price': 21032.41,
    'unrealized_pnl': 33.68,
    'leverage': 5,
    'exit_plan': {
        'profit_target': 26601.0,
        'stop_loss': 24281.5,
        'invalidation_condition': '...'
    },
    'confidence': 0.0,
    'risk_usd': 0.0,
    'notional_usd': 23353.78
}
```

---

## OpenBB Coverage Analysis

### ✅ **CAN BE PROVIDED BY OPENBB**

#### 1. **Current Price** ✅
```python
# Your data: 'current_price': 25663.5
# OpenBB can provide:
current_price = obb.equity.price.quote("XYZ100")['price']
# or
current_price = obb.equity.price.historical("XYZ100", limit=1)['close'].iloc[-1]
```

**Status**: ✅ **100% Coverage** - OpenBB provides real-time and historical prices

---

#### 2. **Historical Prices** ✅
```python
# For calculating price changes, volatility, etc.
historical_prices = obb.equity.price.historical("XYZ100", start_date="2024-01-01")
```

**Status**: ✅ **100% Coverage** - OpenBB provides full historical price data

---

### ❌ **CANNOT BE PROVIDED BY OPENBB** (Position/Account-Specific)

#### 1. **Entry Price** ❌
```python
# Your data: 'entry_price': 25626.49
```
**Why Not**: This is your position's entry price, not market data. OpenBB provides market prices, not your trading history.

**Status**: ❌ **Not available** - This is position-specific data

---

#### 2. **Quantity** ❌
```python
# Your data: 'quantity': 0.91
```
**Why Not**: This is your position size, not market data.

**Status**: ❌ **Not available** - This is position-specific data

---

#### 3. **Liquidation Price** ❌
```python
# Your data: 'liquidation_price': 21032.41
```
**Why Not**: This is calculated from:
- Entry price
- Leverage
- Margin requirements
- Position size

OpenBB doesn't know your leverage or margin requirements.

**Status**: ❌ **Not available** - This is calculated from position + account settings

**Can Calculate If You Have:**
- Entry price (from your positions)
- Leverage (from your account)
- Margin requirements (from exchange)

---

#### 4. **Unrealized P&L** ❌
```python
# Your data: 'unrealized_pnl': 33.68
```
**Why Not**: This is calculated from:
- Entry price (your position)
- Current price (OpenBB can provide this)
- Quantity (your position)

OpenBB can provide current_price, but you need entry_price and quantity from your positions.

**Status**: ⚠️ **Partial** - OpenBB provides current_price, but you need entry_price and quantity

**Can Calculate:**
```python
# OpenBB provides current_price
current_price = obb.equity.price.quote(symbol)['price']

# You provide entry_price and quantity from your positions
unrealized_pnl = (current_price - entry_price) * quantity
```

---

#### 5. **Leverage** ❌
```python
# Your data: 'leverage': 5
```
**Why Not**: This is your account/trading setting, not market data.

**Status**: ❌ **Not available** - This is account-specific

---

#### 6. **Exit Plan (Profit Target, Stop Loss)** ❌
```python
# Your data: 
'exit_plan': {
    'profit_target': 26601.0,
    'stop_loss': 24281.5,
    'invalidation_condition': '...'
}
```
**Why Not**: These are your trading strategy decisions, not market data.

**Status**: ❌ **Not available** - These are trading strategy decisions

**However**: OpenBB can provide price data to help you calculate these:
- Support/Resistance levels (for stop loss placement)
- Volatility (for position sizing)
- Price targets (technical analysis)

---

#### 7. **Confidence** ❌
```python
# Your data: 'confidence': 0.0
```
**Why Not**: This is from your analysis/LLM, not market data.

**Status**: ❌ **Not available** - This is from your analysis system

---

#### 8. **Risk USD** ❌
```python
# Your data: 'risk_usd': 0.0
```
**Why Not**: This is calculated from:
- Position size
- Stop loss distance
- Entry price

OpenBB can provide current price, but risk calculation needs your position data.

**Status**: ⚠️ **Partial** - Can calculate if you have stop_loss and position size

**Can Calculate:**
```python
# If you have stop_loss from your exit_plan
risk_usd = abs(entry_price - stop_loss) * quantity
```

---

#### 9. **Notional USD** ❌
```python
# Your data: 'notional_usd': 23353.78
```
**Why Not**: This is calculated from:
- Quantity (your position)
- Current price (OpenBB can provide)

**Status**: ⚠️ **Partial** - OpenBB provides current_price, but you need quantity

**Can Calculate:**
```python
# OpenBB provides current_price
current_price = obb.equity.price.quote(symbol)['price']

# You provide quantity from your positions
notional_usd = current_price * quantity
```

---

## Summary

### ✅ **OpenBB Can Provide:**
1. **Current Price** - ✅ 100%
2. **Historical Prices** - ✅ 100%
3. **Price Data for Calculations** - ✅ 100%

### ❌ **OpenBB Cannot Provide (Position-Specific):**
1. **Entry Price** - ❌ Your position data
2. **Quantity** - ❌ Your position data
3. **Leverage** - ❌ Your account setting
4. **Exit Plan** - ❌ Your trading strategy
5. **Confidence** - ❌ Your analysis output

### ⚠️ **Can Calculate with OpenBB + Your Data:**
1. **Unrealized P&L** - ⚠️ Need: OpenBB (current_price) + Your (entry_price, quantity)
2. **Risk USD** - ⚠️ Need: Your (stop_loss, quantity) + OpenBB (current_price for validation)
3. **Notional USD** - ⚠️ Need: OpenBB (current_price) + Your (quantity)
4. **Liquidation Price** - ⚠️ Need: Your (entry_price, leverage, margin) + OpenBB (current_price for validation)

---

## What You Can Add to Metrics

### ✅ **Add These (OpenBB Provides):**

```python
# Add to your metrics tracking
metrics = {
    # From OpenBB
    'current_price': obb.equity.price.quote(symbol)['price'],
    'price_change_1d': calculate_price_change(symbol, days=1),
    'price_change_1w': calculate_price_change(symbol, days=7),
    'volatility': obb.technical.volatility(symbol),
    'rsi': obb.technical.rsi(symbol, period=14),
    'macd': obb.technical.macd(symbol),
    'support_level': calculate_support(symbol),
    'resistance_level': calculate_resistance(symbol),
    
    # From your positions (not OpenBB)
    'entry_price': position['entry_price'],
    'quantity': position['quantity'],
    'leverage': position['leverage'],
    
    # Calculated (using OpenBB + your data)
    'unrealized_pnl': (current_price - entry_price) * quantity,
    'notional_usd': current_price * quantity,
    'risk_usd': abs(entry_price - stop_loss) * quantity,
}
```

---

## Recommended Metrics to Track

### Market Data (OpenBB):
- ✅ Current price
- ✅ Price changes (1d, 1w, 1m)
- ✅ Volatility
- ✅ Technical indicators (RSI, MACD)
- ✅ Support/Resistance levels
- ✅ Volume metrics

### Position Data (Your System):
- Entry price
- Quantity
- Leverage
- Exit plan (profit target, stop loss)

### Calculated Metrics (OpenBB + Your Data):
- Unrealized P&L
- Notional USD
- Risk USD
- Distance to stop loss
- Distance to profit target
- Risk/Reward ratio

---

## Implementation Example

```python
def enrich_position_with_openbb_metrics(position: dict) -> dict:
    """
    Enrich position data with OpenBB market metrics.
    """
    symbol = position['symbol'].replace('xyz:', '')  # Remove prefix
    
    # Get market data from OpenBB
    current_price = obb.equity.price.quote(symbol)['price']
    historical = obb.equity.price.historical(symbol, limit=30)
    rsi = obb.technical.rsi(symbol, period=14)
    macd = obb.technical.macd(symbol)
    volatility = obb.technical.volatility(symbol)
    
    # Calculate additional metrics
    price_change_1d = (current_price - historical['close'].iloc[-2]) / historical['close'].iloc[-2] * 100
    
    # Enrich position with OpenBB metrics
    enriched_position = {
        **position,  # Keep existing position data
        'openbb_metrics': {
            'current_price': current_price,
            'price_change_1d_pct': price_change_1d,
            'rsi': rsi,
            'macd': macd,
            'volatility': volatility,
            'support_level': calculate_support(historical),
            'resistance_level': calculate_resistance(historical),
        },
        # Recalculate using OpenBB current_price
        'unrealized_pnl': (current_price - position['entry_price']) * position['quantity'],
        'notional_usd': current_price * position['quantity'],
        'distance_to_stop_loss_pct': ((current_price - position['exit_plan']['stop_loss']) / current_price) * 100,
        'distance_to_profit_target_pct': ((position['exit_plan']['profit_target'] - current_price) / current_price) * 100,
    }
    
    return enriched_position
```

---

## Bottom Line

**OpenBB can provide:**
- ✅ Current prices
- ✅ Historical prices
- ✅ Technical indicators
- ✅ Volatility
- ✅ Support/Resistance

**OpenBB cannot provide:**
- ❌ Position-specific data (entry_price, quantity, leverage)
- ❌ Trading strategy decisions (exit_plan, confidence)
- ❌ Account-specific settings

**You can calculate:**
- ⚠️ Unrealized P&L (using OpenBB current_price + your entry_price/quantity)
- ⚠️ Notional USD (using OpenBB current_price + your quantity)
- ⚠️ Risk USD (using your stop_loss + quantity)

**Recommendation**: Use OpenBB to enrich your positions with market metrics, then combine with your position data to calculate position-specific metrics.


