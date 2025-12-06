# Migration Guide: REST API to MCP

## Overview

This guide shows how to migrate from a rigid REST API framework to a flexible MCP-based agent framework.

---

## Current Architecture (REST API)

### Current Flow

```python
# Current: Manual orchestration
class ParallelOrchestrator:
    def _analyze_single_stock(self, symbol, current_date):
        # 1. Manually fetch data from each agent
        sentiment_data = self._get_latest_analysis(symbol, 'sentiment', current_date)
        valuation_data = self._get_latest_analysis(symbol, 'valuation', current_date)
        fundamental_data = self._get_latest_analysis(symbol, 'fundamental', current_date)
        
        # 2. Manually pass all data to ReasoningAgent
        reasoning_agent = ReasoningAgent(data_dir=self.data_dir)
        decision = reasoning_agent.make_decision(
            symbol, current_date,
            valuation_data, fundamental_data, sentiment_data
        )
        return decision
```

**Problems:**
- ❌ Manual orchestration (you control every step)
- ❌ Rigid workflow (hard to change)
- ❌ No context awareness
- ❌ Hard to extend (must modify code)

---

## Target Architecture (MCP)

### Target Flow

```python
# Target: Agent-driven tool-calling
class ToolCallingAgent:
    def analyze_stock(self, symbol, current_date):
        # Agent decides what tools to call
        # Agent maintains context
        # Agent chains operations dynamically
        
        decision = self.mcp_agent.analyze(
            symbol=symbol,
            date=current_date,
            context={}
        )
        return decision
```

**Benefits:**
- ✅ Autonomous (agent decides what to do)
- ✅ Flexible (can change workflow dynamically)
- ✅ Context-aware (maintains state)
- ✅ Extensible (add tools without code changes)

---

## Migration Strategy

### Phase 1: Set Up MCP Infrastructure (Week 1)

#### Step 1.1: Install MCP Dependencies

```bash
pip install mcp
# or
pip install anthropic-mcp
```

#### Step 1.2: Create MCP Server Structure

```python
# mcp_server/__init__.py
from mcp import Server

# Create MCP server
server = Server("stock-analysis-server")

# Register tools (we'll add these in next steps)
```

#### Step 1.3: Create Tool Registry

```python
# mcp_server/tool_registry.py
from typing import Dict, Callable
from mcp import Tool

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
    
    def register_tool(self, name: str, tool: Tool):
        """Register a tool with the MCP server"""
        self.tools[name] = tool
    
    def get_tool(self, name: str) -> Tool:
        """Get a tool by name"""
        return self.tools.get(name)
    
    def list_tools(self) -> list:
        """List all available tools"""
        return list(self.tools.keys())

# Global registry
tool_registry = ToolRegistry()
```

---

### Phase 2: Convert REST API Calls to MCP Tools (Week 2)

#### Step 2.1: Create Data Provider Tools

```python
# mcp_server/tools/data_provider_tools.py
from mcp import Tool
from typing import Dict, Any
import json
import os

# Your existing data fetching logic (keep this)
def get_fundamental_data(symbol: str, date: str) -> Dict[str, Any]:
    """Get fundamental analysis data for a symbol"""
    # This is your existing REST API call or file loading logic
    # Keep your current implementation, just wrap it
    analysis_dir = os.path.join(data_dir, "fundamental_test_reports")
    # ... your existing code ...
    return fundamental_data

def get_valuation_data(symbol: str, date: str) -> Dict[str, Any]:
    """Get valuation analysis data for a symbol"""
    # Wrap your existing REST API call
    analysis_dir = os.path.join(data_dir, "valuation_reports")
    # ... your existing code ...
    return valuation_data

def get_sentiment_data(symbol: str, date: str) -> Dict[str, Any]:
    """Get sentiment analysis data for a symbol"""
    # Wrap your existing REST API call
    analysis_dir = os.path.join(data_dir, "sentiment_data")
    # ... your existing code ...
    return sentiment_data

# Register as MCP tools
fundamental_tool = Tool(
    name="get_fundamental_data",
    description="Get fundamental analysis data (income statements, balance sheets, P/E, P/B ratios)",
    parameters={
        "type": "object",
        "properties": {
            "symbol": {"type": "string", "description": "Stock ticker symbol"},
            "date": {"type": "string", "description": "Analysis date (YYYY-MM-DD)"}
        },
        "required": ["symbol", "date"]
    },
    handler=get_fundamental_data
)

valuation_tool = Tool(
    name="get_valuation_data",
    description="Get valuation analysis data (price, RSI, MACD, moving averages)",
    parameters={
        "type": "object",
        "properties": {
            "symbol": {"type": "string", "description": "Stock ticker symbol"},
            "date": {"type": "string", "description": "Analysis date (YYYY-MM-DD)"}
        },
        "required": ["symbol", "date"]
    },
    handler=get_valuation_data
)

sentiment_tool = Tool(
    name="get_sentiment_data",
    description="Get sentiment analysis data (news articles, sentiment scores)",
    parameters={
        "type": "object",
        "properties": {
            "symbol": {"type": "string", "description": "Stock ticker symbol"},
            "date": {"type": "string", "description": "Analysis date (YYYY-MM-DD)"}
        },
        "required": ["symbol", "date"]
    },
    handler=get_sentiment_data
)
```

