# Parallel Backtest System with Portfolio Management

## Overview

This system runs stock analysis in parallel using multiple API keys and implements a two-tier decision-making architecture:

1. **Stock-Level Decisions**: Each stock is analyzed independently using its own API key
2. **Portfolio-Level Allocation**: A Portfolio Manager receives all stock decisions and makes final allocation decisions

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Parallel Orchestrator                         │
│                                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Stock 1  │  │ Stock 2  │  │ Stock 3  │  │ Stock N  │       │
│  │ (API-1)  │  │ (API-2)  │  │ (API-3)  │  │ (API-N)  │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │             │             │             │               │
│       └─────────────┴─────────────┴─────────────┘               │
│                         │                                        │
│                         ▼                                        │
│              ┌──────────────────────┐                           │
│              │  Portfolio Manager   │                           │
│              │  (Separate API Key)  │                           │
│              └──────────┬───────────┘                           │
│                         │                                        │
│                         ▼                                        │
│              ┌──────────────────────┐                           │
│              │   Execute Trades     │                           │
│              └──────────────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

## Key Benefits

1. **Parallel Execution**: All stocks analyzed simultaneously → faster backtests
2. **Rate Limit Avoidance**: Each stock uses a different API key
3. **Portfolio-Level Risk Management**: Portfolio Manager balances positions across stocks
4. **Dynamic Position Sizing**: No hardcoded calculations - Portfolio Manager determines optimal allocation
5. **Synchronized Decisions**: All decisions finish around the same time, enabling holistic portfolio management

## Setup

### 1. Configure API Keys

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```bash
# Add as many API keys as you have
GEMINI_API_KEY_1=your_first_key
GEMINI_API_KEY_2=your_second_key
GEMINI_API_KEY_3=your_third_key
# etc.

# Optional: Dedicated key for Portfolio Manager
GEMINI_API_KEY_PORTFOLIO=your_portfolio_manager_key
```

**Important**: The more API keys you provide, the more stocks you can analyze in parallel without hitting rate limits.

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Run a backtest with default settings (Sentiment + Valuation):

```bash
python ParallelOrchestrator.py \
  --start-date 2025-07-01 \
  --end-date 2025-10-01 \
  --symbols PLTR,NVDA,GOOGL,ABBV,JPM
```

### Advanced Usage

Specify which agents to use:

```bash
# Use all three agents
python ParallelOrchestrator.py \
  --start-date 2025-07-01 \
  --end-date 2025-10-01 \
  --symbols PLTR,NVDA,GOOGL,ABBV,JPM,UNH,RKLB \
  --all-agents \
  --backtest-name full_test

# Use only sentiment and fundamental
python ParallelOrchestrator.py \
  --start-date 2025-07-01 \
  --end-date 2025-10-01 \
  --symbols PLTR,NVDA,GOOGL \
  --sentiment \
  --fundamental \
  --backtest-name sent_fund

# Control parallelism
python ParallelOrchestrator.py \
  --start-date 2025-07-01 \
  --end-date 2025-10-01 \
  --symbols PLTR,NVDA,GOOGL,ABBV,JPM \
  --max-workers 5  # Limit to 5 parallel workers
```

### Command-Line Options

- `--start-date`: Start date for backtest (YYYY-MM-DD)
- `--end-date`: End date for backtest (YYYY-MM-DD)
- `--symbols`: Comma-separated list of stock symbols
- `--sentiment`: Enable sentiment analysis
- `--valuation`: Enable valuation analysis
- `--fundamental`: Enable fundamental analysis
- `--all-agents`: Enable all three agents
- `--lookback`: Number of previous decisions to include as context (default: 4)
- `--backtest-name`: Name for this backtest run (default: "parallel")
- `--max-workers`: Maximum number of parallel workers (default: number of API keys)
- `--data-dir`: Data directory (default: current directory)

## How It Works

### 1. Stock Analysis Phase (Parallel)

For each trading day, the orchestrator:

1. Spawns parallel workers (one per stock)
2. Each worker:
   - Loads/generates sentiment, valuation, and fundamental analysis
   - Uses assigned API key to call ReasoningAgent
   - Returns a decision: BUY/SELL/HOLD with confidence level
3. All workers complete around the same time

### 2. Portfolio Management Phase (Sequential)

After collecting all stock decisions, the Portfolio Manager:

1. Receives all stock decisions for the day
2. Analyzes current portfolio state:
   - Available cash
   - Current positions and their values
   - Portfolio concentration
   - Risk exposure
3. Makes allocation decisions:
   - Which stocks to actually trade
   - Position sizes for each trade
   - Risk management constraints
4. Returns portfolio-level decisions with specific dollar amounts

### 3. Trade Execution Phase

The orchestrator:

1. Executes trades based on Portfolio Manager decisions
2. Updates portfolio state
3. Logs all trades and decisions
4. Moves to next trading day

## Portfolio Manager Capabilities

The Portfolio Manager considers:

- **Position Sizing**: Determines optimal position sizes based on confidence and risk
- **Portfolio Balance**: Maintains diversification across stocks
- **Risk Management**: Prevents over-concentration in single positions
- **Cash Management**: Maintains appropriate cash reserves
- **Existing Positions**: Considers current holdings when sizing new positions
- **Correlation**: Avoids over-allocation to correlated stocks

