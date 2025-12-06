# MCP vs Current Approach: Architecture Comparison

## Overview

Both **Rallies AI** and **Scalar Field** use **MCP (Model Context Protocol)** for their agent architectures. This document explains the differences and why MCP is better for a future DB-based trade decision system.

---

## Current Approach: Multi-Step Agents with REST APIs

### How We Work Now

```python
# Current: Manual orchestration, explicit function calls
class ReasoningAgent:
    def make_decision(self, symbol, valuation_data, fundamental_data, sentiment_data):
        # 1. Build prompt with all pre-fetched data
        prompt = self._build_prompt(symbol, valuation_data, fundamental_data, sentiment_data)
        
        # 2. Call LLM API directly
        response = self._call_chutes_api(prompt)
        
        # 3. Parse response
        return self._parse_response(response)
```

**Flow:**
```
ParallelOrchestrator
    ↓
FundamentalAgent → REST API → Get data → Return to Orchestrator
ValuationAgent → REST API → Get data → Return to Orchestrator  
SentimentAgent → REST API → Get data → Return to Orchestrator
    ↓
Orchestrator collects all data
    ↓
ReasoningAgent → LLM API → Make decision
```

**Characteristics:**
- ✅ **Explicit**: We control every step
- ✅ **Predictable**: Fixed data flow
- ❌ **Rigid**: Hard to change workflow
- ❌ **Manual**: Must orchestrate everything
- ❌ **No Context**: Each call is independent

---

## MCP Approach: Agent-Driven Tool Discovery

### How Rallies AI & Scalar Field Work

```python
# MCP: LLM autonomously discovers and uses tools
class MCPReasoningAgent:
    def make_decision(self, symbol, context):
        # LLM can dynamically call tools as needed
        # Tools are discovered via MCP protocol
        
        # LLM decides: "I need fundamental data"
        # → Calls get_fundamental_data(symbol) via MCP
        
        # LLM decides: "I need to query DB for similar trades"
        # → Calls query_trade_decisions_db(symbol) via MCP
        
        # LLM chains operations based on context
        return llm_with_mcp_tools(context)
```

**Flow:**
```
LLM Agent (with MCP tools)
    ↓
Agent decides: "I need fundamental data"
    ↓
Calls MCP tool: get_fundamental_data(symbol)
    ↓
Agent decides: "I need to check DB for similar decisions"
    ↓
Calls MCP tool: query_trade_decisions_db(symbol, criteria)
    ↓
Agent decides: "Based on results, I'll make decision"
    ↓
Returns decision
```

**Characteristics:**
- ✅ **Autonomous**: LLM decides what tools to use
- ✅ **Context-Aware**: Maintains state across tool calls
- ✅ **Flexible**: Can chain operations dynamically
- ✅ **Discoverable**: Tools are self-describing
- ✅ **Stateful**: Context persists across interactions

---

## Key Differences

### 1. **Orchestration**

**Current (REST/Function Calls):**
```python
# We manually orchestrate
valuation_data = valuation_agent.analyze(symbol)
fundamental_data = fundamental_agent.analyze(symbol)
sentiment_data = sentiment_agent.analyze(symbol)
decision = reasoning_agent.make_decision(symbol, valuation_data, fundamental_data, sentiment_data)
```

**MCP:**
```python
# LLM orchestrates based on context
# LLM decides what it needs and when
decision = llm_agent.analyze(symbol)  
# LLM internally calls tools as needed via MCP
```

### 2. **Tool Discovery**

**Current:**
- Tools are hardcoded in Python
- Must know all available functions
- No dynamic discovery

**MCP:**
- Tools are registered with MCP server
- LLM discovers available tools dynamically
- Tools describe themselves (name, parameters, purpose)

### 3. **Context Management**

**Current:**
- Each API call is stateless
- Must pass all context explicitly
- No memory between calls

**MCP:**
- Maintains conversation context
- Tools can access previous results
- Stateful interactions

### 4. **Flexibility**

**Current:**
```python
# Fixed workflow - hard to change
if use_fundamental:
    fundamental_data = fundamental_agent.analyze(symbol)
if use_sentiment:
    sentiment_data = sentiment_agent.analyze(symbol)
# Must code every path
```

**MCP:**
```python
# LLM decides workflow dynamically
# "Based on this symbol, I should check DB first, then fundamentals"
# LLM can adapt workflow per symbol/context
```

---

## Future: DB-Based Trade Decision System

### What You Want

A system where the LLM can:
1. Query a database of past trade decisions
2. Find similar patterns
3. Make decisions based on historical context
4. Chain multiple queries dynamically

### Current Approach (Hard)

```python
# Must manually code every query
def make_decision_with_db(symbol, current_date):
    # 1. Manually query DB
    similar_trades = db.query("""
        SELECT * FROM trade_decisions 
        WHERE symbol = ? AND date > ? - 30 days
        ORDER BY confidence DESC
    """, symbol, current_date)
    
    # 2. Manually filter
    high_confidence = [t for t in similar_trades if t['confidence'] > 0.7]
    
    # 3. Manually build prompt
    prompt = f"Based on these similar trades: {high_confidence}..."
    
    # 4. Call LLM
    return llm.call(prompt)
```