#### Step 2.2: Register Tools with MCP Server

```python
# mcp_server/server.py
from mcp import Server
from mcp_server.tools.data_provider_tools import (
    fundamental_tool, valuation_tool, sentiment_tool
)
from mcp_server.tool_registry import tool_registry

# Create MCP server
server = Server("stock-analysis-server")

# Register tools
server.register_tool(fundamental_tool)
server.register_tool(valuation_tool)
server.register_tool(sentiment_tool)

# Also register in our registry
tool_registry.register_tool("get_fundamental_data", fundamental_tool)
tool_registry.register_tool("get_valuation_data", valuation_tool)
tool_registry.register_tool("get_sentiment_data", sentiment_tool)
```

---

### Phase 3: Create Tool-Calling Agent (Week 3)

#### Step 3.1: Create MCP Client Wrapper

```python
# mcp_client/mcp_client.py
from mcp_server.tool_registry import tool_registry
from typing import Dict, Any, Optional

class MCPClient:
    """Wrapper for MCP tool calls"""
    
    def __init__(self, server):
        self.server = server
        self.tool_registry = tool_registry
    
    def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Call an MCP tool by name"""
        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool {tool_name} not found")
        
        # Execute tool handler
        return tool.handler(**kwargs)
    
    def list_tools(self) -> list:
        """List all available tools"""
        return self.tool_registry.list_tools()
```

#### Step 3.2: Create Tool-Calling Agent

```python
# agents/tool_calling_agent.py
from mcp_client.mcp_client import MCPClient
from typing import Dict, Any, Optional
import json

class ToolCallingAgent:
    """
    Agent that autonomously decides which tools to call
    based on context and requirements.
    """
    
    def __init__(self, mcp_client: MCPClient, llm_client):
        self.mcp_client = mcp_client
        self.llm_client = llm_client
        self.context = {}
    
    def analyze_stock(self, symbol: str, current_date: str) -> Dict[str, Any]:
        """
        Analyze a stock by letting the agent decide what tools to call.
        """
        # Step 1: Agent plans what tools it needs
        tool_plan = self._plan_tool_usage(symbol, current_date)
        
        # Step 2: Execute tool calls
        gathered_data = {}
        for tool_call in tool_plan:
            try:
                result = self.mcp_client.call_tool(
                    tool_call['tool_name'],
                    symbol=symbol,
                    date=current_date,
                    **tool_call.get('extra_params', {})
                )
                gathered_data[tool_call['tool_name']] = result
            except Exception as e:
                print(f"Error calling {tool_call['tool_name']}: {e}")
                gathered_data[tool_call['tool_name']] = None
        
        # Step 3: Feed gathered data to reasoning agent
        return self._reason_with_data(symbol, current_date, gathered_data)
    
    def _plan_tool_usage(self, symbol: str, date: str) -> list:
        """
        Use LLM to plan which tools to call.
        This replaces the manual orchestration.
        """
        available_tools = self.mcp_client.list_tools()
        
        prompt = f"""
        You are analyzing stock {symbol} on date {date}.
        
        Available tools:
        {json.dumps(available_tools, indent=2)}
        
        Plan which tools you need to call to analyze this stock.
        Return a JSON list of tool names you want to call.
        
        Example:
        ["get_fundamental_data", "get_valuation_data", "get_sentiment_data"]
        """
        
        response = self.llm_client.call(prompt)
        
        # Parse response to get tool list
        try:
            tool_list = json.loads(response)
            return [{"tool_name": tool} for tool in tool_list]
        except:
            # Fallback: use all tools
            return [
                {"tool_name": "get_fundamental_data"},
                {"tool_name": "get_valuation_data"},
                {"tool_name": "get_sentiment_data"}
            ]
    
    def _reason_with_data(self, symbol: str, date: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use reasoning agent with gathered data.
        This is your existing ReasoningAgent logic.
        """
        from ReasoningAgent import ReasoningAgent
        
        reasoning_agent = ReasoningAgent()
        
        # Extract data from gathered results
        fundamental_data = data.get("get_fundamental_data")
        valuation_data = data.get("get_valuation_data")
        sentiment_data = data.get("get_sentiment_data")
        
        # Call existing reasoning agent
        return reasoning_agent.make_decision(
            symbol=symbol,
            current_date=date,
            valuation_data=valuation_data,
            fundamental_data=fundamental_data,
            sentiment_data=sentiment_data
        )
```

