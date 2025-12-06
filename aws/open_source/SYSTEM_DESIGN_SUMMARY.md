# System Design Summary: Reasoning Agent → Portfolio Manager

## Overview

The system uses a **two-tier decision-making architecture** that separates **stock-level analysis** from **portfolio-level allocation**. This design ensures that individual stock decisions are made independently of portfolio constraints, while portfolio management handles capital allocation, risk limits, and position management.

---

## Architecture Flow

```
Analysis Agents (Fundamental, Valuation, Sentiment)
         ↓
    Reasoning Agent (Stock-Level Decision)
         ↓
   Portfolio Manager Agent (Portfolio-Level Allocation)
         ↓
   Parallel Orchestrator (Execution)
```

---

## 1. Reasoning Agent

### Purpose
**Stock-level decision maker** that evaluates individual stocks based on analysis signals. It focuses solely on the stock's outlook, independent of portfolio state.

### Key Responsibilities
1. **Synthesize Analysis Signals**: Integrates inputs from:
   - Fundamental Agent (financial metrics, P/E, P/B ratios)
   - Valuation Agent (technical analysis, price targets)
   - Sentiment Agent (news sentiment, market sentiment)

2. **Make Stock-Level Decisions**: Outputs one of three decisions:
   - **BUY**: Stock is undervalued or has strong positive signals
   - **SELL**: Stock is overvalued or has strong negative signals
   - **HOLD**: No clear decisive action from signals

3. **Provide Confidence Metrics**:
   - `confidence` (1-100): Overall confidence in the decision
   - `short_confidence` (0-100): For SELL decisions, confidence in shorting potential

### Design Principles
- **Portfolio-Agnostic**: Does NOT know about:
  - Current portfolio positions
  - Available cash
  - Portfolio constraints
  - Other stock decisions
  
- **Stock-Focused**: Only evaluates:
  - Stock's fundamental strength/weakness
  - Valuation attractiveness
  - Market sentiment
  - Historical decision patterns for that stock

### Output Format
```json
{
  "symbol": "ASPI",
  "decision": "SELL",
  "confidence": 85,
  "short_confidence": 75,
  "reasoning": "Weak fundamentals, overvalued, negative sentiment"
}
```

### Why This Design?
- **Separation of Concerns**: Stock analysis is independent of portfolio management
- **Scalability**: Can analyze many stocks in parallel without portfolio context
- **Clarity**: Each agent has a single, clear responsibility
- **Flexibility**: Portfolio Manager can reinterpret decisions based on portfolio state

---

## 2. Portfolio Manager Agent

### Purpose
**Portfolio-level capital allocator** that takes individual stock decisions and converts them into actionable portfolio allocations with position sizing, risk management, and constraint enforcement.

### Key Responsibilities
1. **Convert Stock Decisions to Portfolio Actions**:
   - `BUY` → `BUY` action with position sizing
   - `SELL` on owned stock → `SELL` action (close long)
   - `SELL` on unowned stock → `SHORT` action (open short)
   - `HOLD` → `HOLD` action (maintain/extend positions)

2. **Position Sizing**:
   - Scales allocations by confidence and available capital
   - Enforces 30% portfolio limit per position
   - Applies 30% of cash limit for shorts
   - Distributes capital across multiple opportunities

3. **Risk Management**:
   - Ensures total allocations don't exceed available cash
   - Manages margin requirements for shorts (50% margin)
   - Tracks total short allocation (30% max)
   - Prevents over-concentration

4. **Portfolio Context Awareness**:
   - Knows current positions (longs and shorts)
   - Knows available cash and portfolio value
   - Knows previous allocation decisions
   - Understands portfolio performance

### Design Principles
- **Portfolio-Aware**: Has full visibility into:
  - Current positions and their values
  - Available cash and margin capacity
  - Portfolio constraints and limits
  - Historical allocation patterns

- **Capital Allocation Focus**: Makes decisions about:
  - How much to allocate to each opportunity
  - Which positions to close or extend
  - How to balance risk and return
  - How to manage cash and margin

### Parallel Processing
- **Splits stock decisions** into two parts for parallel API calls
- **Coordination mechanism**:
  - Shared state with lock
  - Symbol tracking to prevent duplicates
  - Reconciliation with action priority

### Output Format
```json
{
  "portfolio_decisions": [
    {
      "symbol": "ASPI",
      "action": "SHORT",
      "amount_usd": 30000.00,
      "reasoning": "High conviction short, 75% short confidence",
      "portfolio_weight_target": 3.0
    }
  ],
  "portfolio_summary": {
    "total_allocation": 0,
    "total_short_allocation": 30000.00,
    "cash_reserved": 970000.00
  }
}
```

### Why This Design?
- **Centralized Risk Management**: All constraints enforced in one place
- **Portfolio Optimization**: Can balance allocations across all opportunities
- **Context-Aware Decisions**: Can handle complex scenarios (e.g., short owned stock)
- **Efficient Capital Deployment**: Optimizes capital allocation across multiple stocks

