"""
PortfolioManagerAgent.py: Portfolio-level decision maker that allocates capital across stocks
based on individual stock decisions and portfolio constraints.
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv
import anthropic

# Load environment variables from .env in the same directory as this script
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(dotenv_path=env_path)

class PortfolioManagerAgent:
    """
    Portfolio Manager that receives all individual stock decisions and makes
    portfolio-level allocation decisions considering:
    - Available capital
    - Current positions
    - Position sizing
    - Portfolio balance
    """
    
    def __init__(self, data_dir=".", api_key=None):
        self.data_dir = data_dir
        self.portfolio_save_dir = os.path.join(self.data_dir, "portfolio_decisions_Claude")
        
        # Use provided API key or load from environment
        # Portfolio Manager only needs ONE key since it runs sequentially (not in parallel)
        self.api_key = api_key
        if not self.api_key:
            self.api_key = os.getenv("PORTFOLIO_CLAUDE_API_KEY")
        
        if not self.api_key:
            raise ValueError("PORTFOLIO_CLAUDE_API_KEY environment variable not set. Portfolio Manager needs only one API key since it runs sequentially after all stock decisions are collected.")
        
        # Initialize Anthropic client
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model_name = "claude-3-5-haiku-20241022"
        
        print(f"✅ PortfolioManagerAgent initialized with {self.model_name}")
    
    def make_portfolio_decisions(self, stock_decisions, portfolio_state, current_date, previous_portfolio_decisions=None):
        """
        Make portfolio-level allocation decisions based on individual stock decisions.
        
        Args:
            stock_decisions: List of decisions from ReasoningAgent for each stock
                [{'symbol': 'AAPL', 'decision': 'BUY', 'confidence': 0.85, 'reasoning': '...'}, ...]
            portfolio_state: Current portfolio state
                {'cash': 1000000, 'positions': {'AAPL': {'shares': 100, 'avg_price': 150}}, 
                 'total_value': 1050000, 'last_prices': {'AAPL': 155}}
            current_date: Current trading date
            previous_portfolio_decisions: List of previous portfolio allocation decisions (optional)
        
        Returns:
            Dict with portfolio-level decisions including position sizes for each action
        """
        try:
            # Build prompt with all stock decisions and portfolio context
            prompt = self._build_portfolio_prompt(stock_decisions, portfolio_state, current_date, previous_portfolio_decisions)
            
            print(f"📊 Calling Claude API for portfolio allocation covering {len(stock_decisions)} stock decisions...")
            
            # Call Claude API
            response_text = self._call_claude_api(prompt)
            
            print(f"✅ Got Claude Portfolio response")
            
            # Parse response into portfolio decisions
            try:
                portfolio_decisions = self._parse_portfolio_response(
                    response_text, stock_decisions, portfolio_state, current_date
                )
                self._save_portfolio_decision(portfolio_decisions)
                return portfolio_decisions
            except Exception as parse_error:
                print(f"❌ Error parsing portfolio response: {parse_error}")
                return self._fallback_allocation(stock_decisions, portfolio_state, current_date)
        except Exception as e:
            print(f"❌ Claude API Error: {e}")
            return self._fallback_allocation(stock_decisions, portfolio_state, current_date)
            
    def _call_claude_api(self, prompt: str) -> str:
        """Make call to Claude API"""
        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=4000,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                system="You are the best portfolio manager in the world."
            )
            
            if response and response.content:
                # Extract text content from the response
                for content_block in response.content:
                    if content_block.type == "text":
                        return content_block.text
                return ""
            else:
                raise Exception("Empty response from Claude API")
        except Exception as e:
            raise Exception(f"Claude API Error: {e}")
            
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
    
    def _build_portfolio_prompt(self, stock_decisions, portfolio_state, current_date, previous_portfolio_decisions=None):
        """Build prompt for portfolio-level decision making"""
        
        # Calculate portfolio metrics
        total_value = portfolio_state.get('total_value', portfolio_state.get('cash', 0))
        cash = portfolio_state.get('cash', 0)
        positions = portfolio_state.get('positions', {})
        last_prices = portfolio_state.get('last_prices', {})
        initial_value = portfolio_state.get('initial_value', 1000000)  # Default to $1M if not provided
        
        # Calculate current total return percentage
        total_return_pct = ((total_value - initial_value) / initial_value) * 100 if initial_value > 0 else 0
        
        # Calculate position values and unrealized PnL
        position_values = {}
        total_unrealized_pnl = 0
        
        for symbol, pos in positions.items():
            if pos['shares'] > 0:
                current_price = last_prices.get(symbol, pos.get('avg_price', 0))
                position_value = pos['shares'] * current_price
                cost_basis = pos['shares'] * pos.get('avg_price', current_price)
                unrealized_pnl = position_value - cost_basis
                total_unrealized_pnl += unrealized_pnl
                
                position_values[symbol] = {
                    'shares': pos['shares'],
                    'current_price': current_price,
                    'avg_price': pos.get('avg_price', current_price),
                    'value': position_value,
                    'unrealized_pnl': unrealized_pnl,
                    'pct_of_portfolio': (position_value / total_value * 100) if total_value > 0 else 0
                }
        
        prompt = f"""
