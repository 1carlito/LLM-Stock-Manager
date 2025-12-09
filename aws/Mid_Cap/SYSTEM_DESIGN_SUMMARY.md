System Design Summary: Reasoning Agent → Portfolio Manager

Overview

Two-tier decision-making

          
     Reasoning Agent
          ↓
 Portfolio Manager Agent
          ↓
 Parallel Orchestrator (exec)

1) Reasoning Agent
Role: Stock-level decision maker
Inputs: 3 Sub-Agent analyses, Previous decisions (up to 5).
Output: BUY / SELL / NEUTRAL / MAINTAIN + confidence; short_confidence when SELL.
Model: DeepSeek via Chutes API with retry/backoff; saves JSON decisions per symbol/date.

2) Portfolio Manager Agent
Role: Portfolio-aware allocator and constraint enforcer
Execution priority: CLOSE/COVER/SELL → SHORT → BUY
Decision conversion:
SELL on unowned → SHORT
BUY on shorted → COVER then BUY
SHORT on owned → SELL then SHORT

Short rules:
Block all new shorts if cash < 25% of initial capital
Per-short cap: 25% of remaining cash (bounded by max_short_per_stock_pct, default 25%)
Spread fee on shorts: 0.0006 + 0.0010 + (1 / sqrt(market_cap_bil)), charged on entry and cover

Long rules:
Each BUY capped at 25% of remaining cash
No spread fee applied to BUY in current PM code
Sorting/priority: Shorts and buys sorted by confidence; CLOSEs always included

3) Parallel Orchestrator
Role: Runs daily loop; loads latest analyses; calls Reasoning; feeds PM; executes with price lookups and short spreads
Uses multiple API keys, trading calendar, and logs per backtest; executes in priority order (close → short → buy); applies short spreads on entry/exit


4) Constraints & Costs (as implemented)
Short spread: 0.0006 + 0.0010 + (1 / sqrt(market_cap_bil)) on short entry + cover
Overnight fee on shorts: ~2% annual, charged daily while the short is open (deducted from cash)
Short gating: no new shorts when cash < 25% of initial
Position caps: BUY cap 25% of remaining cash; SHORT cap 25% of remaining cash (per name)


Note: Longs have no overnight fee in the current code.
