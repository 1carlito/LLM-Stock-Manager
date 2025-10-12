"""
ReasoningAgent.py: Final decision maker that integrates analyses from all other agents
"""

import os
import json
import re
from datetime import datetime
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

# Configure DeepSeek
openai.api_key = 'sk-c895e21f2dbd410c933b7f018910906f'  # Dedicated key for NVO fundamental analysis
openai.api_base = "https://api.deepseek.com/v1"
MODEL_NAME = "deepseek-reasoner"  # Using the V3 reasoning model (released Dec 26, 2024)

class ReasoningAgent:
    def __init__(self, data_dir="."):
        self.data_dir = data_dir
        self.model = MODEL_NAME
        if not openai.api_key:
            raise ValueError("DeepSeek API key not found in environment variables")
        print("✅ DeepSeek ReasoningAgent initialized with DeepSeek API")

    def make_decision(self, symbol="NVO", current_date=None, valuation_data=None, fundamental_data=None, sentiment_data=None, previous_decisions=None):
        """
        Make a trading decision based on the provided analysis data from all agents and previous decisions.
        
        Args:
            symbol: Stock ticker symbol
            current_date: Current trading date
            valuation_data: Data from ValuationAgent
            fundamental_data: Data from FundamentalAgent
            sentiment_data: Data from SentimentAgent
            previous_decisions: List of previous trading decisions for this symbol (optional)
        """
        try:
            # Format the prompt with analysis data and previous decisions
            prompt = self._build_decision_prompt(symbol, current_date, valuation_data, fundamental_data, sentiment_data, previous_decisions)
                
            print(f"📞 Calling DeepSeek API for {symbol}...")
            
            response = self._call_deepseek_api(prompt)
            
            print(f"✅ Got DeepSeek response for {symbol}")
            return self._parse_response(response, symbol, current_date)
        except Exception as e:
            print(f"❌ DeepSeek API Error for {symbol}: {e}")
            return {
                "symbol": symbol,
                "date": current_date,
                "decision": "HOLD",
                "confidence": 0.5,
                "reasoning": f"Error: {str(e)}",
                "model_used": "deepseek-reasoner"
            }

    def _call_deepseek_api(self, prompt: str) -> str:
        """Call DeepSeek API with the given prompt"""
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.7,
                max_tokens=2000
            )
            
            return response['choices'][0]['message']['content']
                
        except Exception as e:
            print(f"❌ Error calling DeepSeek API: {e}")
            raise e

    def _build_decision_prompt(self, symbol, current_date, valuation_data, fundamental_data, sentiment_data, previous_decisions=None):
        """Build a prompt that integrates all agent analyses and previous decisions for final decision making"""
        
        # Format date if it's a datetime object
        date_str = current_date
        if hasattr(current_date, 'strftime'):
            date_str = current_date.strftime('%Y-%m-%d')
        
        # Build the base prompt with analysis data
        prompt = f"""
You are a professional trading agent analyzing {symbol} on {date_str}.

VALUATION ANALYSIS:
{json.dumps(valuation_data, indent=2)}

FUNDAMENTAL ANALYSIS:
{json.dumps(fundamental_data, indent=2)}

SENTIMENT ANALYSIS:
{json.dumps(sentiment_data, indent=2)}
"""
        
        # Add previous decisions if available
        if previous_decisions and len(previous_decisions) > 0:
            prompt += f"""

PREVIOUS TRADING DECISIONS:
{json.dumps(previous_decisions, indent=2)}

Consider these previous decisions in your analysis. Look for trends, consistency, and any changes in market conditions since these decisions were made.
"""
        
        # Add final instructions
        prompt += f"""

Based on this comprehensive analysis from all three specialized agents, make a final trading decision:
1. Analyze the valuation metrics, fundamental data, and sentiment signals
2. Consider the overall market conditions and sector performance
3. Evaluate risk factors and potential catalysts
4. Determine if the three analyses are in agreement or conflict
5. Consider how this decision fits with the previous trading history (if provided)

Provide your decision in this format:
DECISION: [BUY/SELL/HOLD]
CONFIDENCE: [1-100]
REASONING: [Brief explanation of your decision, key factors considered, and risk assessment]
"""
        
        return prompt

    def _parse_response(self, response_text, symbol, current_date):
        """Parse the LLM response to extract decision, confidence, and reasoning."""
        try:
            # Initialize default values
            decision = "HOLD"
            confidence = 50
            reasoning = "Unable to parse response"
            
            # Extract decision
            decision_match = re.search(r'DECISION:\s*([A-Z]+)', response_text, re.IGNORECASE)
            if decision_match:
                decision = decision_match.group(1).upper()
            
            # Extract confidence
            confidence_match = re.search(r'CONFIDENCE:\s*(\d+)', response_text)
            if confidence_match:
                confidence = int(confidence_match.group(1))
                confidence_normalized = confidence / 100.0  # Normalize to 0-1 range
            else:
                confidence_normalized = 0.5
            
            # Extract reasoning
            reasoning_match = re.search(r'REASONING:\s*(.+)', response_text, re.DOTALL)
            if reasoning_match:
                reasoning = reasoning_match.group(1).strip()
            
            result = {
                'symbol': symbol,
                'date': current_date,
                'decision': decision,
                'confidence': confidence_normalized,
                'reasoning': reasoning,
                'model_used': 'deepseek-reasoner',
                'raw_response': response_text
            }
            
            print(f"✅ Parsed: {decision} (confidence: {confidence}%)")
            return result
            
        except Exception as e:
            print(f"❌ Parse error: {e}")
            return {
                'symbol': symbol,
                'date': current_date,
                'decision': "HOLD",
                'confidence': 0.5,
                'reasoning': f'Parse error: {str(e)}',
                'model_used': 'deepseek-reasoner'
            }