---

### Phase 4: Update Orchestrator (Week 4)

#### Step 4.1: Update ParallelOrchestrator

```python
# ParallelOrchestrator.py (Updated)

# BEFORE (REST API):
def _analyze_single_stock(self, symbol, current_date, api_key):
    # Manual data fetching
    sentiment_data = self._get_latest_analysis(symbol, 'sentiment', current_date)
    valuation_data = self._get_latest_analysis(symbol, 'valuation', current_date)
    fundamental_data = self._get_latest_analysis(symbol, 'fundamental', current_date)
    
    # Manual orchestration
    reasoning_agent = ReasoningAgent(data_dir=self.data_dir, api_key_override=api_key)
    decision = reasoning_agent.make_decision(
        symbol, current_date, valuation_data, fundamental_data, sentiment_data
    )
    return decision

# AFTER (MCP):
def _analyze_single_stock(self, symbol, current_date, api_key):
    # Agent-driven tool-calling
    from agents.tool_calling_agent import ToolCallingAgent
    from mcp_client.mcp_client import MCPClient
    
    # Initialize MCP client
    mcp_client = MCPClient(self.mcp_server)
    
    # Initialize tool-calling agent
    tool_agent = ToolCallingAgent(
        mcp_client=mcp_client,
        llm_client=self._get_llm_client(api_key)
    )
    
    # Agent decides what tools to call and analyzes
    decision = tool_agent.analyze_stock(symbol, current_date)
    return decision
```

---

## Migration Checklist

### Week 1: Infrastructure
- [ ] Install MCP dependencies
- [ ] Create MCP server structure
- [ ] Create tool registry
- [ ] Set up basic MCP server

### Week 2: Convert Tools
- [ ] Convert `get_fundamental_data` to MCP tool
- [ ] Convert `get_valuation_data` to MCP tool
- [ ] Convert `get_sentiment_data` to MCP tool
- [ ] Register all tools with MCP server
- [ ] Test tool calls manually

### Week 3: Create Agent
- [ ] Create MCP client wrapper
- [ ] Create tool-calling agent
- [ ] Implement tool planning logic
- [ ] Integrate with existing ReasoningAgent
- [ ] Test agent tool-calling

### Week 4: Integration
- [ ] Update ParallelOrchestrator
- [ ] Replace manual orchestration with agent
- [ ] Test end-to-end flow
- [ ] Add error handling
- [ ] Add fallback mechanisms

---

## Code Examples: Before vs After

### Example 1: Data Fetching

#### BEFORE (REST API):
```python
# Manual orchestration
def _analyze_single_stock(self, symbol, current_date):
    # Step 1: Manually fetch each data type
    sentiment_data = self._get_latest_analysis(symbol, 'sentiment', current_date)
    valuation_data = self._get_latest_analysis(symbol, 'valuation', current_date)
    fundamental_data = self._get_latest_analysis(symbol, 'fundamental', current_date)
    
    # Step 2: Manually pass to reasoning agent
    reasoning_agent = ReasoningAgent()
    decision = reasoning_agent.make_decision(
        symbol, current_date,
        valuation_data, fundamental_data, sentiment_data
    )
    return decision
```

#### AFTER (MCP):
```python
# Agent-driven
def _analyze_single_stock(self, symbol, current_date):
    # Agent decides what to fetch
    tool_agent = ToolCallingAgent(mcp_client, llm_client)
    decision = tool_agent.analyze_stock(symbol, current_date)
    return decision
```

---

### Example 2: Adding New Data Source

#### BEFORE (REST API):
```python
# Must modify orchestrator code
def _analyze_single_stock(self, symbol, current_date):
    sentiment_data = self._get_latest_analysis(symbol, 'sentiment', current_date)
    valuation_data = self._get_latest_analysis(symbol, 'valuation', current_date)
    fundamental_data = self._get_latest_analysis(symbol, 'fundamental', current_date)
    
    # NEW: Must add here
    alternative_data = self._get_alternative_data(symbol, current_date)  # New code
    
    reasoning_agent = ReasoningAgent()
    decision = reasoning_agent.make_decision(
        symbol, current_date,
        valuation_data, fundamental_data, sentiment_data,
        alternative_data  # Must update signature
    )
    return decision
```

