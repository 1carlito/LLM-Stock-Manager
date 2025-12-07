"""
ReasoningAgent.py: Final decision maker that integrates analyses from all other agents
"""

import os
import json
import re
import time
from datetime import datetime
from dotenv import load_dotenv
import requests

# Load environment variables from .env in the same directory as this script
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(dotenv_path=env_path)

# Gather default API token (parallel orchestrator typically overrides this)
DEFAULT_API_TOKEN = os.getenv("DEEPSEEK_API_KEY_1")

MODEL_NAME = "deepseek-ai/DeepSeek-V3.1-Terminus"
CHUTES_API_URL = os.getenv("CHUTES_API_URL", "https://llm.chutes.ai/v1/chat/completions")

class ReasoningAgent:
    def __init__(self, data_dir=".", api_key_override=None):
        self.data_dir = data_dir
        self.decision_save_dir = os.path.join(self.data_dir, "reasoning_decisions_DSeek_2.0")
        self.model = MODEL_NAME
        
        # Use override API token if provided (parallel mode), otherwise fallback to env
        self.api_key = api_key_override or DEFAULT_API_TOKEN
        if not self.api_key:
            raise ValueError(
                "No API token provided. Pass api_key_override or set DEEPSEEK_API_KEY_1 in the environment."
            )
        
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
                
            print(f"📞 Calling Chutes DeepSeek API for {symbol}...")
            
            response = self._call_chutes_api(prompt)
            
            print(f"✅ Got DeepSeek response for {symbol}")
            decision_result = self._parse_response(response, symbol, current_date, fundamental_data=fundamental_data)
            self._save_decision(decision_result)
            return decision_result
        except Exception as e:
            print(f"❌ DeepSeek API Error for {symbol}: {e}")
            return {
                "symbol": symbol,
                "date": current_date,
                "decision": "NEUTRAL",
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

    def _call_chutes_api(self, prompt: str) -> str:
        """Call the Chutes DeepSeek endpoint and return the combined text response."""
        # Add a delay before API call to reduce rate limiting
        # (in addition to the 0.5s stagger per request in ParallelOrchestrator)
        time.sleep(2.0)
        
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are the best trading advisor in the world."},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "max_tokens": 3300,
            "temperature": 0.7,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Retry logic with exponential backoff for rate limiting (429), service unavailable (503), and timeouts
        max_retries = 5
        base_delay = 3.0
        
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
                        # Exponential backoff: 3s, 6s, 12s, 24s, 48s
                        delay = base_delay * (2 ** attempt)
                        status_msg = "rate limited (429)" if response.status_code == 429 else "service unavailable (503)"
                        print(f"⚠️ {status_msg} for ReasoningAgent, retrying in {delay:.1f}s... (attempt {attempt + 1}/{max_retries})")
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
                    print(f"⚠️ Timeout for ReasoningAgent, retrying in {delay:.1f}s... (attempt {attempt + 1}/{max_retries})")
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
                    print(f"⚠️ {status_msg} for ReasoningAgent, retrying in {delay:.1f}s... (attempt {attempt + 1}/{max_retries})")
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

    def _build_decision_prompt(self, symbol, current_date, valuation_data, fundamental_data, sentiment_data, previous_decisions=None):
        """Build a prompt that integrates sentiment and valuation analyses for decision making"""
        
        # Format date if it's a datetime object
        date_str = current_date
        if hasattr(current_date, 'strftime'):
            date_str = current_date.strftime('%Y-%m-%d')
        
        # Build the base prompt with both sentiment and valuation analyses
        prompt = f"""
You are the highest level market trader in existence, you constantly make extremely good returns. Analyze {symbol} on {date_str} and make a trading decision based on the analysis data provided below.

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

DECISION OPTIONS:
- BUY: Stock is undervalued or has strong positive signals - recommend buying/long position
- SELL: Stock is overvalued or has strong negative signals - recommend exiting or avoiding
- NEUTRAL: Signals are truly mixed/neutral - no clear edge found, no actionable signal
- MAINTAIN: Thesis is still intact (positive signals or negative signals remain), but not enough new edge to add new positions

DECISION LOGIC:
1. Analyze the sentiment analysis signals, fundamental analysis signals, and valuation analysis signals.
2. Evaluate the strength and reliability of the analysis signals.
3. Consider how this decision fits with the previous trading history (if provided).
4. Be more decisive when the analysis signals are strong.
5. Take into account previous decisions when selecting MAINTAIN as there may have been BUY decisions previously that are still intact, but not enough signal to add new positions
6. The Portfolio Manager will handle position management (e.g., converting SELL on unowned stocks to SHORT actions).


SHORT CONFIDENCE (for SELL decisions):
- If you output SELL, also assess your confidence for shorting this stock (0-100)
- This helps the Portfolio Manager decide whether to short if the stock is not owned
- Example: "I have 85% confidence of shorting this stock" or "Short confidence: 75%"

Provide your decision in this format:
DECISION: [BUY/SELL/NEUTRAL/MAINTAIN]
CONFIDENCE: [1-100]
SHORT_CONFIDENCE: [0-100] (only for SELL decisions, your confidence in shorting this stock)
REASONING: [Brief explanation of your decision, key factors considered, risk assessment, and short confidence rationale if SELL]
"""
        
        return prompt

    def _parse_response(self, response_text, symbol, current_date, fundamental_data=None):
        """Parse the LLM response to extract decision, confidence, and reasoning."""
        try:
            # Initialize default values
            decision = "NEUTRAL"  # Default to NEUTRAL (no edge found)
            confidence = 50
            reasoning = "Unable to parse response"
            
            # Extract decision - look for DECISION: followed by BUY/SELL/NEUTRAL/MAINTAIN (same line only)
            # Use [ \t]* instead of \s* to avoid matching across newlines
            decision_match = re.search(r'DECISION:[ \t]*(\w+)', response_text, re.IGNORECASE)
            if decision_match:
                extracted_decision = decision_match.group(1).upper()
                decision = extracted_decision
                # Validate decision is one of the allowed options
                valid_decisions = ['BUY', 'SELL', 'NEUTRAL', 'MAINTAIN']
                if decision not in valid_decisions:
                    print(f"⚠️ Invalid decision '{extracted_decision}' extracted from response, defaulting to NEUTRAL")
                    print(f"Debug: Matched text: '{decision_match.group(0)}' | Extracted value: '{extracted_decision}'")
                    decision = "NEUTRAL"
            else:
                print(f"⚠️ No DECISION: pattern found in response, defaulting to NEUTRAL")
            
            # Extract confidence
            confidence_match = re.search(r'CONFIDENCE:\s*(\d+)', response_text)
            if confidence_match:
                confidence = int(confidence_match.group(1))
                confidence_normalized = confidence / 100.0  # Normalize to 0-1 range
            else:
                confidence_normalized = 0.5
            
            # Extract short confidence (for SELL decisions)
            short_confidence_normalized = None
            if decision == 'SELL':
                short_confidence_match = re.search(r'SHORT_CONFIDENCE:\s*(\d+)', response_text, re.IGNORECASE)
                if short_confidence_match:
                    short_confidence = int(short_confidence_match.group(1))
                    short_confidence_normalized = short_confidence / 100.0
                else:
                    # Try to extract from reasoning text
                    reasoning_text = response_text.lower()
                    short_conf_patterns = [
                        r'(\d+)%\s*confidence.*short',
                        r'short.*confidence.*(\d+)%',
                        r'confidence.*short.*(\d+)'
                    ]
                    for pattern in short_conf_patterns:
                        match = re.search(pattern, reasoning_text)
                        if match:
                            short_confidence_normalized = int(match.group(1)) / 100.0
                            break
                    # If still not found, use main confidence as fallback
                    if short_confidence_normalized is None:
                        short_confidence_normalized = confidence_normalized
            
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
            
            # Add short_confidence for SELL decisions
            if decision == 'SELL' and short_confidence_normalized is not None:
                result['short_confidence'] = short_confidence_normalized
            
            # Extract sector and industry from fundamental_data (if available)
            try:
                if fundamental_data:
                    sector = fundamental_data.get('Sector') or fundamental_data.get('sector')
                    industry = fundamental_data.get('Industry') or fundamental_data.get('industry')
                    if sector:
                        result['sector'] = sector
                    if industry:
                        result['industry'] = industry
            except Exception:
                pass  # Non-critical, continue without sector/industry
            
            print(f"✅ Parsed: {decision} (confidence: {confidence}%)")
            return result
            
        except Exception as e:
            print(f"❌ Parse error: {e}")
            return {
                'symbol': symbol,
                'date': current_date,
                'decision': "NEUTRAL",
                'confidence': 0.5,
                'reasoning': f'Parse error: {str(e)}',
                'model_used': MODEL_NAME
            }
    
    def apply_waterfall_allocation(self, decision, portfolio_state, stock_decisions=None):
        """
        Apply waterfall allocation to a single decision.
        
        This function takes a decision from make_decision() and applies waterfall allocation
        to determine the actual dollar amount to allocate, considering cash constraints.
        
        Args:
            decision: Decision dict from make_decision() with 'action', 'symbol', 'confidence', etc.
            portfolio_state: Current portfolio state with 'cash', 'last_prices', 'market_caps', etc.
            stock_decisions: Optional list of all stock decisions for confidence-based sorting
        
        Returns:
            Decision dict with 'amount_usd' field updated based on waterfall allocation.
            For SELL/COVER/CLOSE actions, amount_usd may be 0 (means close full position).
        
        Note:
            - SELL = closing long positions (selling shares you own)
            - COVER = closing short positions (buying back shares you shorted)
            - CLOSE = generic term that could mean either
        """
        from waterfall_allocator import allocate_decisions
        
        # Convert single decision to list format for allocator
        decisions_list = [decision.copy()]
        
        # Apply waterfall allocation
        allocated_decisions = allocate_decisions(
            decisions_list=decisions_list,
            portfolio_state=portfolio_state,
            stock_decisions=stock_decisions if stock_decisions else [decision],
            per_trade_cap_pct=0.25,  # 25% of remaining cash per trade
            short_cap_pct=0.25,       # 25% for short positions
            cash_threshold_pct=0.25, # Block shorts when cash < 25% of initial
            initial_value=portfolio_state.get('initial_value', 100000)
        )
        
        # Return the allocated decision (should be only one)
        if allocated_decisions:
            return allocated_decisions[0]
        else:
            # If allocation failed, return decision with amount_usd = 0
            decision['amount_usd'] = 0
            return decision