---

## 3. Key Design Decisions

### Why Separate Reasoning from Portfolio Management?

1. **Single Responsibility Principle**:
   - Reasoning Agent: "Is this stock good/bad?"
   - Portfolio Manager: "How much should we allocate?"

2. **Parallel Processing**:
   - Stock analysis can run in parallel (no shared state)
   - Portfolio decisions require coordination (shared cash, positions)

3. **Scalability**:
   - Can analyze 100 stocks without portfolio context
   - Portfolio Manager only processes decisions that pass analysis

4. **Flexibility**:
   - Portfolio Manager can reinterpret decisions:
     - SELL on unowned → SHORT
     - BUY on shorted → COVER then BUY
     - SHORT on owned → SELL then SHORT

### Why Portfolio Manager Handles Position Management?

1. **Context Required**: Needs to know:
   - What positions exist
   - What cash is available
   - What constraints apply

2. **Complex Scenarios**: Handles:
   - Converting SELL to SHORT (if not owned)
   - Auto-covering shorts before BUY
   - Auto-selling longs before SHORT
   - Extending short holding periods

3. **Risk Management**: Enforces:
   - Position size limits (30% per position)
   - Total short limits (30% of cash)
   - Cash constraints
   - Margin requirements

---

## 4. Data Flow

### Daily Trading Flow

1. **Price Update** (Start of Day):
   - Get current day's closing prices from analysis
   - Update `last_prices` with current day's prices

2. **Stock Analysis** (Parallel):
   - For each stock: Load analysis data (fundamental, valuation, sentiment)
   - Reasoning Agent makes decision (BUY/SELL/HOLD)
   - Returns: `{symbol, decision, confidence, short_confidence, reasoning}`

3. **Portfolio Value Calculation**:
   - Calculate portfolio value using current day's closing prices
   - Formula: `Cash + Long Positions Value + Short P&L`

4. **Portfolio Allocation** (Parallel Threads):
   - Split stock decisions into two parts
   - Each thread processes half the stocks
   - Coordination mechanism prevents duplicates
   - Returns: `{portfolio_decisions: [{symbol, action, amount_usd, ...}]}`

5. **Trade Execution**:
   - Execute portfolio decisions in priority order:
     - SELL/COVER first (free up capital)
     - SHORT second
     - BUY last
   - Apply constraints (30% limits, cash limits)
   - Apply costs (spreads, overnight fees)

---

## 5. Constraints and Limits

### Position Limits
- **Max Single Position**: 30% of portfolio value (for longs)
- **Max Single Short**: 30% of available cash
- **Max Total Shorts**: 30% of available cash

### Margin Requirements
- **Short Margin**: 50% of short value
- **Example**: Short $30K → Reserve $15K margin

### Cost Structure
- **Short Spread**: 0.1% + 1/√(Market Cap in billions)
- **Overnight Fees**: 2% annual rate (~0.0055% per day)
- **Applied to**: SHORT entry, COVER exit

---

## 6. Key Features

### Coordination Mechanism
- **Shared State**: Tracks allocated symbols and cash
- **Lock Mechanism**: Ensures thread-safe allocation
- **Reconciliation**: Deduplicates by action priority

### Error Handling
- **JSON Parsing**: Robust multi-strategy parser with cleanup
- **Symbol Validation**: Rejects invalid symbols (e.g., "NEW_OPPORTUNITY")
- **Fallback Allocation**: Simple confidence-based allocation if API fails

### Position Management
- **Auto-Sell Before Short**: If SHORT on owned stock, sells long first
- **Auto-Cover Before Buy**: If BUY on shorted stock, covers short first
- **Flexible Short Holding**: Can extend short positions via SHORT/HOLD actions
- **Auto-Close Safety**: Closes shorts after 90 days (safety limit)

---

## 7. Summary

### Reasoning Agent
- **Role**: Stock analyst
- **Input**: Analysis data (fundamental, valuation, sentiment)
- **Output**: Stock decision (BUY/SELL/HOLD) with confidence
- **Focus**: Stock outlook only
- **Blind to**: Portfolio state, other stocks, constraints

### Portfolio Manager Agent
- **Role**: Capital allocator
- **Input**: Stock decisions + portfolio state
- **Output**: Portfolio allocations with position sizes
- **Focus**: Capital allocation, risk management, constraints
- **Aware of**: All positions, cash, limits, previous decisions

### Design Benefits
1. **Clear Separation**: Each agent has a single, well-defined purpose
2. **Scalability**: Can analyze many stocks in parallel
3. **Flexibility**: Portfolio Manager can reinterpret decisions
4. **Risk Management**: Centralized constraint enforcement
5. **Maintainability**: Changes to one agent don't affect the other

This architecture ensures that stock analysis remains pure and unbiased, while portfolio management handles the complex task of capital allocation and risk management.

