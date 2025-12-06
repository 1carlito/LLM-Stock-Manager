"""
llm_strategy.py: LLM-based trading strategy using OpenRouter API.

Uses OpenRouter to support any LLM model with user's own API key.
"""

import requests
import json
from typing import Dict, Any
from .base_strategy import BaseStrategy


class LLMStrategy(BaseStrategy):
    """
    LLM-based trading strategy.
    
    Uses OpenRouter API to call any LLM model.
    User provides their own OpenRouter API key.
    """
    
    def __init__(self, openrouter_api_key: str, model_name: str = "deepseek/deepseek-chat",
                 config: Dict[str, Any] = None):
        """
        Initialize LLM strategy.
        
        Args:
            openrouter_api_key: User's OpenRouter API key
            model_name: Model to use (e.g., "deepseek/deepseek-chat", "openai/gpt-4", "anthropic/claude-3")
            config: Optional additional config
        """
        super().__init__(config)
        self.openrouter_api_key = openrouter_api_key
        self.model_name = model_name
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
    
    def _call_openrouter(self, prompt: str) -> str:
        """
        Call OpenRouter API.
        
        Args:
            prompt: Prompt to send to LLM
        
        Returns:
            LLM response text
        """
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }
        
        response = requests.post(self.api_url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        return result['choices'][0]['message']['content']
    
    def _build_prompt(self, symbol: str, data: Dict[str, Any], 
                     current_date: str, previous_decisions: list = None) -> str:
        """
        Build prompt for LLM based on available data.
        
        Args:
            symbol: Stock symbol
            data: Market data
            current_date: Trading date
            previous_decisions: Previous decisions for this symbol
        
        Returns:
            Formatted prompt string
        """
        prompt = f"""Analyze {symbol} on {current_date} and make a trading decision.

Current Price: ${data.get('current_price', 0):,.2f}
"""
        
        # Add technical indicators if available
        if 'rsi' in data:
            prompt += f"RSI: {data['rsi']:.2f}\n"
        if 'macd' in data:
            prompt += f"MACD: {data.get('macd', 0):.2f}\n"
        
        # Add fundamental data if available
        if 'pe_ratio' in data:
            prompt += f"P/E Ratio: {data['pe_ratio']:.2f}\n"
        if 'revenue_growth' in data:
            prompt += f"Revenue Growth: {data['revenue_growth']*100:.1f}%\n"
        
        # Add sentiment if available
        if 'sentiment_score' in data:
            prompt += f"Sentiment Score: {data['sentiment_score']:.2f}\n"
        
        # Add previous decisions if available
        if previous_decisions:
            prompt += f"\nPrevious Decisions:\n"
            for prev in previous_decisions[-3:]:  # Last 3 decisions
                prompt += f"- {prev.get('date')}: {prev.get('decision')} (confidence: {prev.get('confidence', 0)})\n"
        
        prompt += """
Respond in JSON format:
{
    "decision": "BUY" | "SELL" | "SHORT" | "HOLD" | "NEUTRAL",
    "confidence": 0.0 to 1.0,
    "reasoning": "explanation of decision"
}
"""
        
        return prompt
    
    def _parse_response(self, response_text: str, symbol: str, 
                       current_price: float) -> Dict[str, Any]:
        """
        Parse LLM response into decision dict.
        
        Args:
            response_text: LLM response
            symbol: Stock symbol
            current_price: Current stock price
        
        Returns:
            Decision dict
        """
        try:
            # Try to extract JSON from response
            # Handle common LLM formatting issues
            response_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0]
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0]
            
            # Parse JSON
            decision_data = json.loads(response_text)
            
            return {
                'symbol': symbol,
                'decision': decision_data.get('decision', 'NEUTRAL').upper(),
                'confidence': float(decision_data.get('confidence', 0.5)),
                'reasoning': decision_data.get('reasoning', ''),
                'current_price': current_price
            }
        except Exception as e:
            # Fallback on parse error
            return {
                'symbol': symbol,
                'decision': 'NEUTRAL',
                'confidence': 0.5,
                'reasoning': f'Parse error: {str(e)}',
                'current_price': current_price
            }
    
    def analyze(self, symbol: str, data: Dict[str, Any], 
                portfolio_state: Dict[str, Any], 
                current_date: str) -> Dict[str, Any]:
        """
        Analyze stock using LLM.
        
        Args:
            symbol: Stock symbol
            data: Market data
            portfolio_state: Portfolio state (not used by LLM strategy)
            current_date: Trading date
        
        Returns:
            Decision dict
        """
        current_price = data.get('current_price', 0)
        previous_decisions = data.get('previous_decisions', [])
        
        # Build prompt
        prompt = self._build_prompt(symbol, data, current_date, previous_decisions)
        
        # Call OpenRouter
        try:
            response = self._call_openrouter(prompt)
            decision = self._parse_response(response, symbol, current_price)
            decision['model_used'] = self.model_name
            return decision
        except Exception as e:
            # Fallback on API error
            return {
                'symbol': symbol,
                'decision': 'NEUTRAL',
                'confidence': 0.5,
                'reasoning': f'API error: {str(e)}',
                'current_price': current_price,
                'model_used': self.model_name
            }