## Output Files

The system generates:

1. **Results JSON**: `parallel_backtest_{name}_results.json`
   - Complete backtest results
   - Trade history
   - Performance metrics
   
2. **Decision Logs**: `reasoning_decisions/`
   - Individual stock decisions for each day
   - Used as context for future decisions
   
3. **Backtest Log**: `logs/parallel_backtest_{name}.log`
   - Detailed execution log
   - All decisions and trades
   - Portfolio state changes

## Performance Metrics

The backtest calculates:

- **Total Return**: Absolute and percentage return
- **Portfolio Value**: Daily portfolio valuation
- **Trade Statistics**: Number of trades, decisions made
- **Position Breakdown**: Final positions and cash allocation

## Comparison: Sequential vs Parallel

### Old Sequential Approach (Orchestrator_2.0_Universal.py)

```python
for symbol in symbols:
    # Process one stock at a time
    sentiment = analyze_sentiment(symbol)
    valuation = analyze_valuation(symbol)
    decision = make_decision(symbol, sentiment, valuation)
    execute_trade(decision)  # Executes immediately with hardcoded sizing
```

**Issues**:
- Slow: stocks processed one by one
- Rate limits: single API key
- Hardcoded position sizing (20% * confidence)
- No portfolio-level coordination

### New Parallel Approach (ParallelOrchestrator.py)

```python
# Phase 1: Parallel stock analysis
with ThreadPoolExecutor() as executor:
    decisions = executor.map(analyze_stock, symbols, api_keys)

# Phase 2: Portfolio-level allocation
portfolio_decisions = portfolio_manager.allocate(decisions, portfolio_state)

# Phase 3: Execute trades
execute_trades(portfolio_decisions)
```

**Benefits**:
- Fast: all stocks analyzed simultaneously
- No rate limits: separate API key per stock
- Dynamic position sizing via Portfolio Manager
- Holistic portfolio management

## Example Output

```
🚀 Starting PARALLEL backtest from 2025-07-01 to 2025-10-01
📊 Analyzing 7 stocks in parallel
📅 Found 65 trading days

============================================================
📅 TRADING DAY: 2025-07-01
============================================================

[PLTR] ✅ Decision: BUY (confidence: 0.85)
[NVDA] ✅ Decision: BUY (confidence: 0.92)
[GOOGL] ✅ Decision: HOLD (confidence: 0.75)
[ABBV] ✅ Decision: BUY (confidence: 0.78)
[JPM] ✅ Decision: HOLD (confidence: 0.60)
[UNH] ✅ Decision: SELL (confidence: 0.88)
[RKLB] ✅ Decision: BUY (confidence: 0.70)

📊 Collected 7 stock decisions

💼 Calling Portfolio Manager for allocation decisions...

💰 Portfolio Manager Decisions:
  PLTR: BUY $170,000 (target: 17.0%)
  NVDA: BUY $184,000 (target: 18.4%)
  GOOGL: HOLD $0 (target: 0.0%)
  ABBV: BUY $117,000 (target: 11.7%)
  JPM: HOLD $0 (target: 0.0%)
  UNH: SELL $215,000 (target: 0.0%)
  RKLB: BUY $105,000 (target: 10.5%)

📈 Portfolio Summary:
  Total Allocation: $576,000
  Cash Reserved: $639,000
  Risk Assessment: Moderate - balanced allocation across growth and value

✅ BUY PLTR: 965 shares @ $176.17 = $170,004.05
✅ BUY NVDA: 1,012 shares @ $181.85 = $184,032.20
✅ BUY ABBV: 479 shares @ $244.38 = $117,058.02
✅ BUY RKLB: 2,187 shares @ $47.97 = $104,903.39
✅ SELL UNH: 617 shares @ $348.30 = $214,961.10

💼 Portfolio Value: $1,008,250.00

============================================================
```

## Troubleshooting

### Rate Limiting Issues

If you're still hitting rate limits:
1. Add more API keys in `.env`
2. Reduce `--max-workers`
3. Add delays between days (can modify the orchestrator)

### API Key Not Found

Error: `No API keys found. Set GEMINI_API_KEY_1, GEMINI_API_KEY_2, etc.`

Solution: Make sure `.env` file exists and contains at least one API key

### Missing Analysis Data

If stocks are being skipped:
1. Check that analysis files exist in `sentiment_data/`, `valuation_reports/`, `fundamental_reports/`
2. Or enable agent generation (the system will auto-generate missing data)

## Future Improvements

Potential enhancements:

1. **Async Execution**: Use asyncio instead of ThreadPoolExecutor for better performance
2. **Dynamic API Key Pool**: Add/remove API keys at runtime
3. **Advanced Portfolio Strategies**: Multiple portfolio management strategies
4. **Risk Models**: Incorporate volatility, correlation, VaR calculations
5. **Multi-Day Optimization**: Portfolio Manager considers multi-day strategy
6. **Partial Position Management**: Buy/sell partial positions instead of all-or-nothing

## Questions?

This system provides a professional-grade backtesting framework with parallel execution and sophisticated portfolio management. The architecture is extensible and can be adapted for live trading with minimal modifications.

