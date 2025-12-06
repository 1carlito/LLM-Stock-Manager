# Cash Tracking & Calculation: Comparison with Popular Libraries

## Overview
This document compares how popular Python trading/backtesting libraries handle cash tracking versus our **Waterfall Allocation** approach.

---

## 🔍 How Popular Libraries Handle Cash

### 0. **TradingAgents** (TauricResearch/TradingAgents)
**Approach:** Multi-agent LLM framework with LangGraph orchestration

**Architecture:**
- Built with **LangGraph** (not LangChain, but related framework)
- Multi-agent system: Analyst Team → Researcher Team → Trader Agent → Risk Management → Portfolio Manager
- Portfolio Manager has final approval/rejection authority
- Risk Management evaluates and adjusts trading strategies

**Cash/Fund Allocation (Based on Architecture):**
- **Portfolio Manager** approves/rejects transaction proposals
- **Trader Agent** determines "timing and magnitude of trades"
- **Risk Management** evaluates portfolio risk and adjusts strategies
- No explicit waterfall allocation mentioned in documentation
- Decision-making appears to be LLM-based rather than algorithmic

**Key Characteristics:**
```python
# Inferred pattern from architecture:
# 1. Trader Agent proposes trade with magnitude
# 2. Risk Management evaluates risk
# 3. Portfolio Manager approves/rejects
# 4. If approved, order sent to simulated exchange
```

**Issues (Inferred):**
- ❌ **LLM-based decisions**: Allocation magnitude determined by LLM, not algorithmic constraints
- ❌ **No sequential waterfall**: No mention of sequential cash constraint enforcement
- ❌ **Approval-based, not allocation-based**: Portfolio Manager approves/rejects, but doesn't appear to allocate capital sequentially
- ❌ **No per-trade caps**: No mention of percentage-based caps on remaining cash
- ❌ **Potential overspending**: If multiple trades approved simultaneously, total could exceed available capital

**Cash Update Pattern (Inferred):**
- Cash likely updated after Portfolio Manager approval
- No sequential processing mentioned
- Relies on LLM to determine appropriate trade sizes
- No algorithmic constraint enforcement

**Repository Focus:**
- Focuses on multi-agent collaboration and LLM-based decision making
- Uses LangGraph for agent orchestration
- Emphasis on agent debates and discussions
- Portfolio management appears to be approval-based rather than allocation-based

---

### 1. **moon-dev-ai-agents** (moondevonyt/moon-dev-ai-agents)
**Approach:** Agent-based, per-agent cash tracking

**Cash Tracking:**
- Each agent maintains its own `self.cash` attribute
- Cash balance initialized per agent (e.g., starting balance)
- Cash updated during trade execution within each agent
- No centralized portfolio allocation system
- Agents operate independently

**Key Characteristics:**
```python
# Typical moon-dev-ai-agents pattern:
class TradingAgent:
    def __init__(self):
        self.cash = 100000  # Starting balance per agent
    
    def execute_trade(self, cost):
        if self.cash >= cost:
            self.cash -= cost  # Update agent's cash
            # Execute trade
```

**Issues:**
- ❌ **No centralized cash management**: Each agent tracks cash independently
- ❌ **No waterfall allocation**: No sequential processing or constraint enforcement
- ❌ **No per-trade caps**: No mechanism to limit trade sizes relative to remaining cash
- ❌ **No priority processing**: All trades calculated independently
- ❌ **Potential overspending**: If multiple agents trade simultaneously, total can exceed available capital
- ❌ **No portfolio-level constraints**: No enforcement of cash constraints across all agents

**Cash Update Pattern:**
- Cash updated per agent after each trade
- No sequential waterfall logic
- No centralized portfolio manager enforcing constraints
- Relies on per-agent checks only

**Repository Focus:**
- Focuses on AI agents for strategy generation and backtesting
- Uses external libraries (like `backtesting.py`) for actual execution
- No built-in portfolio allocation algorithm
- Agents are more about generating trading signals than managing capital

---

### 1. **backtrader** (mementum/backtrader)
**Approach:** Event-driven, broker-managed cash

**Cash Tracking:**
- Cash is managed by the `Broker` object
- `broker.getcash()` returns current cash balance
- Cash is updated **after** order execution
- Orders are checked against cash **before** execution

**Key Characteristics:**
```python
# Typical backtrader pattern:
if self.broker.getcash() >= order_price:
    self.buy(size=shares)
    # Cash automatically deducted by broker
```

