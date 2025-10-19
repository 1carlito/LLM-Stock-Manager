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

# Configure Gemini
import google.generativeai as genai

# Load Gemini API key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable not set")

genai.configure(api_key=api_key)
MODEL_NAME = "gemini-2.5-pro"  # Using Gemini Pro for advanced reasoning

class ReasoningAgent:
    def __init__(self, data_dir="."):
        self.data_dir = data_dir
        self.model = MODEL_NAME
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        print("✅ ReasoningAgent initialized with Gemini Pro API")

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
                
            print(f"📞 Calling Gemini API for {symbol}...")
            
            response = self._call_gemini_api(prompt)
            
            print(f"✅ Got Gemini response for {symbol}")
            return self._parse_response(response, symbol, current_date)
        except Exception as e:
            print(f"❌ Gemini API Error for {symbol}: {e}")
            return {
                "symbol": symbol,
                "date": current_date,
                "decision": "HOLD",
                "confidence": 0.5,
                "reasoning": f"Error: {str(e)}",
                "model_used": "gemini-2.5-pro"
            }

    def _call_gemini_api(self, prompt: str) -> str:
        """Call Gemini API with the given prompt"""
        try:
            # Initialize Gemini client
            model = genai.GenerativeModel(self.model)
            
            # Generate response
            response = model.generate_content(prompt)
            
            if response and response.text:
                return response.text
            else:
                raise Exception("Empty response from Gemini API")
                
        except Exception as e:
            print(f"❌ Error calling Gemini API: {e}")
            raise e

    def _build_decision_prompt(self, symbol, current_date, valuation_data, fundamental_data, sentiment_data, previous_decisions=None):
        """Build a prompt that focuses on sentiment analysis and previous decisions for final decision making"""
        
        # Format date if it's a datetime object
        date_str = current_date
        if hasattr(current_date, 'strftime'):
            date_str = current_date.strftime('%Y-%m-%d')
        
        # Build the base prompt focusing on sentiment analysis
        prompt = f"""
You are a professional trading agent analyzing {symbol} on {date_str}.

SENTIMENT ANALYSIS:
{json.dumps(sentiment_data, indent=2) if sentiment_data else "No sentiment data available"}
"""
        
        # Add additional analysis data if available (but don't require it)
        if valuation_data:
            prompt += f"""
VALUATION ANALYSIS (if available):
{json.dumps(valuation_data, indent=2)}
"""
        
        if fundamental_data:
            prompt += f"""
FUNDAMENTAL ANALYSIS (if available):
{json.dumps(fundamental_data, indent=2)}
"""
        
        # Add previous decisions if available
        if previous_decisions and len(previous_decisions) > 0:
            prompt += f"""

PREVIOUS TRADING DECISIONS:
{json.dumps(previous_decisions, indent=2)}

Consider these previous decisions in your analysis. Look for trends, consistency, and any changes in market conditions since these decisions were made.
"""
        
        # Add final instructions focused on sentiment-driven decisions
        prompt += f"""

Based on the sentiment analysis and any available additional data, make a trading decision:
1. Analyze the sentiment signals, confidence levels, and market sentiment trends
2. Consider the current stock price and any price momentum indicated in the sentiment data
3. Evaluate the strength and reliability of the sentiment signals
4. Look for significant sentiment shifts or strong directional signals
5. Consider how this decision fits with the previous trading history (if provided)
6. Be more decisive when sentiment is strong and well-supported by data

IMPORTANT: You should be willing to make BUY/SELL decisions based on strong sentiment signals, even if other analysis data is limited. The sentiment analysis includes current stock prices and market sentiment that can drive trading decisions.

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
                'model_used': 'gemini-2.5-pro',
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
                'model_used': 'gemini-2.5-pro'
            }