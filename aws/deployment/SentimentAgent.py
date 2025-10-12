#!/usr/bin/env python3
"""
Sentiment Analysis Agent
=======================

Analyzes news sentiment and price data to make trading decisions.
Maintains history of decisions and reasoning for continuous learning.
"""

import os
import json
import glob
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
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
        self.output_dir = "sentiment_data"
        self.news_data_dir = "news_data"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize OpenAI client for sentiment analysis
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OpenAI API key is required")
        
        openai.api_key = openai_api_key
        self.model = "gpt-3.5-turbo"  # Using GPT-3.5 for sentiment analysis

    def _parse_news_date(self, date_str: str) -> Optional[datetime]:
        """Parse news date string into datetime object."""
        try:
            # Try DD/MM/YYYY format
            return datetime.strptime(date_str, "%d/%m/%Y")
        except ValueError:
            try:
                # Try YYYY-MM-DD format
                return datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                print(f"Warning: Could not parse date string: {date_str}")
                return None

    def _filter_news_by_date(self, news_data: Dict, current_date: str) -> Dict:
        """Filter news to only include articles up to the current trading date."""
        try:
            current_dt = datetime.strptime(current_date, "%Y-%m-%d")
            filtered_data = news_data.copy()
            
            # Filter news for each symbol
            for symbol in filtered_data.get('parsed_results', {}).keys():
                if 'news' in filtered_data['parsed_results'][symbol]:
                    filtered_news = []
                    for article in filtered_data['parsed_results'][symbol]['news']:
                        article_date = self._parse_news_date(article['date'])
                        if article_date and article_date <= current_dt:
                            filtered_news.append(article)
                    
                    filtered_data['parsed_results'][symbol]['news'] = filtered_news
                    print(f"Filtered news for {symbol}: {len(filtered_news)} articles on or before {current_date}")
            
            return filtered_data
            
        except Exception as e:
            print(f"Error filtering news by date: {str(e)}")
            return news_data

    def _load_manual_news_data(self, symbol: str, current_date: str) -> Optional[Dict]:
        """Load manually scraped news data for a stock up to current_date"""
        try:
            # Look for the latest manual news file for this symbol
            pattern = os.path.join(self.news_data_dir, f"{symbol}_manual_news_*.json")
            news_files = glob.glob(pattern)
            
            if not news_files:
                print(f"No manual news data found for {symbol}")
                return None
            
            # Get the latest file (by timestamp in filename)
            latest_file = max(news_files, key=os.path.getctime)
            
            with open(latest_file, 'r') as f:
                news_data = json.load(f)
            
            # Filter news by date
            filtered_news = self._filter_news_by_date(news_data, current_date)
            
            print(f"Loaded and filtered news data from {latest_file}")
            return filtered_news
            
        except Exception as e:
            print(f"Error loading manual news data for {symbol}: {str(e)}")
            return None

    def _prepare_sentiment_prompt(self, price_data: Dict, news_data: Dict, previous_decisions: List[Dict]) -> str:
        """Prepare prompt for sentiment analysis"""
        
        # Extract news summary from the manual data
        news_summary = ""
        symbol = price_data['symbol']
        if 'parsed_results' in news_data and symbol in news_data['parsed_results']:
            stock_news = news_data['parsed_results'][symbol]
            if 'news' in stock_news:
                news_summary = "Recent News Headlines:\n"
                for article in stock_news['news'][:5]:  # Show top 5 articles
                    news_summary += f"- {article['title']} ({article['date']})\n"
        
        prompt = f"""
You are a financial analyst specializing in news sentiment analysis. Analyze the following data for {price_data['symbol']} stock:

1. Current Price Data:
- Current Price: ${price_data['current_price']}
- Volume: {price_data.get('volume_analysis', {}).get('current_volume', 0):,}

2. Recent News:
{news_summary if news_summary else 'No news summary available'}

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
                    # Capture multi-line reasoning
                    reasoning_lines = []
                    for next_line in response_text.split('\n')[response_text.split('\n').index(line)+1:]:
                        if next_line.strip() and not next_line.startswith(('DECISION:', 'CONFIDENCE:')):
                            reasoning_lines.append(next_line.strip())
                        else:
                            break
                    if reasoning_lines:
                        reasoning = ' '.join(reasoning_lines)
            
            return {
                'decision': decision,
                'confidence': confidence,
                'reasoning': reasoning
            }
            
        except Exception as e:
            print(f"Error getting LLM analysis: {str(e)}")
            return None

    def analyze_sentiment(self, symbol: str, current_date: str = None, valuation_data: Dict = None) -> Optional[Dict]:
        """
        Analyze sentiment for a stock using news and price data.
        
        Args:
            symbol: Stock symbol to analyze
            current_date: Current trading date (YYYY-MM-DD)
            valuation_data: Optional pre-loaded valuation data
            
        Returns:
            Dictionary containing sentiment analysis and decision
        """
        try:
            # Get current price data from valuation data
            if not valuation_data:
                print(f"No valuation data provided for {symbol}")
                return None
            
            price_data = {
                'symbol': symbol,
                'current_price': valuation_data.get('current_price', 0),
                'volume_analysis': valuation_data.get('volume_analysis', {})
            }
            
            # Load news data
            news_data = self._load_manual_news_data(symbol, current_date)
            if not news_data:
                print(f"No news data available for {symbol}")
                return None
            
            # Load previous decisions
            previous_decisions = []
            pattern = os.path.join(self.output_dir, f"{symbol}_sentiment_analysis_*.json")
            decision_files = glob.glob(pattern)
            
            if decision_files:
                latest_decision = max(decision_files, key=os.path.getctime)
                try:
                    with open(latest_decision, 'r') as f:
                        prev_data = json.load(f)
                        if 'previous_decisions' in prev_data:
                            previous_decisions = prev_data['previous_decisions']
                except Exception as e:
                    print(f"Error loading previous decisions: {str(e)}")
            
            # Prepare analysis prompt
            prompt = self._prepare_sentiment_prompt(price_data, news_data, previous_decisions)
            
            # Get sentiment analysis
            analysis = self._analyze_with_llm(prompt)
            if not analysis:
                print(f"Failed to get sentiment analysis for {symbol}")
                return None
            
            # Prepare final analysis data
            analysis_data = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'price_context': price_data,
                'news_data': news_data,
                'previous_decisions': previous_decisions,
                'current_analysis': {
                    'decision': analysis['decision'],
                    'confidence': analysis['confidence'],
                    'reasoning': analysis['reasoning'],
                    'price_at_decision': price_data['current_price']
                }
            }
            
            # Save analysis
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{symbol}_sentiment_analysis_{timestamp}.json"
            filepath = os.path.join(self.output_dir, filename)
            
            os.makedirs(self.output_dir, exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(analysis_data, f, indent=2)
            
            print(f"Analysis saved to {filepath}")
            return analysis_data
            
        except Exception as e:
            print(f"Error analyzing sentiment for {symbol}: {str(e)}")
            return None

def main():
    """Example usage of SentimentAgent"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze stock sentiment")
    parser.add_argument("symbol", help="Stock symbol to analyze")
    parser.add_argument("--data-dir", default=".", help="Base directory for data")
    
    args = parser.parse_args()
    
    agent = SentimentAgent(data_dir=args.data_dir)
    analysis = agent.analyze_sentiment(args.symbol)
    
    if analysis:
        print(f"\nSentiment Analysis for {args.symbol}:")
        print(f"Decision: {analysis['current_analysis']['decision']}")
        print(f"Confidence: {analysis['current_analysis']['confidence']}%")
        print("\nReasoning:")
        print(analysis['current_analysis']['reasoning'])
    else:
        print(f"Could not analyze sentiment for {args.symbol}")

if __name__ == "__main__":
    main()
