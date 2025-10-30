"""
PortfolioManagerAgent.py: Portfolio-level decision maker that allocates capital across stocks
based on individual stock decisions and portfolio constraints.
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables from .env in the same directory as this script
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(dotenv_path=env_path)

class PortfolioManagerAgent:
    """
    Portfolio Manager that receives all individual stock decisions and makes
    portfolio-level allocation decisions considering:
    - Available capital
    - Current positions
    - Risk management
    - Position sizing
    - Portfolio balance
    """
    
    def __init__(self, data_dir=".", api_key=None):
        self.data_dir = data_dir
        
        # Use provided API key or load from environment
        # Try dedicated portfolio key first, then general key, then numbered keys
        self.api_key = api_key
        if not self.api_key:
            self.api_key = os.getenv("GEMINI_API_KEY_PORTFOLIO")
        if not self.api_key:
            self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            # Try numbered keys as fallback
            for i in range(1, 21):
                key = os.getenv(f"GEMINI_API_KEY_{i}")
                if key:
                    self.api_key = key
                    break
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY_PORTFOLIO, GEMINI_API_KEY, or GEMINI_API_KEY_1-20 environment variable not set")
        
        genai.configure(api_key=self.api_key)
        self.model_name = "gemini-2.5-pro"
        print("✅ PortfolioManagerAgent initialized with Gemini Pro API")
    
    def make_portfolio_decisions(self, stock_decisions, portfolio_state, current_date):
        """
        Make portfolio-level allocation decisions based on individual stock decisions.
        
        Args:
            stock_decisions: List of decisions from ReasoningAgent for each stock
                [{'symbol': 'AAPL', 'decision': 'BUY', 'confidence': 0.85, 'reasoning': '...'}, ...]
            portfolio_state: Current portfolio state
                {'cash': 1000000, 'positions': {'AAPL': {'shares': 100, 'avg_price': 150}}, 
                 'total_value': 1050000, 'last_prices': {'AAPL': 155}}
            current_date: Current trading date
        
        Returns:
            Dict with portfolio-level decisions including position sizes for each action
        """
        try:
            # Build prompt with all stock decisions and portfolio context
            prompt = self._build_portfolio_prompt(stock_decisions, portfolio_state, current_date)
            
            print(f"📊 Calling Portfolio Manager API for {len(stock_decisions)} stock decisions...")
            
            # Call Gemini API
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            
            if not response or not response.text:
                raise Exception("Empty response from Gemini API")
            
            print(f"✅ Got Portfolio Manager response")
            
            # Parse response into portfolio decisions
            portfolio_decisions = self._parse_portfolio_response(
                response.text, stock_decisions, portfolio_state, current_date
            )
            
            return portfolio_decisions
            
        except Exception as e:
            print(f"❌ Portfolio Manager API Error: {e}")
            # Return default decisions - execute as-is with simple allocation
            return self._fallback_allocation(stock_decisions, portfolio_state, current_date)
    
    def _build_portfolio_prompt(self, stock_decisions, portfolio_state, current_date):
        """Build prompt for portfolio-level decision making"""
        
        # Calculate portfolio metrics
        total_value = portfolio_state.get('total_value', portfolio_state.get('cash', 0))
        cash = portfolio_state.get('cash', 0)
        positions = portfolio_state.get('positions', {})
        last_prices = portfolio_state.get('last_prices', {})
        
        # Calculate position values
        position_values = {}
        for symbol, pos in positions.items():
            if pos['shares'] > 0:
                current_price = last_prices.get(symbol, pos.get('avg_price', 0))
                position_values[symbol] = {
                    'shares': pos['shares'],
                    'current_price': current_price,
                    'value': pos['shares'] * current_price,
                    'pct_of_portfolio': (pos['shares'] * current_price / total_value * 100) if total_value > 0 else 0
                }
        
        prompt = f"""
You are a Portfolio Manager making final allocation decisions for a trading portfolio on {current_date}. Optimize for returns; do not apply conservative cash buffers unless the data clearly warrants it.

CURRENT PORTFOLIO STATE:
- Total Portfolio Value: ${total_value:,.2f}
- Available Cash: ${cash:,.2f}
- Cash Percentage: {(cash/total_value*100) if total_value > 0 else 0:.1f}%

CURRENT POSITIONS:
{json.dumps(position_values, indent=2) if position_values else "No current positions"}

INDIVIDUAL STOCK DECISIONS:
{json.dumps(stock_decisions, indent=2)}

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