You are the highest level Portfolio Manager in existence making final allocation decisions for a trading portfolio on {current_date}. Optimize for returns; do not apply conservative cash buffers unless the data clearly warrants it.

CURRENT PORTFOLIO PERFORMANCE:
- Current Total Return (percent): {total_return_pct:.2f}%
- Total Portfolio Value: ${total_value:,.2f}
- Available Cash: ${cash:,.2f}
- Cash Percentage: {(cash/total_value*100) if total_value > 0 else 0:.1f}%
- Total Unrealized PnL: ${total_unrealized_pnl:,.2f}

CURRENT POSITIONS:
{json.dumps(position_values, indent=2) if position_values else "No current positions"}

INDIVIDUAL STOCK DECISIONS:
{json.dumps(stock_decisions, indent=2)}
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
Analyze all individual stock decisions and make portfolio-level allocation decisions. For each stock with a BUY or SELL decision, determine:

1. Should we execute this trade? (Consider portfolio balance, risk, and existing positions)
2. What position size should we use? (Dollar amount to invest or shares to sell)

ALLOCATION GUIDELINES (AGGRESSIVE):
- You may fully deploy capital on high conviction; no fixed cash buffer is required.
- Individual positions can be sized up to ~30% of portfolio value at maximum conviction.
- Favor deploying capital on high-confidence signals; do not throttle allocations due to generic risk aversion.
- Scale position sizes by confidence and available capital.
- For SELL decisions, choose partial or full exits based on conviction and existing exposure.

RISK MANAGEMENT (PRAGMATIC):
- Do not allocate more than available cash.
- Avoid obvious over-concentration in highly correlated names when multiple high-conviction signals compete.
- Consider current position sizes before adding.

RESPONSE FORMAT:
For each stock decision, provide your allocation decision in this JSON format:

