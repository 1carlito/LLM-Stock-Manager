#!/usr/bin/env python3
"""
Sentiment Analysis Agent
=======================

Analyzes news sentiment and price data to make trading decisions.
Maintains history of decisions and reasoning for continuous learning.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
from llm_news_search import LLMNewsSearcher
from data_utils import DataManager
import openai

class SentimentAgent:
    """
    Agent that analyzes news sentiment and price data to make trading decisions.
    Maintains context of previous decisions for continuous learning.
    """

    def __init__(self, data_dir: str = "."):
        """
        Initialize the Sentiment Agent
        
        Args:
            data_dir: Directory to store sentiment data
        """
        load_dotenv()
        self.data_manager = DataManager(base_dir=data_dir)
        self.output_dir = "sentiment_data"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize OpenAI client for both news search and sentiment analysis
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OpenAI API key is required")
        
        # Use same client for both news search and sentiment analysis
        openai.api_key = openai_api_key
        self.news_searcher = LLMNewsSearcher(api_key=openai_api_key)
        self.model = "gpt-3.5-turbo"  # Using GPT-3.5 for sentiment analysis

    def _prepare_sentiment_prompt(self, price_data: Dict, news_data: Dict, previous_decisions: List[Dict]) -> str:
        """Prepare prompt for sentiment analysis"""
        prompt = f"""
You are a financial analyst specializing in news sentiment analysis. Analyze the following data for {price_data['symbol']} stock:

1. Current Price Data:
- Current Price: ${price_data['current_price']}
- Open: ${price_data['open_price']}
- High: ${price_data['high_price']}
- Low: ${price_data['low_price']}
- Close: ${price_data['close_price']}
- Volume: {price_data['volume']:,}

2. Recent News:
{news_data['summary'] if 'summary' in news_data else 'No news summary available'}

3. Previous Decisions:
"""
        if previous_decisions:
            for decision in previous_decisions[-3:]:  # Show last 3 decisions
                prompt += f"""
- {decision['timestamp']}: {decision['decision']} (Confidence: {decision['confidence']}%)
  Reasoning: {decision['reasoning']}
  Price then: ${decision['price_at_decision']}
"""
        else:
            prompt += "No previous decisions available.\n"
            
        prompt += """
Based on this data, provide:
1. A clear BUY/SELL/HOLD decision
2. Confidence level (0-100)
3. Clear reasoning based on the news and price data

