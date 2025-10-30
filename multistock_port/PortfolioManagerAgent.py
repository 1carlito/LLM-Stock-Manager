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
    - Position sizing
    - Portfolio balance
    """
    
    def __init__(self, data_dir=".", api_key=None):
        self.data_dir = data_dir
        
        # Use provided API key or load from environment
        self.api_key = api_key or os.getenv("GEMINI_API_KEY_PORTFOLIO")
        if not self.api_key:
            # Fall back to main API key if portfolio-specific key not available
            self.api_key = os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY or GEMINI_API_KEY_PORTFOLIO environment variable not set")
        
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
You are tasked to make trade decisions like a Portfolio Manager for a trading portfolio on {current_date} However you are trying to maximise returns, therefore you are not constrained to predictable portfolio allocations.

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

ALLOCATION GUIDELINES:
- Total portfolio exposure should generally not exceed 80-90% (keep 10-20% cash buffer)
- Individual positions should typically be 10-25% of portfolio value
- Consider concentration risk - don't over-allocate to similar sectors
- Higher confidence decisions can warrant larger position sizes
- Scale position sizes based on available capital and risk
- For SELL decisions, consider whether to sell partial or full positions
- Balance new positions with maintaining existing winners

RISK MANAGEMENT:
- Don't allocate more than available cash
- Consider correlation between holdings
- Maintain diversification across stocks
- Consider current position sizes before adding to existing positions

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
- Be decisive but prudent with capital allocation
- Ensure total allocations don't exceed available cash
- Consider the portfolio holistically, not just individual stocks
- Provide clear reasoning for each position size
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

