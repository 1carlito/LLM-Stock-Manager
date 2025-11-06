"""
ReasoningAgent.py: Final decision maker that integrates analyses from all other agents
"""

import os
import json
import re
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env in the same directory as this script
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(dotenv_path=env_path)

# Load OpenAI API key - fallback only (should be passed via api_key_override in parallel mode)
# In parallel mode, ParallelOrchestrator passes API keys directly to each ReasoningAgent instance
api_key = None
# Try STOCK_*_OPENAI_API_KEY keys first (used by ParallelOrchestrator)
for i in range(1, 21):
    key = os.getenv(f"STOCK_{i}_OPENAI_API_KEY")
    if key:
        api_key = key
        break

# Fallback to OPENAI_API_KEY_* if STOCK keys not found
if not api_key:
    for i in range(1, 21):
        key = os.getenv(f"OPENAI_API_KEY_{i}")
        if key:
            api_key = key
            break

# Only raise error if no keys found at all (for non-parallel usage)
# In parallel mode, api_key_override will always be provided

MODEL_NAME = "gpt-5"  # Using GPT-5 for advanced reasoning

class ReasoningAgent:
    def __init__(self, data_dir=".", api_key_override=None):
        self.data_dir = data_dir
        self.decision_save_dir = os.path.join(self.data_dir, "reasoning_decisions_GPT")
        self.model = MODEL_NAME
        
        # Use override API key if provided (always used in parallel mode)
        # Fallback to STOCK_*_OPENAI_API_KEY keys for non-parallel usage
        self.api_key = api_key_override
        if not self.api_key:
            # Try STOCK_*_OPENAI_API_KEY keys first (used by ParallelOrchestrator)
            for i in range(1, 21):
                key = os.getenv(f"STOCK_{i}_OPENAI_API_KEY")
                if key:
                    self.api_key = key
                    break
            # Fallback to OPENAI_API_KEY_* if STOCK keys not found
            if not self.api_key:
                for i in range(1, 21):
                    key = os.getenv(f"OPENAI_API_KEY_{i}")
                    if key:
                        self.api_key = key
                        break
        if not self.api_key:
            raise ValueError("No API key provided. In parallel mode, ParallelOrchestrator passes keys via api_key_override. For standalone usage, set STOCK_1_OPENAI_API_KEY through STOCK_20_OPENAI_API_KEY in .env")
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.api_key)
        print(f"✅ ReasoningAgent initialized with {self.model}")

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
                
            print(f"📞 Calling OpenAI API for {symbol}...")
            
            response = self._call_claude_api(prompt)
            
            print(f"✅ Got OpenAI response for {symbol}")
            decision_result = self._parse_response(response, symbol, current_date)
            self._save_decision(decision_result)
            return decision_result
        except Exception as e:
            print(f"❌ OpenAI API Error for {symbol}: {e}")
            return {
                "symbol": symbol,
                "date": current_date,
                "decision": "HOLD",
                "confidence": 0.5,
                "reasoning": f"Error: {str(e)}",
                "model_used": MODEL_NAME
            }
            
    def _save_decision(self, decision_result):
        """Save the decision to a JSON file in the decision_save_dir"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(self.decision_save_dir, exist_ok=True)
            
            # Format the filename with symbol and timestamp
            symbol = decision_result.get('symbol', 'unknown')
            date_str = decision_result.get('date')
            if hasattr(date_str, 'strftime'):
                date_str = date_str.strftime('%Y%m%d')
            else:
                # If date_str is already a string, ensure it's formatted consistently
                date_str = datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y%m%d')
            
            timestamp = datetime.now().strftime('%H%M%S')
            filename = f"{symbol}_reasoning_analysis_{date_str}_{timestamp}.json"
            file_path = os.path.join(self.decision_save_dir, filename)
            
            # Save the decision to file
            with open(file_path, 'w') as f:
                json.dump(decision_result, f, indent=2)
            
            print(f"✅ Decision saved to {file_path}")
        except Exception as e:
            print(f"❌ Error saving decision: {e}")
            # Don't raise exception - this is non-critical functionality

    def _call_claude_api(self, prompt: str) -> str:
        """Call OpenAI API with the given prompt"""
        try:
            response = self.client.responses.create(
                model=self.model,
                input=prompt,
                max_output_tokens=4000,
            )
            
            if response and getattr(response, "output_text", None):
                return response.output_text
            else:
                raise Exception("Empty response from OpenAI API")
                
        except Exception as e:
            print(f"❌ Error calling OpenAI API: {e}")
            raise e

    def _build_decision_prompt(self, symbol, current_date, valuation_data, fundamental_data, sentiment_data, previous_decisions=None):
        """Build a prompt that integrates sentiment and valuation analyses for decision making"""
        
        # Format date if it's a datetime object
        date_str = current_date
        if hasattr(current_date, 'strftime'):
            date_str = current_date.strftime('%Y-%m-%d')
        
        # Build the base prompt with both sentiment and valuation analyses
        prompt = f"""
You are a professional trading agent analyzing {symbol} on {date_str}.

SENTIMENT ANALYSIS:
{json.dumps(sentiment_data, indent=2) if sentiment_data else "No sentiment data available"}

VALUATION ANALYSIS:
{json.dumps(valuation_data, indent=2) if valuation_data else "No valuation data available"}
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
        
        # Add final instructions for integrating sentiment and valuation analyses
        prompt += f"""

Based on BOTH the sentiment analysis AND valuation analysis, make a trading decision:
1. Analyze the sentiment signals, confidence levels, and market sentiment trends
2. Consider the valuation metrics, price targets, and technical indicators
3. Look for agreement or disagreement between sentiment and valuation analyses
4. Evaluate the strength and reliability of both types of signals
5. Consider how this decision fits with the previous trading history (if provided)
6. Be more decisive when both sentiment and valuation signals align

IMPORTANT: You should integrate insights from BOTH sentiment and valuation analyses. When they agree, this strengthens the signal. When they disagree, carefully weigh the evidence from each source.

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
                'model_used': MODEL_NAME,
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
                'model_used': MODEL_NAME
            }