**Problems:**
- Must code every query pattern
- Hard to adapt to new scenarios
- No dynamic query generation
- Rigid workflow

### MCP Approach (Better)

```python
# Register MCP tools
@mcp_tool
def query_trade_decisions_db(symbol: str, date_range: str = "30d", 
                            min_confidence: float = 0.5,
                            filters: dict = None) -> List[dict]:
    """Query database for similar trade decisions"""
    # Tool implementation
    pass

@mcp_tool  
def find_pattern_matches(symbol: str, pattern_type: str) -> List[dict]:
    """Find historical patterns matching current situation"""
    pass

# LLM uses tools autonomously
decision = llm_agent.analyze(symbol)
# LLM internally:
# 1. "I should check DB for similar decisions"
#    → Calls query_trade_decisions_db(symbol, date_range="30d", min_confidence=0.7)
# 2. "I found 5 similar trades, let me check patterns"
#    → Calls find_pattern_matches(symbol, pattern_type="momentum")
# 3. "Based on results, I'll make decision"
#    → Returns decision
```

**Benefits:**
- ✅ LLM generates queries dynamically
- ✅ Can chain multiple queries
- ✅ Adapts to context
- ✅ No hardcoded workflows

---

## Example: DB Query System with MCP

### MCP Tools for Trade Decisions

```python
# MCP Server: Trade Decision Tools
tools = [
    {
        "name": "query_trade_decisions",
        "description": "Query database for historical trade decisions",
        "parameters": {
            "symbol": "Stock symbol to query",
            "date_range": "Time range (e.g., '30d', '90d')",
            "min_confidence": "Minimum confidence threshold",
            "action_type": "Filter by action (BUY, SELL, SHORT, etc.)",
            "similarity_threshold": "Similarity score threshold"
        }
    },
    {
        "name": "find_similar_patterns",
        "description": "Find historical patterns matching current market conditions",
        "parameters": {
            "symbol": "Stock symbol",
            "pattern_type": "Type of pattern (momentum, reversal, etc.)",
            "lookback_days": "Days to look back"
        }
    },
    {
        "name": "get_decision_statistics",
        "description": "Get statistics on decision performance",
        "parameters": {
            "symbol": "Stock symbol",
            "decision_type": "Type of decision",
            "time_period": "Time period for statistics"
        }
    }
]
```

### LLM Agent Usage

```python
# LLM agent with MCP tools
agent = MCPAgent(tools=tools)

# LLM autonomously uses tools
decision = agent.analyze(
    symbol="NVDA",
    current_date="2025-01-15",
    market_context="Bull market, tech sector strong"
)

# LLM's internal reasoning:
# 1. "I should check DB for similar NVDA decisions in bull markets"
#    → query_trade_decisions(symbol="NVDA", filters={"market": "bull"})
# 2. "Found 12 similar decisions, 8 were profitable"
#    → get_decision_statistics(symbol="NVDA", decision_type="BUY")
# 3. "Pattern shows momentum continuation in tech"
#    → find_similar_patterns(symbol="NVDA", pattern_type="momentum")
# 4. "Based on DB results, I'll recommend BUY with high confidence"
```

---

## Migration Path

### Phase 1: Add MCP Tools (Keep Current System)

```python
# Add MCP tools alongside current agents
class HybridSystem:
    def __init__(self):
        self.current_agents = CurrentAgentSystem()  # Keep existing
        self.mcp_tools = MCPToolRegistry()  # Add MCP
        
    def make_decision(self, symbol):
        # Option 1: Use current system
        if use_current:
            return self.current_agents.make_decision(symbol)
        
        # Option 2: Use MCP agent
        return self.mcp_agent.analyze(symbol)  # Uses MCP tools
```

### Phase 2: Register DB Tools

```python
# Register database query tools
@mcp_tool
def query_trade_decisions_db(symbol, **filters):
    """Query trade decisions database"""
    return db.query_trade_decisions(symbol, **filters)

@mcp_tool
def get_historical_performance(symbol, decision_type):
    """Get historical performance of decisions"""
    return db.get_performance(symbol, decision_type)
```

### Phase 3: LLM-Driven Decisions

```python
# LLM uses DB tools autonomously
decision = mcp_agent.analyze(symbol)
# LLM decides what queries to make based on context
```

---

## Why MCP for DB-Based System?

1. **Dynamic Queries**: LLM generates queries based on context, not hardcoded
2. **Query Chaining**: LLM can chain multiple queries based on results
3. **Context Awareness**: Maintains context across queries
4. **Adaptability**: Adapts query strategy per symbol/situation
5. **Discovery**: New DB tools can be added without code changes

---

## References

- **Rallies AI**: Uses MCP for agent tool discovery and orchestration
- **Scalar Field**: Uses MCP for their AI-powered trading terminal
- **Alpha Vantage MCP**: Example of MCP server for financial data
- **MCP Protocol**: https://modelcontextprotocol.io/

---

## Summary

**Current Approach:**
- Manual orchestration
- Explicit function calls
- Stateless
- Rigid workflows

**MCP Approach:**
- Agent-driven tool discovery
- Dynamic tool usage
- Stateful context
- Flexible workflows

**For DB-Based System:**
- MCP allows LLM to query DB dynamically
- Can chain queries based on context
- Adapts to different scenarios
- No hardcoded query patterns

