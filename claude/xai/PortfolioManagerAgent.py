"""
PortfolioManagerAgent.py: Portfolio-level decision maker that allocates capital across stocks
based on individual stock decisions and portfolio constraints.
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv
from xai_sdk import Client as XAIClient
from xai_sdk.chat import user as xai_user, system as xai_system

# Load environment variables from .env in the same directory as this script
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(dotenv_path=env_path)

DEFAULT_PORTFOLIO_TOKEN = (
    os.getenv("PORTFOLIO_XAI_API_KEY")
)


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
        self.portfolio_save_dir = os.path.join(self.data_dir, "portfolio_decisions_Grok")
        
        # Use provided API key or load from environment
        # Portfolio Manager only needs ONE key since it runs sequentially (not in parallel)
        self.api_key = api_key or DEFAULT_PORTFOLIO_TOKEN
        if not self.api_key:
            raise ValueError(
                "No xAI API token found. Pass api_key or set PORTFOLIO_XAI_API_KEY / XAI_API_KEY_1 in the environment."
            )
        
        self.client = XAIClient(api_key=self.api_key)
        self.model_name = os.getenv("XAI_PORTFOLIO_MODEL", "grok-4-0709")
        
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
            
            print(f"📊 Calling Grok API for portfolio allocation covering {len(stock_decisions)} stock decisions...")
            
            # Call Grok API
            response_text = self._call_grok_api(prompt)
            
            print(f"✅ Got Grok Portfolio response")
            
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
            print(f"❌ Grok API Error: {e}")
            return self._fallback_allocation(stock_decisions, portfolio_state, current_date)
            
    def _call_grok_api(self, prompt: str) -> str:
        """Make call to xAI Grok API"""
        chat = self.client.chat.create(model=self.model_name, temperature=0)
        chat.append(
            xai_system(
                "You are the best portfolio manager in the world. "
                "Respond strictly with valid JSON in the structure specified."
            )
        )
        chat.append(xai_user(prompt))

        response = chat.sample()
        content = getattr(response, "content", None)

        if isinstance(content, str):
            return content

        if isinstance(content, list):
            parts = []
            for part in content:
                part_text = getattr(part, "text", None)
                if part_text:
                    parts.append(part_text)
            if parts:
                return "".join(parts)

        raise RuntimeError(f"Unexpected Grok response format: {response}")
            
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
    
    def _fallback_allocation(self, stock_decisions, portfolio_state, current_date):
        """
        Fallback allocation strategy when API fails.
        Uses simple confidence-based position sizing.
        """
        cash = portfolio_state.get('cash', 0)
        total_value = portfolio_state.get('total_value', cash)
        
        # Calculate simple allocations
        decisions_list = []
        
        # Count BUY decisions to distribute capital
        buy_decisions = [d for d in stock_decisions if d.get('decision') == 'BUY']
        
        for decision in stock_decisions:
            symbol = decision.get('symbol')
            action = decision.get('decision', 'HOLD')
            confidence = decision.get('confidence', 0.5)
            
            if action == 'BUY':
                # Allocate based on confidence and available capital
                # Base allocation: 15% of portfolio * confidence
                base_allocation = total_value * 0.15 * confidence
                # Adjust for number of concurrent buys
                adjusted_allocation = min(base_allocation, cash / max(len(buy_decisions), 1))
                
                decisions_list.append({
                    'symbol': symbol,
                    'action': 'BUY',
                    'amount_usd': adjusted_allocation,
                    'reasoning': f'Fallback allocation: {confidence*100:.0f}% confidence',
                    'portfolio_weight_target': (adjusted_allocation / total_value * 100) if total_value > 0 else 0
                })
            
            elif action == 'SELL':
                # Sell full position
                positions = portfolio_state.get('positions', {})
                if symbol in positions and positions[symbol].get('shares', 0) > 0:
                    last_price = portfolio_state.get('last_prices', {}).get(symbol, positions[symbol].get('avg_price', 0))
                    position_value = positions[symbol]['shares'] * last_price
                    
                    decisions_list.append({
                        'symbol': symbol,
                        'action': 'SELL',
                        'amount_usd': position_value,
                        'reasoning': f'Fallback: Sell full position',
                        'portfolio_weight_target': 0
                    })
        
        return {
            'date': current_date,
            'portfolio_decisions': decisions_list,
            'portfolio_summary': {
                'total_allocation': sum(d['amount_usd'] for d in decisions_list if d['action'] == 'BUY'),
                'cash_reserved': cash - sum(d['amount_usd'] for d in decisions_list if d['action'] == 'BUY'),
                'risk_assessment': 'Fallback allocation strategy used',
                'strategy_notes': 'API error - using simple confidence-based allocation'
            },
            'model_used': 'fallback'
        }