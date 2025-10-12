import google.generativeai as genai
import os
import json
import re
from datetime import datetime

class ReasoningAgent:
    def __init__(self, data_dir="."):
        self.data_dir = data_dir
        # Set Gemini API key and client
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel("gemini-2.5-pro")
        print("✅ Gemini ReasoningAgent initialized with Gemini API")

    def make_decision(self, symbol, current_date, valuation_data, fundamental_data, sentiment_data):
        """
        Make a trading decision based on the provided analysis data.
        """
        try:
            # Format the prompt with analysis data
            prompt = f"""
You are a professional trading agent analyzing {symbol} on {current_date.strftime('%Y-%m-%d')}.

VALUATION ANALYSIS:
{json.dumps(valuation_data, indent=2)}

FUNDAMENTAL ANALYSIS:
{json.dumps(fundamental_data, indent=2)}

SENTIMENT ANALYSIS:
{json.dumps(sentiment_data, indent=2)}

Based on this comprehensive analysis, make a trading decision:

DECISION: [BUY/SELL/HOLD]
CONFIDENCE: [0-100]
REASONING: [Your detailed reasoning in 2-3 sentences]

Format your response exactly as shown above.
"""

            print(f"🤖 Calling Gemini Pro for {symbol}...")
            
            # Make the API call
            system_prompt = "You are a professional stock market analyst and trading strategist. Your task is to analyze market data and make trading decisions based on technical, fundamental, and sentiment analysis."
            full_prompt = f"{system_prompt}\n\n{prompt}"
            
            response = self.client.generate_content(full_prompt)
            
            response_text = response.text.strip()
            print(f"📝 Raw Gemini response: {response_text[:100]}...")
            
            # Parse the response
            decision_result = self._parse_response(response_text)
            
            return decision_result
            
        except Exception as e:
            print(f"❌ Error in make_decision: {e}")
            return {
                'decision': 'HOLD',
                'confidence': 50,
                'reasoning': f'Error occurred: {str(e)}',
                'model_used': 'gemini-2.5-pro'
            }

    def _parse_response(self, response_text):
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
            
            # Extract reasoning
            reasoning_match = re.search(r'REASONING:\s*(.+)', response_text, re.DOTALL)
            if reasoning_match:
                reasoning = reasoning_match.group(1).strip()
            
            result = {
                'decision': decision,
                'confidence': confidence,
                'reasoning': reasoning,
                'model_used': 'gemini-2.5-pro',
                'raw_response': response_text
            }
            
            print(f"✅ Parsed: {decision} ({confidence}%)")
            return result
            
        except Exception as e:
            print(f"❌ Parse error: {e}")
            return {
                'decision': 'HOLD',
                'confidence': 50,
                'reasoning': f'Parse error: {str(e)}',
                'model_used': 'gemini-2.5-pro'
            } 