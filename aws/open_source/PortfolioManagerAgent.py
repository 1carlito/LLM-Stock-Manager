"""
PortfolioManagerAgent.py: Portfolio-level decision maker that allocates capital across stocks
based on individual stock decisions and portfolio constraints.
"""

import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv
import requests
import re
import math
from typing import List, Dict, Any

# Load environment variables from .env in the same directory as this script
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(dotenv_path=env_path)

CHUTES_API_URL = os.getenv("CHUTES_API_URL", "https://llm.chutes.ai/v1/chat/completions")
DEFAULT_PORTFOLIO_TOKEN = os.getenv("PORTFOLIO_CHUTES_DEEPSEEK_API_KEY")

class PortfolioManagerAgent:
    """
    Portfolio Manager that uses a Waterfall Allocation method to ensure 
    cash constraints are strictly respected.
    """
    
    def __init__(self, data_dir=".", api_key=None): 
        self.data_dir = data_dir
        self.portfolio_save_dir = os.path.join(self.data_dir, "portfolio_decisions_DSeek_2.0")
        
        # Use provided API key or load from environment
        # Portfolio Manager only needs ONE key since it runs sequentially (not in parallel)
        self.api_key = api_key or DEFAULT_PORTFOLIO_TOKEN
        if not self.api_key:
            raise ValueError(
                "No Chutes API token found. Pass api_key or set PORTFOLIO_CHUTES_DEEPSEEK_API_KEY in the environment."
            )
        
        self.model_name = "deepseek-ai/DeepSeek-V3.1-Terminus"
        
        os.makedirs(self.portfolio_save_dir, exist_ok=True)
        print(f"✅ PortfolioManagerAgent initialized with {self.model_name}")
    
    def _build_portfolio_prompt(self, stock_decisions, portfolio_state, current_date, previous_portfolio_decisions=None):
        """Build prompt for portfolio-level decision making"""
        
        # Calculate portfolio metrics
        total_value = portfolio_state.get('total_value', portfolio_state.get('cash', 0))
        cash = portfolio_state.get('cash', 0)
        positions = portfolio_state.get('positions', {})
        last_prices = portfolio_state.get('last_prices', {})
        short_positions = portfolio_state.get('short_positions', {})
        initial_value = portfolio_state.get('initial_value', 100000)  # Default to $100k if not provided
        
        # Calculate current total return percentage
        total_return_pct = ((total_value - initial_value) / initial_value) * 100 if initial_value > 0 else 0
        
        # Calculate position values and unrealized PnL for long positions
        position_values = {}
        total_unrealized_pnl = 0
        
        for symbol, pos in positions.items():
            if pos.get('shares', 0) > 0:
                # Get current price from last_prices (should be updated daily)
                # If not available, skip P&L calculation (price not updated)
                current_price = last_prices.get(symbol, 0)
                if current_price <= 0:
                    # Fallback to avg_price only for position_value display, but P&L will be 0
                    current_price = pos.get('avg_price', 0)
                
                position_value = pos['shares'] * current_price
                cost_basis = pos['shares'] * pos.get('avg_price', 0)
                
                # Only calculate P&L if we have a current price that's different from avg_price
                # (indicates price was updated)
                if current_price > 0 and current_price != pos.get('avg_price', 0):
                    unrealized_pnl = position_value - cost_basis
                else:
                    unrealized_pnl = 0  # Price not updated, can't calculate P&L
                
                total_unrealized_pnl += unrealized_pnl
                
                position_values[symbol] = {
                    'shares': pos['shares'],
                    'current_price': current_price,
                    'avg_price': pos.get('avg_price', current_price),
                    'cost_basis': cost_basis,
                    'value': position_value,
                    'unrealized_pnl': unrealized_pnl,
                    'pct_of_portfolio': (position_value / total_value * 100) if total_value > 0 else 0
                }
        
        # Calculate short position details
        # IMPORTANT: For CFD model, short notional is the collateral tied up at ENTRY price
        # The current price only affects P&L, not the notional amount locked up
        short_position_values = {}
        total_short_unrealized_pnl = 0
        total_short_notional_locked = 0  # Track total notional locked as collateral
        for symbol, short_pos in short_positions.items():
            if short_pos.get('shares', 0) > 0:
                # Get current price from last_prices (should be updated daily)
                current_price = last_prices.get(symbol, 0)
                
                # Entry price is the avg_price at which the short was entered
                entry_price = short_pos.get('avg_price', 0)
                
                # If no current price in last_prices, fallback to avg_price for P&L calculation
                if current_price <= 0:
                    current_price = entry_price
                
                # NOTIONAL: The collateral locked up at entry (this is what was deducted from cash)
                # For CFD model, this is based on ENTRY price, not current price
                notional_value_at_entry = short_pos['shares'] * entry_price
                total_short_notional_locked += notional_value_at_entry
                
                # Current notional exposure (for display purposes, based on current market price)
                current_notional_exposure = short_pos['shares'] * current_price
                
                # Calculate P&L: profit when price goes DOWN (entry_price > current_price)
                if entry_price > 0 and current_price > 0:
                    # Short P&L = (Entry Price - Current Price) * Shares
                    short_pnl = (entry_price - current_price) * short_pos['shares']
                else:
                    # Can't calculate P&L if prices are missing
                    short_pnl = 0
                
                total_short_unrealized_pnl += short_pnl
                
                short_position_values[symbol] = {
                    'shares': short_pos['shares'],
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'notional_at_entry': notional_value_at_entry,  # Collateral locked up
                    'current_notional_exposure': current_notional_exposure,  # Current market exposure
                    'unrealized_pnl': short_pnl
                }
        
        # Build current stock prices section
        current_prices_section = "\nCURRENT STOCK PRICES:\n"
        for symbol in sorted(set(list(last_prices.keys()) + [d.get('symbol') for d in stock_decisions if d.get('symbol')])):
            price = last_prices.get(symbol, 'N/A')
            if price != 'N/A':
                current_prices_section += f"- {symbol}: ${price:,.2f}\n"
        
        prompt = f"""
You are the highest level Portfolio Manager in existence making final allocation decisions for a trading portfolio on {current_date}. Optimize for returns; do not apply conservative cash buffers unless the data clearly warrants it.

CURRENT PORTFOLIO PERFORMANCE:
- Current Total Return (percent): {total_return_pct:.2f}%
- Total Portfolio Value: ${total_value:,.2f}
- Available Cash: ${cash:,.2f}
- Cash Percentage: {(cash/total_value*100) if total_value > 0 else 0:.1f}%
- Total Unrealized PnL (Long): ${total_unrealized_pnl:,.2f}
- Total Unrealized PnL (Short): ${total_short_unrealized_pnl:,.2f}
- Short Notional Locked (Collateral at Entry): ${total_short_notional_locked:,.2f}

IMPORTANT CASH ACCOUNTING:
- Cash = Initial Capital - Long Positions Cost Basis - Short Notional Locked - Spread Fees Paid - Overnight Fees Paid
- Short Notional represents collateral tied up at ENTRY prices (based on avg_price in short_positions)
- Unrealized PnL on shorts affects portfolio value but doesn't change cash until position is closed
- When allocating for SHORT actions, remember that cash will be deducted: Notional Amount + Entry Spread Fee

{current_prices_section}

CURRENT LONG POSITIONS:
{json.dumps(position_values, indent=2) if position_values else "No current long positions"}

CURRENT SHORT POSITIONS:
{json.dumps(short_position_values, indent=2) if short_position_values else "No current short positions"}

CASH BALANCE: ${cash:,.2f}

CURRENT PRICES (per symbol):
{json.dumps(last_prices, indent=2)}

INDIVIDUAL STOCK DECISIONS:
{json.dumps(stock_decisions, indent=2)}

NOTE: For SELL decisions, the ReasoningAgent may include a 'short_confidence' field (0-1) indicating confidence in shorting this stock if it's not owned. Use this to inform your SHORT allocation decisions.
"""
        
        # Add previous portfolio decisions if available
        if previous_portfolio_decisions and len(previous_portfolio_decisions) > 0:
            prompt += f"""
PREVIOUS PORTFOLIO ALLOCATION DECISIONS:
{json.dumps(previous_portfolio_decisions, indent=2)}

Review these previous allocation decisions to understand the portfolio's recent trading history. Consider:
- Whether previous allocations achieved their intended portfolio weights
- How the portfolio evolved through these previous decisions
- Any patterns in position sizing or trading activity
- Current vs. target allocations based on recent history
"""
        
        prompt += f"""
YOUR TASK:
Analyze ALL individual stock decisions and make portfolio-level allocation decisions.

CRITICAL REQUIREMENT: You MUST return a portfolio decision for EVERY stock in the INDIVIDUAL STOCK DECISIONS list above. 
- If a stock should have no action (e.g., NEUTRAL/MAINTAIN for unowned stocks), still include it with action "NEUTRAL" or "MAINTAIN" and amount_usd: 0
- Do NOT skip any stocks - all {len(stock_decisions)} stocks must appear in your portfolio_decisions array 



CRITICAL DECISION RULES:
1. BUY decisions: Allocate capital based on confidence and available cash
2. SELL decisions on OWNED stocks: Close or reduce long positions
3. SELL decisions on UNOWNED stocks: Convert to SHORT action (this is a short selling opportunity)
4. NEUTRAL: Signals are mixed/neutral, no edge found
   - If stock is OWNED: Consider closing position if capital is needed elsewhere for better opportunities
   - If stock is NOT OWNED: Ignore, no action taken
5. MAINTAIN: Thesis intact, but not enough new edge to add
   - If stock is OWNED: Keep position, do NOT add more shares
   - If stock is NOT OWNED: Ignore, no action taken

Long Position Guidelines:
- You may fully deploy capital on high conviction; no fixed cash buffer is required.
- Individual positions can be sized up to 25% of available cash at maximum conviction.
- Favor deploying capital on high-confidence signals; do not throttle allocations due to generic risk aversion.
- Scale position sizes by confidence and available capital.


Short Selling Guidelines:
- When ReasoningAgent outputs SELL for a stock NOT currently owned, convert this to SHORT action
- When the available cash is less than 25% of the initial value (25,000), Do Not Open any new CFD Short Positions.
- Maximum short allocation per position: 25% of Available Cash (and may be further limited by per-stock cap)
- Scale position sizes by confidence and available capital
- Holding period is FLEXIBLE: You can extend short positions by outputting SHORT or HOLD actions
- Target close dates can be updated based on your decisions 
- Default initial holding period: 7 days (but can be extended indefinitely via new decisions)

DECISION LOGIC:
- If stock decision is BUY → Use BUY action
- If stock decision is SELL AND we own the stock → Use SELL action (close long)
- If stock decision is SELL AND we DON'T own the stock → Use SHORT action (open short)
- If stock decision is NEUTRAL:
  - If we own the stock (long or short) → Consider closing if capital needed, otherwise HOLD
  - If we DON'T own the stock → No action, ignore this decision
- If stock decision is MAINTAIN:
  - If we own the stock (long or short) → Keep position, extend short target dates, do NOT add more
  - If we DON'T own the stock → No action, ignore this decision
- For existing short positions: MAINTAIN or NEUTRAL actions will extend the target close date (flexible holding)
- Only close shorts explicitly via COVER/CLOSE_SHORT actions or when exceeding maximum holding period

RISK MANAGEMENT (PRAGMATIC):
- Do not allocate more than available cash.
- Avoid obvious over-concentration in highly correlated names when multiple high-conviction signals compete.
- Consider current position sizes before adding.



RESPONSE FORMAT:
You MUST provide a portfolio decision for EVERY stock in the INDIVIDUAL STOCK DECISIONS list above. Include all {len(stock_decisions)} stocks in your portfolio_decisions array.

For each stock, provide your allocation decision in this JSON format.
IMPORTANT: 
- The "symbol" field MUST be a real stock ticker from the INDIVIDUAL STOCK DECISIONS list above - never create fictional symbols
- You MUST include ALL stocks from the input list, even if the action is NEUTRAL with amount_usd: 0

{{
  "portfolio_decisions": [
    {{
      "symbol": "AAPL",
      "action": "BUY|SELL|SHORT|COVER|NEUTRAL|MAINTAIN",
      "amount_usd": 50000.00,
      "reasoning": "Brief explanation of position sizing rationale",
      "portfolio_weight_target": 15.5
    }},
    ...
  ],
  "portfolio_summary": {{
    "total_allocation": 750000.00,
    "cash_reserved": 250000.00,
    "risk_assessment": "Brief overall risk assessment",
    "strategy_notes": "Key considerations for this allocation"
  }}
}}

IMPORTANT:
- Be decisive; prioritize return maximization with sensible safeguards.
- Ensure total allocations don't exceed available cash.
- Provide clear reasoning for each position size.
- Do NOT suggest new symbols that are not in the INDIVIDUAL STOCK DECISIONS list above.
"""
        
        return prompt
    
    def _call_chutes_api(self, prompt: str, user_prompt: str) -> str:
        """Make call to Chutes DeepSeek API"""
        body = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "max_tokens": 3800,
            "temperature": 0.7,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Retry logic with exponential backoff for rate limiting (429), service unavailable (503), and timeouts
        max_retries = 5
        base_delay = 5.0  # Start with 5 second delay for portfolio manager
        time.sleep(3.0)  # Initial delay before first API call
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    CHUTES_API_URL,
                    headers=headers,
                    json=body,
                    timeout=240,  # Increased timeout to 240 seconds
                )
                
                # Check for rate limit (429) or service unavailable (503)
                if response.status_code in [429, 503]:
                    if attempt < max_retries - 1:
                        # Exponential backoff: 5s, 10s, 20s, 40s, 80s
                        delay = base_delay * (2 ** attempt)
                        status_msg = "rate limited (429)" if response.status_code == 429 else "service unavailable (503)"
                        print(f"⚠️ {status_msg} for Portfolio Manager, retrying in {delay:.1f}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        response.raise_for_status()
                else:
                    response.raise_for_status()
                    break  # Success, exit retry loop
                    
            except requests.Timeout as exc:
                # Handle timeout errors
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    print(f"⚠️ Timeout for Portfolio Manager, retrying in {delay:.1f}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    raise RuntimeError(f"Chutes API request timed out after {max_retries} attempts: {exc}") from exc
            except requests.RequestException as exc:
                # Check if it's a 429 or 503 error
                status_code = None
                if hasattr(exc, 'response') and exc.response is not None:
                    status_code = exc.response.status_code
                
                if status_code in [429, 503] and attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    status_msg = "rate limited (429)" if status_code == 429 else "service unavailable (503)"
                    print(f"⚠️ {status_msg} for Portfolio Manager, retrying in {delay:.1f}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                elif attempt == max_retries - 1:
                    raise RuntimeError(f"Chutes API request failed after {max_retries} attempts: {exc}") from exc
                else:
                    raise RuntimeError(f"Chutes API request failed: {exc}") from exc

        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected Chutes response format: {data}") from exc

    def get_portfolio_decisions(self, stock_decisions: List[Dict[str, Any]], portfolio_state: Dict[str, Any], current_date: str, previous_portfolio_decisions=None) -> Dict[str, Any]:
        """
        Single-threaded portfolio allocation with waterfall allocation logic.
        """
        print(f"📢 Portfolio Manager allocating capital for {current_date}...")
        print(f"📊 Received {len(stock_decisions)} stock decisions: {[d.get('symbol') for d in stock_decisions]}")
        
        # Build prompt
        prompt = self._build_portfolio_prompt(stock_decisions, portfolio_state, current_date, previous_portfolio_decisions)
        user_prompt = "Generate the JSON output based on the provided instructions, stock decisions, and portfolio state."
        
        # Make single API call
        try:
            print(f"📊 Calling Chutes DeepSeek API for portfolio allocation covering {len(stock_decisions)} stock decisions...")
            response_text = self._call_chutes_api(prompt, user_prompt)
            print(f"✅ Got DeepSeek Portfolio response")
            
            parsed_result = self._parse_portfolio_response(response_text, stock_decisions, portfolio_state, current_date)
            
            # Apply waterfall allocation to enforce strict cash constraints
            if parsed_result and 'portfolio_decisions' in parsed_result:
                portfolio_decisions_list = parsed_result['portfolio_decisions']
                # Update portfolio_state with cash for waterfall calculation
                waterfall_decisions = self._waterfall_allocation(
                    portfolio_decisions_list, 
                    portfolio_state, 
                    stock_decisions
                )
                parsed_result['portfolio_decisions'] = waterfall_decisions
            
            # Save portfolio decision to file
            if parsed_result:
                self._save_portfolio_decision(parsed_result)
            
            return parsed_result
            
        except Exception as e:
            print(f"❌ DeepSeek API Error in Portfolio Manager: {e}")
            raise RuntimeError("PortfolioManager waterfall allocation failed - no fallback allowed under strict mode.")

    def _parse_portfolio_response(self, response_text, stock_decisions, portfolio_state, current_date):
        """Parse the portfolio manager's response"""
        try:
            # Try to extract JSON from response with robust error handling
            import re
            import json
            
            json_str = None
            
            # Method 1: Try to find JSON in code blocks (```json ... ``` or ``` ... ```)
            code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if code_block_match:
                json_str = code_block_match.group(1)
                print("📋 Found JSON in code block")
            
            # Method 2: Try to find JSON object with balanced braces
            if not json_str:
                # Find the first { and then match balanced braces
                brace_count = 0
                start_idx = response_text.find('{')
                if start_idx != -1:
                    for i in range(start_idx, len(response_text)):
                        if response_text[i] == '{':
                            brace_count += 1
                        elif response_text[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_str = response_text[start_idx:i+1]
                                print("📋 Found JSON with balanced braces")
                                break
            
            # Method 3: Fallback to simple regex (original method)
            if not json_str:
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    print("📋 Found JSON with regex fallback")
            
            if json_str:
                
                # Comprehensive JSON cleanup function
                def cleanup_json(json_text):
                    """Clean up common JSON formatting issues from LLM responses"""
                    # Step 0: Remove markdown code block markers if still present
                    json_text = re.sub(r'^```(?:json)?\s*', '', json_text, flags=re.MULTILINE)
                    json_text = re.sub(r'```\s*$', '', json_text, flags=re.MULTILINE)
                    
                    # Step 1: Remove dollar signs from numeric values (e.g., "$575002.97" -> "575002.97")
                    # Match: colon, optional whitespace, dollar sign, then digits
                    json_text = re.sub(r':\s*\$(\d+(?:,\d+)*(?:\.\d+)?)', r': \1', json_text)
                    
                    # Step 2: Remove commas from numbers (e.g., "1215,031.80" -> "1215031.80")
                    # Handle multiple commas in a single number (e.g., "1,234,567.89" -> "1234567.89")
                    # Apply multiple times to handle numbers with multiple commas
                    prev_text = None
                    iterations = 0
                    while prev_text != json_text and iterations < 10:  # Limit iterations
                        prev_text = json_text
                        iterations += 1
                        # Match: digits, comma, then more digits (with optional decimal at end)
                        # But be careful not to match commas in strings - only match in numeric contexts
                        json_text = re.sub(r'(\d+),(\d+)', r'\1\2', json_text)
                    
                    # Step 3: Fix unquoted property names (add quotes if missing)
                    # Match property names that appear after { or , and before :
                    # Only quote if they're not already quoted
                    def quote_property_name(match):
                        prefix = match.group(1)  # { or ,
                        prop_name = match.group(2)  # the property name
                        # Only quote if they're not already quoted and not a number
                        if not prop_name.startswith('"') and not prop_name[0].isdigit():
                            return f'{prefix}"{prop_name}":'
                        return match.group(0)  # Already quoted, leave as is
                    
                    # Match: ({ or ,) + (optional whitespace) + (word chars) + :
                    # This safely matches property names in JSON structure
                    json_text = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', quote_property_name, json_text)
                    
                    # Step 4: Remove trailing commas (but not in strings)
                    json_text = re.sub(r',\s*}', '}', json_text)
                    json_text = re.sub(r',\s*]', ']', json_text)
                    
                    # Step 5: Fix escaped quotes in strings (ensure proper escaping)
                    # This is tricky - we'll be conservative and only fix obvious issues
                    
                    # Step 6: Remove control characters (keep newlines, tabs, carriage returns)
                    json_text = ''.join(char for char in json_text if ord(char) >= 32 or char in '\n\r\t')
                    
                    return json_text
                
                # Apply initial cleanup
                json_str_original = json_str
                json_str = cleanup_json(json_str)
                
                # Try to parse JSON with error handling
                try:
                    portfolio_decisions = json.loads(json_str)
                    print(f"✅ Successfully parsed JSON response")
                except json.JSONDecodeError as e:
                    # Try to fix common JSON issues with more aggressive cleanup
                    print(f"⚠️ JSON parse error: {e} at line {e.lineno}, column {e.colno}")
                    
                    # Show the problematic section for debugging
                    lines = json_str.split('\n')
                    if e.lineno <= len(lines):
                        problem_line = lines[e.lineno - 1]
                        start_col = max(0, e.colno - 50)
                        end_col = min(len(problem_line), e.colno + 50)
                        print(f"   Problem area: ...{problem_line[start_col:end_col]}...")
                        print(f"   Full problem line ({e.lineno}): {problem_line}")
                    
                    # Apply cleanup again (sometimes fixes are cumulative)
                    json_str = cleanup_json(json_str)
                    
                    try:
                        portfolio_decisions = json.loads(json_str)
                        print("✅ JSON parsing succeeded after cleanup")
                    except json.JSONDecodeError as e2:
                        print(f"⚠️ JSON parse still failed after cleanup: {e2}")
                        # Show raw response snippet for debugging (first 500 chars and last 500 chars)
                        print(f"   Raw response preview (first 500 chars): {response_text[:500]}")
                        print(f"   Raw response preview (last 500 chars): {response_text[-500:]}")
                        # Also show the problematic JSON section
                        print(f"   Extracted JSON (first 1000 chars): {json_str[:1000]}...")
                        if len(json_str) > 1000:
                            print(f"   Extracted JSON (last 500 chars): ...{json_str[-500:]}")
                        print(f"⚠️ Using fallback allocation due to JSON parsing failure")
                        return self._fallback_allocation(stock_decisions, portfolio_state, current_date)
            else:
                # Fallback to default allocation
                print("⚠️ Could not find JSON block in Portfolio Manager response")
                print(f"   Response preview (first 500 chars): {response_text[:500]}")
                print(f"   Response preview (last 500 chars): {response_text[-500:]}")
                print("⚠️ Using fallback allocation")
                return self._fallback_allocation(stock_decisions, portfolio_state, current_date)
            
            # Validate and normalize the decisions
            decisions_list = portfolio_decisions.get('portfolio_decisions', [])
            portfolio_summary = portfolio_decisions.get('portfolio_summary', {})
            
            print(f"📋 LLM returned {len(decisions_list)} portfolio decisions")
            if decisions_list:
                print(f"   Symbols from LLM: {[d.get('symbol') for d in decisions_list if d.get('symbol')]}")
            
            # Get valid symbols from stock_decisions and existing positions to validate against
            stock_decision_symbols = {d.get('symbol') for d in stock_decisions if d.get('symbol')}
            print(f"📋 Valid symbols from stock_decisions: {sorted(stock_decision_symbols)}")
            
            positions = portfolio_state.get('positions', {})
            short_positions = portfolio_state.get('short_positions', {})
            
            # Also allow symbols from existing positions (for SELL/COVER actions)
            valid_symbols = stock_decision_symbols.copy()
            valid_symbols.update(positions.keys())
            valid_symbols.update(short_positions.keys())
            
            # Check for missing stocks (only check stocks from stock_decisions, not positions)
            llm_symbols = {d.get('symbol') for d in decisions_list if d.get('symbol')}
            missing_symbols = stock_decision_symbols - llm_symbols
            if missing_symbols:
                print(f"⚠️ WARNING: LLM did not return decisions for {len(missing_symbols)} stocks: {sorted(missing_symbols)}")
                print(f"   Adding missing stocks with NEUTRAL decisions (no action)")
                
                # Add missing stocks with appropriate default decisions
                for symbol in missing_symbols:
                    owns_stock = symbol in positions and positions[symbol].get('shares', 0) > 0
                    has_short = symbol in short_positions and short_positions[symbol].get('shares', 0) > 0
                    
                    if owns_stock or has_short:
                        decisions_list.append({
                            'symbol': symbol,
                            'action': 'MAINTAIN',
                            'amount_usd': 0,
                            'reasoning': 'Missing from LLM response - maintaining existing position',
                            'portfolio_weight_target': 0
                        })
                    else:
                        decisions_list.append({
                            'symbol': symbol,
                            'action': 'NEUTRAL',
                            'amount_usd': 0,
                            'reasoning': 'Missing from LLM response - no action taken',
                            'portfolio_weight_target': 0
                        })
            positions = portfolio_state.get('positions', {})
            short_positions = portfolio_state.get('short_positions', {})
            
            # Also allow symbols from existing positions (for SELL/COVER actions)
            valid_symbols.update(positions.keys())
            valid_symbols.update(short_positions.keys())
            
            processed_decisions = []
            
            for decision in decisions_list:
                symbol = decision.get('symbol')
                action = decision.get('action', '')
                # If action is an int (malformed response), fallback to NEUTRAL
                if isinstance(action, int):
                    action = 'NEUTRAL'
                    decision['action'] = 'NEUTRAL'
                else:
                    action = str(action).upper() if action else ''
                
                # VALIDATE: Reject invalid symbols (e.g., "NEW_OPPORTUNITY" hallucinated by LLM)
                if not isinstance(symbol, str) or not symbol.strip():
                    print(f"⚠️ Rejecting decision with missing/invalid symbol: {decision}")
                    continue  # Only skip if symbol is actually blank or malformed
                
                if symbol not in valid_symbols:
                    # No more warnings or rejections for symbols; only skip if symbol is actually blank or malformed.
                    pass # Removed print(f"⚠️ Rejecting invalid symbol '{symbol}' from Portfolio Manager (not in stock_decisions or existing positions). Valid symbols: {', '.join(sorted(valid_symbols))}")
                
                # Check if we own the stock
                owns_stock = symbol in positions and positions[symbol].get('shares', 0) > 0
                has_short = symbol in short_positions and short_positions[symbol].get('shares', 0) > 0
                
                if action == 'SELL':
                    if owns_stock:
                        # We own it - keep as SELL to close long position
                        processed_decisions.append(decision)
                    else:
                        # Don't own it - convert to SHORT (but check if we already have a short)
                        if has_short:
                            # Already have short - convert to MAINTAIN to maintain/extend short
                            decision['action'] = 'MAINTAIN'
                            decision['reasoning'] = f"Maintaining existing short position: {decision.get('reasoning', '')}"
                            print(f"🔄 Converted SELL to MAINTAIN for {symbol} (already have short position)")
                        else:
                            # Convert to SHORT
                            decision['action'] = 'SHORT'
                            # Use short_confidence from ReasoningAgent if available
                            original_decision = next((d for d in stock_decisions if d.get('symbol') == symbol), None)
                            short_conf = original_decision.get('short_confidence') if original_decision else None
                            if short_conf:
                                decision['short_confidence'] = short_conf
                                # Adjust amount_usd based on short_confidence if not already set
                                if decision.get('amount_usd', 0) == 0:
                                    # Use short_confidence to scale allocation
                                    total_value = portfolio_state.get('total_value', 0)
                                    base_allocation = total_value * 0.05 * short_conf  # 5% base * short_confidence
                                    decision['amount_usd'] = base_allocation
                            decision['reasoning'] = f"Converted SELL to SHORT (stock not owned, short_confidence: {short_conf if short_conf else 'N/A'}): {decision.get('reasoning', '')}"
                            print(f"🔄 Converted SELL to SHORT for {symbol} (stock not owned, short_confidence: {short_conf if short_conf else 'N/A'})")
                        processed_decisions.append(decision)
                
                elif action == 'SHORT':
                    # If we own the stock, allow SHORT - execution layer will auto-sell first, then short
                    if owns_stock:
                        print(f"ℹ️ SHORT {symbol} requested on owned stock - will auto-sell long position first, then short")
                        # Keep as SHORT - execution layer will handle selling first
                        processed_decisions.append(decision)
                    elif has_short:
                        # Already have short - keep as SHORT to add to position or extend
                        processed_decisions.append(decision)
                    else:
                        # New short position
                        processed_decisions.append(decision)
                
                elif action == 'BUY':
                    # If we have a short position, close it first, then buy
                    if has_short:
                        # Add COVER action first to close the short
                        short_pos = short_positions[symbol]
                        short_value = short_pos.get('shares', 0) * portfolio_state.get('last_prices', {}).get(symbol, short_pos.get('avg_price', 0))
                        cover_decision = {
                            'symbol': symbol,
                            'action': 'COVER',
                            'amount_usd': short_value,
                            'reasoning': f'Auto-covering short before BUY: {decision.get("reasoning", "")}',
                            'portfolio_weight_target': 0
                        }
                        processed_decisions.append(cover_decision)
                        print(f"🔄 Added COVER for {symbol} before BUY (closing short position)")
                        # Then add the BUY decision
                        processed_decisions.append(decision)
                    else:
                        # No short position - process BUY normally
                        processed_decisions.append(decision)
                
                elif action == 'NEUTRAL':
                    # NEUTRAL: No edge found
                    # If owned (long or short), consider closing if capital needed, otherwise maintain
                    if owns_stock or has_short:
                        # Keep as NEUTRAL - PMA can decide to close if capital needed, or maintain
                        processed_decisions.append(decision)
                    else:
                        # Not owned - ignore, no action needed
                        print(f"ℹ️ NEUTRAL decision for {symbol} (not owned) - no action taken")
                        # Don't add to processed_decisions (effectively ignored)
                
                elif action == 'MAINTAIN':
                    # MAINTAIN: Thesis intact, keep position but don't add
                    if owns_stock or has_short:
                        # Keep position, extend target dates for shorts, but don't add more
                        # MAINTAIN action is already correct - no conversion needed
                        processed_decisions.append(decision)
                    else:
                        # Not owned - ignore, no action needed
                        print(f"ℹ️ MAINTAIN decision for {symbol} (not owned) - no action taken")
                        # Don't add to processed_decisions (effectively ignored)
                
                else:
                    # Other actions - process normally
                    processed_decisions.append(decision)
            
            decisions_list = processed_decisions
            
            # Sanitize and enforce per-position caps (25% of available cash for BUY and SHORT,
            # SHORT further limited by per-stock cap if provided)
            try:
                available_cash = portfolio_state.get('cash', 0) or 0
                last_prices = portfolio_state.get('last_prices', {}) or {}
                max_short_per_stock_pct = portfolio_state.get('max_short_per_stock_pct', 25)
                short_cap_pct = min(0.25, (max_short_per_stock_pct or 25) / 100.0)
                buy_cap = available_cash * 0.25
                short_cap = available_cash * short_cap_pct
                
                for d in decisions_list:
                    symbol = d.get('symbol')
                    action_norm = (d.get('action') or '').upper()
                    amt = d.get('amount_usd', 0) or 0
                    try:
                        amt = float(amt)
                    except Exception:
                        amt = 0.0
                    if amt < 0:
                        amt = abs(amt)
                    min_amount_for_one_share = last_prices.get(symbol) or 0
                    if action_norm == 'BUY':
                        if amt > buy_cap:
                            d['reasoning'] = f"{d.get('reasoning','')}".strip() + f" (capped to 25% of cash)"
                            amt = buy_cap
                        # Drop if cannot afford at least 1 share
                        if min_amount_for_one_share and amt < min_amount_for_one_share:
                            d['amount_usd'] = 0.0
                            d['reasoning'] = f"{d.get('reasoning','')}".strip() + " (dropped: < 1 share)"
                            continue
                        d['amount_usd'] = amt
                    elif action_norm == 'SHORT':
                        if amt > short_cap:
                            d['reasoning'] = f"{d.get('reasoning','')}".strip() + f" (capped to {short_cap_pct*100:.0f}% of cash)"
                            amt = short_cap
                        # Drop if cannot short at least 1 share
                        if min_amount_for_one_share and amt < min_amount_for_one_share:
                            d['amount_usd'] = 0.0
                            d['reasoning'] = f"{d.get('reasoning','')}".strip() + " (dropped: < 1 share)"
                            continue
                        d['amount_usd'] = amt
                    elif action_norm in ('SELL','COVER','CLOSE_SHORT'):
                        d['amount_usd'] = amt
                # Remove zeroed decisions (dropped)
                decisions_list = [d for d in decisions_list if (d.get('amount_usd', 0) or 0) > 0 or (d.get('action','').upper() in ('SELL','COVER','CLOSE_SHORT','NEUTRAL','MAINTAIN'))]
            except Exception:
                pass
            
            # Finalize decisions: ensure 'decision' matches 'action' for orchestrator compatibility
            for d in decisions_list:
                if d.get('action') and not d.get('decision'):
                    d['decision'] = d['action']
            
            result = {
                'date': current_date,
                'portfolio_decisions': decisions_list,  # Ensure both fields present
                'portfolio_summary': portfolio_summary,
                'raw_response': response_text,
                'model_used': self.model_name
            }
            
            print(f"✅ Parsed {len(decisions_list)} portfolio decisions")
            return result
            
        except Exception as e:
            print(f"❌ Parse error in Portfolio Manager response: {e}")
            print(f"⚠️ Skipping day due to JSON error; proceeding with no portfolio allocations.")
            # Fallback: Empty allocation for the day (all symbols neutral, zero allocation)
            neutral_decisions = [
                {
                    "symbol": d.get("symbol"),
                    "action": "NEUTRAL",
                    "amount_usd": 0.0,
                    "reasoning": "LLM output could not be parsed; passing through day with no action.",
                    "portfolio_weight_target": 0.0,
                    "decision": "NEUTRAL",
                }
                for d in stock_decisions if d.get("symbol")
            ]
            result = {
                "date": current_date,
                "portfolio_decisions": neutral_decisions,
                "portfolio_summary": {"strategy_notes": "Skipped allocation due to parse error"},
                "raw_response": response_text,
                "model_used": self.model_name
            }
            return result
    
    def _fallback_allocation(self, stock_decisions, portfolio_state, current_date):
        """
        This fallback allocation is intentionally disabled to force errors if waterfall fails.
        """
        raise RuntimeError("PortfolioManager waterfall allocation failed - no fallback allowed under strict mode.")
    
    def _waterfall_allocation(self, decisions_list, portfolio_state, stock_decisions):
        """
        Waterfall allocation: Process decisions sequentially, updating cash after each trade.
        Enforces strict 25% of remaining cash cap per trade.
        Blocks new SHORT positions when cash < 25% of initial value.
        """
        available_cash = portfolio_state.get('cash', 0)
        initial_value = portfolio_state.get('initial_value', 100000)  # Default to $100k if not provided
        last_prices = portfolio_state.get('last_prices', {}) or {}
        max_short_per_stock_pct = portfolio_state.get('max_short_per_stock_pct', 25)
        short_cap_pct = min(0.25, (max_short_per_stock_pct or 25) / 100.0)
        
        # Calculate 25% of initial value threshold
        cash_threshold = initial_value * 0.25
        
        # Separate decisions by action type for priority processing
        close_decisions = [d for d in decisions_list if d.get('action', '').upper() in ('CLOSE', 'COVER', 'SELL')]
        short_decisions = [d for d in decisions_list if d.get('action', '').upper() == 'SHORT']
        buy_decisions = [d for d in decisions_list if d.get('action', '').upper() == 'BUY']
        other_decisions = [d for d in decisions_list if d.get('action', '').upper() not in ('CLOSE', 'COVER', 'SELL', 'SHORT', 'BUY')]
        
        # Build confidence map from stock_decisions
        confidence_map = {d.get('symbol'): d.get('confidence', 0.5) for d in stock_decisions}
        short_confidence_map = {d.get('symbol'): d.get('short_confidence', d.get('confidence', 0.5)) for d in stock_decisions}
        
        # Sort BUY and SHORT by confidence (higher first)
        buy_decisions.sort(key=lambda x: confidence_map.get(x.get('symbol'), 0.5), reverse=True)
        short_decisions.sort(key=lambda x: short_confidence_map.get(x.get('symbol'), 0.5), reverse=True)
        
        remaining_cash = available_cash
        final_decisions = []
        
        # Process CLOSE/COVER/SELL first (these generate cash)
        for decision in close_decisions:
            final_decisions.append(decision)  # CLOSE actions don't need cash, so always include
        
        # Process SHORT decisions (for CFD: only spread fees, but we track by notional)
        # BLOCK new shorts if cash < 25% of initial value
        if available_cash < cash_threshold:
            # Skip all SHORT decisions when cash is below threshold
            for decision in short_decisions:
                decision['amount_usd'] = 0
                decision['reasoning'] = f"{decision.get('reasoning', '')} (blocked: cash ${available_cash:,.2f} < 25% of initial ${cash_threshold:,.2f})"
                decision['action'] = 'NEUTRAL'  # Convert to NEUTRAL instead of SHORT
            # Still add them but with amount_usd = 0
            final_decisions.extend(short_decisions)
        else:
            # Normal SHORT processing
            for decision in short_decisions:
                symbol = decision.get('symbol')
                requested_amount = abs(float(decision.get('amount_usd', 0) or 0))
                price = last_prices.get(symbol, 0)
                
                if price <= 0:
                    continue
                
                # Calculate cap: 25% of remaining cash (further limited by max_short_per_stock_pct)
                cap = min(remaining_cash * 0.25, remaining_cash * short_cap_pct)
                capped_amount = min(requested_amount, cap)
                if capped_amount < price:
                    continue  # Skip if can't afford 1 share
                shares = int(capped_amount // price)
                if shares < 1:
                    continue
                final_amount = shares * price
                
                # --- Insert spread fee logic, matching orchestrator ---
                # Fetch market cap in billions for this symbol
                market_cap_bil = 10  # fallback
                mcaps = portfolio_state.get('market_caps', {})
                if symbol in mcaps:
                    try:
                        mcval = float(mcaps[symbol])
                        if mcval > 0:
                            market_cap_bil = mcval
                    except Exception:
                        pass

                # Calculate spread rate matching orchestrator formula
                # Formula: 0.0006 + 0.0010 + (1.0 / sqrt(market_cap_bil))
                base_rate = 0.0006 + 0.0010
                spread_rate = base_rate + (1.0 / math.sqrt(market_cap_bil))
                spread_fee = final_amount * spread_rate
                # If trade would cause overspend, reduce or skip
                if final_amount + spread_fee > remaining_cash:
                    shares = int(remaining_cash // (price * (1 + spread_rate)))
                    if shares < 1:
                        continue
                    final_amount = shares * price
                    spread_fee = final_amount * spread_rate
                # Now update fields
                decision['amount_usd'] = final_amount
                decision['reasoning'] = f"{decision.get('reasoning', '')} (waterfall: ${final_amount:,.2f}, {shares} shares, spread_fee: ${spread_fee:,.2f})"
                final_decisions.append(decision)
                # Deduct from remaining cash
                remaining_cash -= (final_amount + spread_fee)
        
        # Process BUY decisions
        for decision in buy_decisions:
            symbol = decision.get('symbol')
            requested_amount = abs(float(decision.get('amount_usd', 0) or 0))
            price = last_prices.get(symbol, 0)
            
            if price <= 0:
                continue
            
            # Calculate cap: 25% of remaining cash
            buy_cap = remaining_cash * 0.25
            
            # Cap the requested amount
            capped_amount = min(requested_amount, buy_cap)
            
            # Ensure at least 1 share
            if capped_amount < price:
                continue  # Skip if can't afford 1 share
            
            # Round down to whole shares
            shares = int(capped_amount // price)
            if shares < 1:
                continue
            
            final_amount = shares * price
            
            # Update remaining cash
            remaining_cash -= final_amount
            
            decision['amount_usd'] = final_amount
            decision['reasoning'] = f"{decision.get('reasoning', '')} (waterfall: ${final_amount:,.2f}, {shares} shares)"
            final_decisions.append(decision)
        
        # Add other decisions (NEUTRAL, MAINTAIN, etc.)
        final_decisions.extend(other_decisions)
        
        return final_decisions
    
    def _save_portfolio_decision(self, portfolio_decisions):
        """Save the portfolio decision to a JSON file"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(self.portfolio_save_dir, exist_ok=True)
            
            # Format the filename with date and timestamp
            date_str = portfolio_decisions.get('date')
            if hasattr(date_str, 'strftime'):
                date_str = date_str.strftime('%Y%m%d')
            else:
                # If date_str is already a string, ensure it's formatted consistently
                try:
                    date_str = datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y%m%d')
                except ValueError:
                    date_str = datetime.now().strftime('%Y%m%d')  # Fallback
            
            timestamp = datetime.now().strftime('%H%M%S')
            filename = f"portfolio_decision_{date_str}_{timestamp}.json"
            file_path = os.path.join(self.portfolio_save_dir, filename)
            
            # Save the decision to file
            with open(file_path, 'w') as f:
                json.dump(portfolio_decisions, f, indent=2)
            
            print(f"✅ Portfolio decision saved to {file_path}")
        except Exception as e:
            print(f"❌ Error saving portfolio decision: {e}")
            # Persistence failure should not interrupt the backtest
    
    