Format your response exactly as:
DECISION: [BUY/SELL/HOLD]
CONFIDENCE: [0-100]
REASONING: [Your detailed analysis here]
"""
        return prompt

    def _analyze_with_llm(self, prompt: str) -> Optional[Dict]:
        """Get sentiment analysis from GPT-3.5"""
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial analyst specializing in news sentiment analysis. Provide clear, well-reasoned trading decisions."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_completion_tokens=1000
            )
            
            # Parse response
            response_text = response.choices[0].message.content
            
            # Extract decision components
            decision = None
            confidence = 0
            reasoning = ""
            
            for line in response_text.split('\n'):
                if line.startswith('DECISION:'):
                    decision = line.replace('DECISION:', '').strip()
                elif line.startswith('CONFIDENCE:'):
                    try:
                        confidence = int(line.replace('CONFIDENCE:', '').strip())
                    except ValueError:
                        confidence = 0
                elif line.startswith('REASONING:'):
                    reasoning = line.replace('REASONING:', '').strip()
                    # Include any following lines in reasoning
                    reasoning_lines = []
                    for next_line in response_text.split('\n')[response_text.split('\n').index(line)+1:]:
                        if next_line.strip() and not next_line.startswith(('DECISION:', 'CONFIDENCE:')):
                            reasoning_lines.append(next_line.strip())
                    if reasoning_lines:
                        reasoning = ' '.join(reasoning_lines)
            
            return {
                'decision': decision or 'HOLD',
                'confidence': confidence,
                'reasoning': reasoning or 'No clear reasoning provided'
            }
            
        except Exception as e:
            print(f"Error getting LLM analysis: {str(e)}")
            return None

    def analyze_sentiment(self, symbol: str) -> Optional[Dict]:
        """Analyze news sentiment and make trading decision"""
        try:
            # Get current price data
            price_data = self._load_stock_data(symbol)
            if not price_data:
                return None
            
            # Get news data
            print(f"Fetching news for {symbol}...")
            news_data = self.news_searcher.search_individual_stock(symbol)
            if not news_data:
                print(f"No news found for {symbol}")
                return None
            
            # Load previous decisions for context
            previous_decisions = self._load_previous_decisions(symbol)
            
            # Prepare prompt and get LLM analysis
            prompt = self._prepare_sentiment_prompt(price_data, news_data, previous_decisions)
            llm_analysis = self._analyze_with_llm(prompt)
            
            if not llm_analysis:
                return None
            
            # Prepare analysis data
            analysis_data = {
                'price_context': price_data,
                'news_data': news_data,
                'previous_decisions': previous_decisions[-5:] if previous_decisions else [],
                'current_analysis': llm_analysis
            }
            
            # Save current analysis
            self.save_analysis(symbol, analysis_data)
            
            # Save the decision
            self.save_llm_decision(symbol, llm_analysis)
            
            return analysis_data
            
        except Exception as e:
            print(f"Error analyzing sentiment for {symbol}: {str(e)}")
            return None

    def _load_stock_data(self, symbol: str) -> Optional[Dict]:
        """Load latest price data for a stock"""
        try:
            raw_data = self.data_manager.load_stock_data(symbol)
            if not raw_data:
                return None
            
            # Extract price data
            price_data = {
                'symbol': raw_data['symbol'],
                'company_name': raw_data['company_name'],
                'current_price': raw_data['current_price'],
                'open_price': raw_data['historical_prices'][0]['open'],
                'high_price': raw_data['historical_prices'][0]['high'],
                'low_price': raw_data['historical_prices'][0]['low'],
                'close_price': raw_data['historical_prices'][0]['close'],
                'volume': raw_data['volume']
            }
            
            return price_data
            
        except Exception as e:
            print(f"Error loading data for {symbol}: {str(e)}")
            return None

    def _load_previous_decisions(self, symbol: str) -> List[Dict]:
        """Load previous trading decisions for context"""
        decisions_file = os.path.join(self.output_dir, f"{symbol}_decisions.json")
        if not os.path.exists(decisions_file):
            return []
            
        try:
            with open(decisions_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading previous decisions: {str(e)}")
            return []

    def save_llm_decision(self, symbol: str, llm_response: Dict):
        """Save LLM's trading decision and reasoning"""
        decision_data = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'decision': llm_response['decision'],
            'confidence': llm_response['confidence'],
            'reasoning': llm_response['reasoning'],
            'price_at_decision': self._load_stock_data(symbol)['current_price']
        }
        
        self._save_decision(symbol, decision_data)
        print(f"Decision saved for {symbol}")

    def _save_decision(self, symbol: str, decision_data: Dict):
        """Save trading decision and reasoning"""
        decisions_file = os.path.join(self.output_dir, f"{symbol}_decisions.json")
        
        # Load existing decisions
        decisions = self._load_previous_decisions(symbol)
        
        # Add new decision
        decisions.append(decision_data)
        
        # Save updated decisions
        try:
            with open(decisions_file, 'w') as f:
                json.dump(decisions, f, indent=2)
        except Exception as e:
            print(f"Error saving decision: {str(e)}")

    def save_analysis(self, symbol: str, analysis_data: Dict):
        """Save sentiment analysis to file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{symbol}_sentiment_analysis_{timestamp}.json"
            filepath = os.path.join(self.output_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(analysis_data, f, indent=2)
            
            print(f"Analysis saved to {filepath}")
        except Exception as e:
            print(f"Error saving analysis: {str(e)}")

def main():
    """Example usage of SentimentAgent"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze news sentiment for trading decisions")
    parser.add_argument("symbol", help="Stock symbol to analyze")
    parser.add_argument("--data-dir", default=".", help="Directory containing stock data")
    
    args = parser.parse_args()
    
    # Initialize agent and analyze sentiment
    agent = SentimentAgent(data_dir=args.data_dir)
    analysis = agent.analyze_sentiment(args.symbol)
    
    if analysis:
        print(f"\nAnalysis completed for {args.symbol}")
        print(f"Decision: {analysis['current_analysis']['decision']}")
        print(f"Confidence: {analysis['current_analysis']['confidence']}%")
        print("\nReasoning:")
        print(analysis['current_analysis']['reasoning'])
        print(f"\nNews articles analyzed: {len(analysis['news_data'])}")
        print(f"Previous decisions considered: {len(analysis['previous_decisions'])}")
    else:
        print(f"Could not analyze {args.symbol}")

if __name__ == "__main__":
    main()