#### AFTER (MCP):
```python
# Just register new tool, no code changes needed
# 1. Create tool
alternative_tool = Tool(
    name="get_alternative_data",
    handler=get_alternative_data
)

# 2. Register tool
server.register_tool(alternative_tool)

# 3. Agent automatically discovers and uses it
# No orchestrator changes needed!
```

---

## Gradual Migration Strategy

### Option 1: Side-by-Side (Recommended)

Keep REST API working while building MCP:

```python
class ParallelOrchestrator:
    def __init__(self, use_mcp=False):
        self.use_mcp = use_mcp
        if use_mcp:
            self.mcp_server = self._setup_mcp_server()
    
    def _analyze_single_stock(self, symbol, current_date, api_key):
        if self.use_mcp:
            # New MCP path
            return self._analyze_with_mcp(symbol, current_date, api_key)
        else:
            # Old REST API path (keep working)
            return self._analyze_with_rest_api(symbol, current_date, api_key)
```

**Benefits:**
- ✅ Can test MCP without breaking existing system
- ✅ Can migrate gradually
- ✅ Can rollback if issues

---

### Option 2: Tool-by-Tool Migration

Migrate one tool at a time:

```python
# Week 1: Migrate fundamental data
fundamental_data = self.mcp_client.call_tool("get_fundamental_data", symbol, date)
# Keep rest as REST API

# Week 2: Migrate valuation data
valuation_data = self.mcp_client.call_tool("get_valuation_data", symbol, date)
# Keep sentiment as REST API

# Week 3: Migrate sentiment data
sentiment_data = self.mcp_client.call_tool("get_sentiment_data", symbol, date)
# All migrated!
```

---

## Testing Strategy

### Step 1: Test Tools Individually

```python
# Test each tool works
def test_fundamental_tool():
    mcp_client = MCPClient(server)
    result = mcp_client.call_tool("get_fundamental_data", symbol="AAPL", date="2025-01-01")
    assert result is not None

def test_valuation_tool():
    mcp_client = MCPClient(server)
    result = mcp_client.call_tool("get_valuation_data", symbol="AAPL", date="2025-01-01")
    assert result is not None
```

### Step 2: Test Agent Tool-Calling

```python
# Test agent can call tools
def test_tool_calling_agent():
    agent = ToolCallingAgent(mcp_client, llm_client)
    decision = agent.analyze_stock("AAPL", "2025-01-01")
    assert decision is not None
```

### Step 3: Test End-to-End

```python
# Test full flow
def test_end_to_end():
    orchestrator = ParallelOrchestrator(use_mcp=True)
    decision = orchestrator._analyze_single_stock("AAPL", "2025-01-01", api_key)
    assert decision is not None
```

---

## Common Pitfalls & Solutions

### Pitfall 1: Agent Calls Wrong Tools

**Solution**: Add tool validation

```python
def _plan_tool_usage(self, symbol, date):
    tool_plan = self.llm_client.plan_tools(...)
    
    # Validate tools exist
    available_tools = self.mcp_client.list_tools()
    validated_plan = [
        tool for tool in tool_plan 
        if tool['tool_name'] in available_tools
    ]
    
    return validated_plan
```

### Pitfall 2: Tool Calls Fail

**Solution**: Add fallback mechanisms

```python
def analyze_stock(self, symbol, date):
    try:
        # Try MCP path
        return self._analyze_with_mcp(symbol, date)
    except Exception as e:
        # Fallback to REST API
        print(f"MCP failed, falling back to REST API: {e}")
        return self._analyze_with_rest_api(symbol, date)
```

### Pitfall 3: Context Loss

**Solution**: Maintain context across calls

```python
class ToolCallingAgent:
    def __init__(self):
        self.context = {}
    
    def analyze_stock(self, symbol, date):
        # Store context
        self.context['symbol'] = symbol
        self.context['date'] = date
        
        # Use context in tool calls
        result = self.mcp_client.call_tool("get_fundamental_data", **self.context)
        
        # Update context with results
        self.context['fundamental_data'] = result
```

---

## Summary

### Migration Steps:
1. **Week 1**: Set up MCP infrastructure
2. **Week 2**: Convert REST API calls to MCP tools
3. **Week 3**: Create tool-calling agent
4. **Week 4**: Update orchestrator

### Key Changes:
- ✅ Manual orchestration → Agent-driven tool-calling
- ✅ Fixed workflow → Dynamic tool selection
- ✅ Code changes for new tools → Just register new tool
- ✅ No context → Context-aware

### Benefits:
- ✅ More flexible
- ✅ Easier to extend
- ✅ Better architecture
- ✅ Future-proof

**Total Migration Time**: 4 weeks