{{
  "portfolio_decisions": [
    {{
      "symbol": "AAPL",
      "action": "BUY|SELL|HOLD",
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
"""
        
        return prompt
    
    def _parse_portfolio_response(self, response_text, stock_decisions, portfolio_state, current_date):
        """Parse the portfolio manager's response"""
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            
            if json_match:
                portfolio_decisions = json.loads(json_match.group(0))
            else:
                # Fallback to default allocation
                print("⚠️ Could not parse JSON from Portfolio Manager response, using fallback")
                return self._fallback_allocation(stock_decisions, portfolio_state, current_date)
            
            # Validate and normalize the decisions
            decisions_list = portfolio_decisions.get('portfolio_decisions', [])
            portfolio_summary = portfolio_decisions.get('portfolio_summary', {})
            
            # Apply top-k allocation by confidence: rank by confidence and fill from highest to lowest
            decisions_list = self._apply_top_k_allocation(
                decisions_list, stock_decisions, portfolio_state
            )
            
            result = {
                'date': current_date,
                'portfolio_decisions': decisions_list,
                'portfolio_summary': portfolio_summary,
                'raw_response': response_text,
                'model_used': self.model_name
            }
            
            print(f"✅ Parsed {len(decisions_list)} portfolio decisions")
            return result
            
        except Exception as e:
            print(f"❌ Parse error in Portfolio Manager response: {e}")
            return self._fallback_allocation(stock_decisions, portfolio_state, current_date)
    
    def _apply_top_k_allocation(self, portfolio_decisions, stock_decisions, portfolio_state):
        """
        Apply top-k allocation strategy: rank by confidence and fill from highest to lowest
        until cash runs out. This enables partial filling instead of all-or-nothing.
        
        Args:
            portfolio_decisions: List of portfolio allocation decisions from LLM
            stock_decisions: Original stock decisions with confidence scores
            portfolio_state: Current portfolio state with available cash
        
        Returns:
            List of portfolio decisions sorted by confidence, with amounts adjusted if needed
        """
        cash = portfolio_state.get('cash', 0)
        last_prices = portfolio_state.get('last_prices', {})
        
        # Create a mapping of symbol to confidence from original stock decisions
        confidence_map = {d.get('symbol'): d.get('confidence', 0.0) for d in stock_decisions}
        
        # Separate BUY and SELL decisions (SELLs don't require cash, so handle separately)
        buy_decisions = []
        sell_decisions = []
        other_decisions = []
        
        for decision in portfolio_decisions:
            action = decision.get('action', '').upper()
            if action == 'BUY':
                buy_decisions.append(decision)
            elif action == 'SELL':
                sell_decisions.append(decision)
            else:
                other_decisions.append(decision)
        
        # Rank BUY decisions by confidence (highest first)
        for decision in buy_decisions:
            symbol = decision.get('symbol')
            decision['_confidence'] = confidence_map.get(symbol, 0.0)
        
        buy_decisions.sort(key=lambda x: x.get('_confidence', 0.0), reverse=True)
        
        # Fill BUY decisions in order of confidence until cash runs out
        remaining_cash = cash
        filled_decisions = []
        
        for decision in buy_decisions:
            symbol = decision.get('symbol')
            amount_usd = decision.get('amount_usd', 0)
            
            if amount_usd <= 0:
                # Skip zero or negative allocations
                continue
            
            # Calculate cost (accounting for share rounding)
            current_price = last_prices.get(symbol, 0)
            if current_price <= 0:
                # Skip if we don't have a price
                print(f"⚠️ Skipping {symbol}: No price available")
                continue
            
            shares = int(amount_usd / current_price)
            if shares == 0:
                # Skip if we can't afford even 1 share
                continue
            
            cost = shares * current_price
            
            if cost <= remaining_cash:
                # Can fill full allocation
                decision['amount_usd'] = cost  # Update to actual cost after rounding
                filled_decisions.append(decision)
                remaining_cash -= cost
                print(f"✅ Allocated ${cost:,.2f} to {symbol} (confidence: {decision['_confidence']:.2f})")
            else:
                # Can't fill full allocation - fill what we can or skip if too small
                if remaining_cash > 0:
                    partial_shares = int(remaining_cash / current_price)
                    if partial_shares > 0:
                        partial_cost = partial_shares * current_price
                        decision['amount_usd'] = partial_cost
                        decision['reasoning'] = (decision.get('reasoning', '') + 
                                               f' [Partial fill: requested ${amount_usd:,.2f}, filled ${partial_cost:,.2f}]')
                        filled_decisions.append(decision)
                        remaining_cash -= partial_cost
                        print(f"⚠️ Partial allocation ${partial_cost:,.2f} to {symbol} (confidence: {decision['_confidence']:.2f}, requested ${amount_usd:,.2f})")
                    else:
                        print(f"❌ Skipped {symbol}: Insufficient cash for even 1 share (confidence: {decision['_confidence']:.2f})")
                else:
                    print(f"❌ Skipped {symbol}: No remaining cash (confidence: {decision['_confidence']:.2f})")
        
        # Remove temporary confidence field before returning
        for decision in filled_decisions:
            decision.pop('_confidence', None)
        
        # Combine: sells first (they add cash), then filled buys, then other decisions
        # Note: SELLs don't need ranking since they add cash and don't require allocation
        final_decisions = sell_decisions + filled_decisions + other_decisions
        
        total_allocated = sum(d.get('amount_usd', 0) for d in filled_decisions)
        print(f"📊 Top-k allocation complete: {len(filled_decisions)}/{len(buy_decisions)} BUY decisions filled, "
              f"total allocated: ${total_allocated:,.2f}, remaining cash: ${remaining_cash:,.2f}")
        
        return final_decisions
    
    def _fallback_allocation(self, stock_decisions, portfolio_state, current_date):
        """
        Fallback allocation strategy when API fails.
        Uses simple confidence-based position sizing with top-k allocation.
        """
        cash = portfolio_state.get('cash', 0)
        total_value = portfolio_state.get('total_value', cash)
        last_prices = portfolio_state.get('last_prices', {})
        
        # Separate BUY and SELL decisions
        buy_decisions = []
        sell_decisions = []
        
        for decision in stock_decisions:
            action = decision.get('decision', 'HOLD')
            if action == 'BUY':
                buy_decisions.append(decision)
            elif action == 'SELL':
                sell_decisions.append(decision)
        
        # Sort BUY decisions by confidence (highest first)
        buy_decisions.sort(key=lambda x: x.get('confidence', 0.0), reverse=True)
        
        # Apply top-k allocation: fill from highest confidence down
        decisions_list = []
        remaining_cash = cash
        
        # Fill BUY decisions in order of confidence
        for decision in buy_decisions:
            symbol = decision.get('symbol')
            confidence = decision.get('confidence', 0.5)
            
            # Base allocation: 15% of portfolio * confidence
            base_allocation = total_value * 0.15 * confidence
            current_price = last_prices.get(symbol, 0)
            
            if current_price > 0 and base_allocation > 0:
                shares = int(base_allocation / current_price)
                if shares > 0:
                    cost = shares * current_price
                    
                    # Check if we can afford it
                    if cost <= remaining_cash:
                        decisions_list.append({
                            'symbol': symbol,
                            'action': 'BUY',
                            'amount_usd': cost,
                            'reasoning': f'Fallback allocation: {confidence*100:.0f}% confidence',
                            'portfolio_weight_target': (cost / total_value * 100) if total_value > 0 else 0
                        })
                        remaining_cash -= cost
                    elif remaining_cash > 0:
                        # Partial fill
                        partial_shares = int(remaining_cash / current_price)
                        if partial_shares > 0:
                            partial_cost = partial_shares * current_price
                            decisions_list.append({
                                'symbol': symbol,
                                'action': 'BUY',
                                'amount_usd': partial_cost,
                                'reasoning': f'Fallback partial allocation: {confidence*100:.0f}% confidence',
                                'portfolio_weight_target': (partial_cost / total_value * 100) if total_value > 0 else 0
                            })
                            remaining_cash -= partial_cost
        
        # Add SELL decisions (they don't require cash allocation)
        for decision in sell_decisions:
            symbol = decision.get('symbol')
            positions = portfolio_state.get('positions', {})
            if symbol in positions and positions[symbol].get('shares', 0) > 0:
                last_price = last_prices.get(symbol, positions[symbol].get('avg_price', 0))
                position_value = positions[symbol]['shares'] * last_price
                
                decisions_list.append({
                    'symbol': symbol,
                    'action': 'SELL',
                    'amount_usd': position_value,
                    'reasoning': f'Fallback: Sell full position',
                    'portfolio_weight_target': 0
                })
        
        total_allocation = sum(d['amount_usd'] for d in decisions_list if d['action'] == 'BUY')
        
        return {
            'date': current_date,
            'portfolio_decisions': decisions_list,
            'portfolio_summary': {
                'total_allocation': total_allocation,
                'cash_reserved': remaining_cash,
                'risk_assessment': 'Fallback allocation strategy used with top-k ranking',
                'strategy_notes': 'API error - using simple confidence-based allocation with top-k filling'
            },
            'model_used': 'fallback'
        }