**Issues:**
- ❌ **No sequential constraint enforcement**: If multiple orders are placed in the same bar, they may all check cash independently
- ❌ **Batch processing risk**: Multiple orders can be queued before any execute, leading to potential overspending
- ❌ **No per-trade caps**: No built-in mechanism to limit individual trade sizes relative to remaining cash

**Cash Update Pattern:**
- Cash updated **after** order fills
- No pre-allocation or waterfall logic
- Relies on broker rejecting orders if insufficient cash

---

### 2. **backtesting.py** (kernc/backtesting.py)
**Approach:** Vectorized backtesting with position sizing

**Cash Tracking:**
- Cash tracked in `Backtest` class
- Position sizing calculated as percentage of equity
- Cash updated after each trade execution

**Key Characteristics:**
```python
# Typical backtesting.py pattern:
size = self.equity * 0.1  # 10% of equity
if size <= self.cash:
    self.buy(size=size)
    # Cash deducted
```

**Issues:**
- ❌ **Percentage-based, not sequential**: All trades calculated independently
- ❌ **No waterfall constraint**: If 5 trades each want 10% of equity, all 5 may execute even if total > 100%
- ❌ **Equity-based sizing**: Uses total equity (cash + positions), not just cash
- ❌ **No per-trade caps**: No mechanism to prevent one trade from taking too much

**Cash Update Pattern:**
- Cash updated after each trade
- But all trades are calculated **before** any execute
- Can lead to overspending if multiple trades are queued

---

### 3. **Zipline** (Quantopian/Zipline)
**Approach:** Event-driven with portfolio object

**Cash Tracking:**
- `portfolio.cash` tracks available cash
- `portfolio.positions` tracks holdings
- Orders checked against cash before execution

**Key Characteristics:**
```python
# Typical zipline pattern:
if context.portfolio.cash >= order_cost:
    order_target_percent(asset, 0.1)  # 10% allocation
    # Cash updated after order fills
```

**Issues:**
- ❌ **Target-based allocation**: Uses `order_target_percent()` which calculates independently
- ❌ **No sequential processing**: All orders calculated before execution
- ❌ **Rebalancing can overspend**: If rebalancing multiple positions, total can exceed cash

**Cash Update Pattern:**
- Cash updated after order execution
- But order sizing calculated **before** execution
- Multiple orders can be queued simultaneously

---

### 4. **vectorbt** (polakowo/vectorbt)
**Approach:** Vectorized, array-based calculations

**Cash Tracking:**
- Cash tracked as array across time
- Position sizing calculated vectorized
- Cash constraints applied via array operations

**Key Characteristics:**
```python
# Typical vectorbt pattern:
sizes = vbt.Portfolio.from_signals(
    prices, 
    entries, 
    exits,
    size=0.1,  # 10% per trade
    cash='auto'  # Auto-managed cash
)
```

**Issues:**
- ❌ **Vectorized = no sequential logic**: All trades calculated simultaneously
- ❌ **Fixed sizing**: Uses fixed percentage, not adaptive to remaining cash
- ❌ **No waterfall**: Can't enforce "25% of remaining cash" per trade sequentially

**Cash Update Pattern:**
- Cash calculated as array across all timesteps
- No sequential constraint enforcement
- All trades sized independently

---

## ✅ Our Waterfall Allocation Approach

### Key Differences

**1. Sequential Processing with Real-Time Cash Updates**
```python
remaining_cash = available_cash  # Start with initial cash

# Process CLOSE first (generates cash)
for decision in close_decisions:
    # Cash increases when positions closed
    remaining_cash += proceeds

# Process SHORT (deducts cash + fees)
for decision in short_decisions:
    cap = remaining_cash * 0.25  # 25% of REMAINING cash
    # Execute trade
    remaining_cash -= (cost + spread_fee)  # Update immediately

# Process BUY (deducts cash)
for decision in buy_decisions:
    cap = remaining_cash * 0.25  # 25% of REMAINING cash (not initial!)
    # Execute trade
    remaining_cash -= cost  # Update immediately
```

**2. Per-Trade Caps Based on Remaining Cash**
- Each trade capped at **25% of remaining cash** (not initial cash)
- First trade: 25% of $100k = $25k
- Second trade: 25% of $75k = $18.75k
- Third trade: 25% of $56.25k = $14.06k
- This ensures cash never goes negative

**3. Priority-Based Processing**
- CLOSE → SHORT → BUY (in that order)
- CLOSE generates cash first
- SHORT uses cash (with fees)
- BUY uses remaining cash

**4. Spread Fee Handling**
- Spread fees deducted **during allocation** (not after)
- Prevents overspending due to fees
- Formula: `spread_rate = 0.0006 + 0.0010 + (1.0 / sqrt(market_cap_bil))`

