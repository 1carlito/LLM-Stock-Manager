# Portfolio Manager Previous Decisions Integration

## Overview
Updated the Portfolio Manager Agent to include up to 4 previous portfolio allocation decisions in its context when making new allocation decisions. This allows the portfolio manager to better understand the portfolio's recent trading history and patterns.

## Changes Made

### 1. **PortfolioManagerAgent.py** (Both locations updated)
- **New Parameter**: Added `previous_portfolio_decisions` parameter to `make_portfolio_decisions()` method
- **Updated Method Signature**:
  ```python
  def make_portfolio_decisions(self, stock_decisions, portfolio_state, current_date, previous_portfolio_decisions=None)
  ```
- **Updated Prompt Builder**: Modified `_build_portfolio_prompt()` to:
  - Accept the `previous_portfolio_decisions` parameter
  - Include previous portfolio allocation decisions in the LLM prompt
  - Add analysis guidance to consider historical patterns, position evolution, and allocation trends

- **New Import**: Added `import glob` for file pattern matching

### 2. **ParallelOrchestrator.py** (Both locations updated)
- **New Method**: `_load_previous_portfolio_decisions(current_date)`
  - Loads up to 4 previous portfolio allocation decisions from the `portfolio_decisions` directory
  - Filters decisions that occurred before the current date
  - Supports both backtest-specific and generic portfolio decision files
  
- **New Method**: `_save_portfolio_decision(portfolio_decisions, current_date)`
  - Saves portfolio decisions to the `portfolio_decisions` directory
  - Uses filename format: `portfolio_decisions_{date}_{backtest_name}.json`
  - Enables future retrieval of decision history

- **Updated Portfolio Decision Flow**:
  - Before calling Portfolio Manager, loads previous portfolio decisions
  - Passes these decisions to the Portfolio Manager
  - After receiving portfolio decisions, saves them for future context

## File Locations Updated
1. `/Users/pc/stock_agent_eval/stock_agent_eval_clean/multistock_port/PortfolioManagerAgent.py`
2. `/Users/pc/stock_agent_eval/stock_agent_eval_clean/multistock_port/ParallelOrchestrator.py`
3. `/Users/pc/stock_agent_eval/stock_agent_eval_clean/aws/multistock_port_2.0/PortfolioManagerAgent.py`
4. `/Users/pc/stock_agent_eval/stock_agent_eval_clean/aws/multistock_port_2.0/ParallelOrchestrator.py`

## Directory Structure
The following directory structure will be created during execution:
```
portfolio_decisions/
├── portfolio_decisions_2025-01-15_parallel.json
├── portfolio_decisions_2025-01-16_parallel.json
├── portfolio_decisions_2025-01-17_parallel.json
└── portfolio_decisions_2025-01-18_parallel.json
```

## LLM Prompt Enhancement
The Portfolio Manager now receives context about:
- **Previous Allocation Decisions**: Last 4 portfolio allocation decisions
- **Analysis Guidance**:
  - Whether previous allocations achieved their intended portfolio weights
  - How the portfolio evolved through previous decisions
  - Patterns in position sizing or trading activity
  - Current vs. target allocations based on recent history

This additional context allows the Portfolio Manager to:
1. Maintain consistency with portfolio strategy
2. Identify and learn from allocation patterns
3. Adapt position sizing based on recent performance
4. Better balance new positions with existing holdings

## Backward Compatibility
- Both methods work with `previous_portfolio_decisions=None` (default)
- If previous portfolio decisions are not provided or the directory doesn't exist, the system gracefully falls back
- Existing code that doesn't pass previous decisions will continue to work unchanged

## Future Enhancements
Potential extensions to this feature:
- Include sentiment/valuation/fundamental analysis in the portfolio decision context
- Track which allocations were profitable for pattern learning
- Implement portfolio performance analysis in the LLM prompt
- Add allocation success metrics to historical decisions