**5. Short Position Blocking**
- Blocks new shorts when `cash < 25% of initial_value`
- Prevents over-leveraging during drawdowns

---

## 📊 Comparison Table

| Feature | TradingAgents | moon-dev-ai-agents | backtrader | backtesting.py | Zipline | vectorbt | **Our Waterfall** |
|--------|--------------|-------------------|------------|----------------|---------|-----------|-------------------|
| **Sequential Cash Updates** | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No | ✅ **Yes** |
| **Per-Trade Caps** | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No | ✅ **25% of remaining** |
| **Priority Processing** | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No | ✅ **CLOSE→SHORT→BUY** |
| **Spread Fee Handling** | ⚠️ LLM-based | ⚠️ Manual | ⚠️ Manual | ⚠️ Manual | ⚠️ Manual | ⚠️ Manual | ✅ **Built-in** |
| **Cash Constraint Enforcement** | ⚠️ Approval-based | ⚠️ Per-agent only | ⚠️ Broker-level | ⚠️ Per-trade check | ⚠️ Per-trade check | ⚠️ Array-based | ✅ **Waterfall-level** |
| **Overspending Prevention** | ⚠️ LLM-based | ⚠️ Per-agent only | ⚠️ Order rejection | ⚠️ Per-trade only | ⚠️ Per-trade only | ⚠️ Array constraints | ✅ **Guaranteed** |
| **Short Position Management** | ⚠️ Basic | ⚠️ Basic | ⚠️ Basic | ⚠️ Basic | ⚠️ Basic | ⚠️ Basic | ✅ **CFD model + blocking** |
| **Centralized Portfolio Management** | ✅ Yes (approval) | ❌ No | ⚠️ Broker-level | ⚠️ Backtest-level | ⚠️ Portfolio-level | ⚠️ Portfolio-level | ✅ **Yes (allocation)** |
| **Algorithmic vs LLM-based** | ⚠️ LLM-based | ⚠️ LLM-based | ✅ Algorithmic | ✅ Algorithmic | ✅ Algorithmic | ✅ Algorithmic | ✅ **Algorithmic** |

---

## 🎯 Why Our Approach is Unique

### Problem Solved
Most libraries calculate **all trades independently** before execution:
```python
# Common pattern (WRONG for strict cash constraints):
trade1_size = cash * 0.25  # $25k
trade2_size = cash * 0.25  # $25k
trade3_size = cash * 0.25  # $25k
# Total: $75k (but if cash = $50k, this overspends!)
```

### Our Solution
We calculate **sequentially with real-time updates**:
```python
# Waterfall pattern (CORRECT):
cash = $50k
trade1_size = cash * 0.25  # $12.5k, cash → $37.5k
trade2_size = cash * 0.25  # $9.375k, cash → $28.125k
trade3_size = cash * 0.25  # $7.03k, cash → $21.095k
# Total: $28.9k (never exceeds available cash!)
```

---

## 🔧 Implementation Details

### Cash Update Locations

**1. During Allocation (PortfolioManagerAgent)**
```python
# Line 905: SHORT positions
remaining_cash -= (final_amount + spread_fee)

# Line 934: BUY positions
remaining_cash -= final_amount
```

**2. During Execution (ParallelOrchestrator)**
```python
# Line 556: SELL positions
self.portfolio['cash'] += shares_to_close * current_price

# Line 595: COVER positions
self.portfolio['cash'] += entry_notional + pnl - exit_spread_fee

# Line 612: SHORT positions
self.portfolio['cash'] -= (cost_or_value + entry_spread_fee)

# Line 641: BUY positions
self.portfolio['cash'] -= cost_or_value
```

**3. Daily Updates (ParallelOrchestrator)**
```python
# Line 699: Overnight fees for shorts
self.portfolio['cash'] -= daily_overnight_fee
```

---

## 💡 Key Insights

1. **Most libraries don't enforce sequential cash constraints** - they rely on per-trade checks or broker-level rejection
2. **Our waterfall approach guarantees no overspending** - cash is updated after each trade before the next is calculated
3. **Per-trade caps based on remaining cash** - ensures no single trade can dominate
4. **Priority processing** - CLOSE generates cash before SHORT/BUY consume it
5. **Built-in fee handling** - spread fees and overnight fees are integrated into cash calculations

---

## 🚀 Open Source Value

This waterfall allocation approach solves a **real problem** that existing libraries don't address well:
- ✅ Strict cash constraint enforcement
- ✅ Sequential trade processing
- ✅ Per-trade caps
- ✅ Fee integration
- ✅ Short position management

**This is a unique contribution to the open-source trading community!**

