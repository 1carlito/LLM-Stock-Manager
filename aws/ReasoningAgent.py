"""
Reasoning Agent
=============

Makes final trading decisions by analyzing outputs from all other agents.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional, List, Any
from dotenv import load_dotenv
import openai

class ReasoningAgent:
    """
    Makes final trading decisions by analyzing all available data.
    Uses LLM to reason about valuation, fundamental, and sentiment analyses.
    """
    
    def __init__(self, data_dir: str = ".", api_key: str = None):
        """
        Initialize reasoning agent.
        
        Args:
            data_dir: Base directory for data files
            api_key: OpenAI API key (optional, will use env var if not provided)
        """
        load_dotenv()
        self.data_dir = data_dir
        
        # Set up logging
        self.logger = logging.getLogger('reasoning_agent')
        self.logger.setLevel(logging.INFO)
        
        # Create logs directory if it doesn't exist
        log_dir = os.path.join(data_dir, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # File handler
        file_handler = logging.FileHandler(os.path.join(log_dir, 'reasoning_agent.log'))
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Set up OpenAI client
        openai.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            raise ValueError("OpenAI API key is required")
            
        self.output_dir = os.path.join(data_dir, "reasoning_decisions")
        os.makedirs(self.output_dir, exist_ok=True)
    
    def _prepare_llm_prompt(self, analyses: Dict) -> str:
        """
        Prepare prompt for LLM reasoning.
        
        Args:
            analyses: Dictionary containing all agent analyses
            
        Returns:
            Formatted prompt string
        """
        # Extract components
        valuation = analyses['valuation_analysis']
        fundamental = analyses['fundamental_analysis']
        sentiment = analyses['sentiment_analysis']
        date = analyses['date']
        
        # Build prompt
        prompt = f"""
You are a professional stock market analyst and trading strategist.
Today is {date}. Please analyze the following data and make a trading decision:

VALUATION ANALYSIS:
- Current Price: ${valuation.get('current_price', 0):.2f}
- Price Trends:
  * Daily Change: {valuation.get('price_trends', {}).get('daily_change', 0):.1%}
  * 5-Day Change: {valuation.get('price_trends', {}).get('five_day_change', 0):.1%}
  * Monthly Change: {valuation.get('price_trends', {}).get('monthly_change', 0):.1%}
- Volume: {valuation.get('volume_analysis', {}).get('current_volume', 0):,.0f} ({valuation.get('volume_analysis', {}).get('volume_ratio', 0):.1f}x average)
- Market Cap: ${fundamental.get('company_info', {}).get('market_cap', 0):,.0f}
- P/E Ratio: {fundamental.get('fundamental_analysis', {}).get('valuation_metrics', {}).get('metrics', {}).get('pe_ratio', 0):.1f}
- Beta: {valuation.get('volatility', {}).get('beta', 0):.2f}

FUNDAMENTAL ANALYSIS:
- Financial Health:
  * Revenue: ${fundamental.get('fundamental_analysis', {}).get('profitability', {}).get('metrics', {}).get('revenue', 0):,.0f}
  * Net Income: ${fundamental.get('fundamental_analysis', {}).get('profitability', {}).get('metrics', {}).get('net_income', 0):,.0f}
  * Profit Margin: {fundamental.get('fundamental_analysis', {}).get('profitability', {}).get('metrics', {}).get('net_profit_margin', 0):.1%}
  * Debt/Equity: {fundamental.get('fundamental_analysis', {}).get('financial_health', {}).get('metrics', {}).get('debt_to_equity', 0):.2f}
- Growth:
  * Revenue Growth: {fundamental.get('fundamental_analysis', {}).get('profitability', {}).get('metrics', {}).get('revenue_growth', 0):.1%}
  * Net Income Growth: {fundamental.get('fundamental_analysis', {}).get('profitability', {}).get('metrics', {}).get('net_income_growth', 0):.1%}
- Valuation:
  * EPS: ${fundamental.get('fundamental_analysis', {}).get('valuation_metrics', {}).get('metrics', {}).get('eps', 0):.2f}
  * Dividend Yield: {fundamental.get('fundamental_analysis', {}).get('valuation_metrics', {}).get('metrics', {}).get('dividend_yield', 0):.1%}

SENTIMENT ANALYSIS:
- Current Price: ${sentiment.get('price_context', {}).get('current_price', 0):.2f}
- Volume: {sentiment.get('price_context', {}).get('volume', 0):,.0f}
- Recent News:
"""
        # Add recent news headlines
        news = sentiment.get('news_data', {}).get('parsed_results', {}).get(valuation['symbol'], {}).get('news', [])
        for article in news[:3]:  # Show top 3 headlines
            prompt += f"  * {article.get('title', 'No title')} ({article.get('date', 'No date')})\n"
        
        # Add fundamental recommendation
        prompt += f"\nFUNDAMENTAL RECOMMENDATION:\n{fundamental.get('trading_recommendation', {}).get('recommendation', 'No recommendation available')}\n"
        
        prompt += """
Based on this comprehensive analysis, please provide:
1. A clear BUY/SELL/HOLD decision
2. Confidence level (0-100%)
3. Detailed reasoning that considers all available data
4. Key risks to your recommendation

Format your response exactly as:
DECISION: [BUY/SELL/HOLD]
CONFIDENCE: [0-100]
REASONING:
[Your detailed reasoning here]
KEY RISKS:
- [Risk 1]
- [Risk 2]
- [Risk 3]
"""
        return prompt
    
    def _call_llm(self, prompt: str) -> Optional[str]:
        """
        Call LLM API for reasoning.
        
        Args:
            prompt: The prepared prompt for analysis
            
        Returns:
            The LLM's response as a string, or None if the call fails
        """
        try:
            self.logger.info("\n🤖 Calling o3 API for reasoning...")
            self.logger.info("=" * 50)
            self.logger.info("\nPrompt:")
            self.logger.info("-" * 30)
            self.logger.info(prompt)
            self.logger.info("-" * 30)
            
            # Log API configuration
            self.logger.info(f"Using API key ending in: ...{openai.api_key[-4:]}")
            self.logger.info("Making API call with model: o3")
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional stock market analyst and trading strategist. Your task is to analyze market data and make trading decisions based on technical, fundamental, and sentiment analysis."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000
            )
            
            self.logger.info("\n✅ API call successful!")
            self.logger.info("Response:")
            self.logger.info("-" * 30)
            self.logger.info(response.choices[0].message.content)
            self.logger.info("-" * 30)
            return response.choices[0].message.content
            
        except Exception as e:
            error_msg = f"❌ Error calling API: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error("API call details:")
            self.logger.error(f"  - Model: o3")
            self.logger.error(f"  - API key present: {'Yes' if openai.api_key else 'No'}")
            self.logger.error(f"  - Error type: {type(e).__name__}")
            self.logger.error(f"  - Full error: {str(e)}")
            raise RuntimeError(error_msg) from e
    
    def _parse_llm_response(self, response: str) -> Dict:
        """Parse LLM response into structured format"""
        if not response:
            error_msg = "No response from LLM to parse"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
            
        try:
            # Split response into sections
            sections = response.split('\n')
            
            # Extract decision
            decision_line = next((line for line in sections if line.startswith('DECISION:')), '')
            decision = decision_line.replace('DECISION:', '').strip()
            
            # Extract confidence
            confidence_line = next((line for line in sections if line.startswith('CONFIDENCE:')), '')
            confidence = int(confidence_line.replace('CONFIDENCE:', '').strip())
            
            # Extract reasoning
            reasoning_start = response.find('REASONING:')
            risks_start = response.find('KEY RISKS:')
            reasoning = response[reasoning_start:risks_start].replace('REASONING:', '').strip()
            
            # Extract risks
            risks_section = response[risks_start:].replace('KEY RISKS:', '').strip()
            risks = [risk.strip('- ').strip() for risk in risks_section.split('\n') if risk.strip().startswith('-')]
            
            return {
                'decision': decision,
                'confidence': confidence,
                'reasoning': reasoning,
                'risks': risks
            }
            
        except Exception as e:
            error_msg = f"Error parsing LLM response: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(f"Response to parse: {response}")
            raise ValueError(error_msg) from e
    
    def make_decision(self, symbol: str, analyses: Dict) -> Optional[Dict]:
        """
        Make final trading decision based on all available analyses.
        
        Args:
            symbol: Stock symbol to analyze
            analyses: Dictionary containing all agent analyses and date
            
        Returns:
            Dictionary containing final decision and reasoning
        """
        try:
            self.logger.info(f"\n📊 Making decision for {symbol}...")
            self.logger.info("=" * 50)
            
            # Prepare prompt for LLM
            prompt = self._prepare_llm_prompt(analyses)
            
            # Get LLM reasoning
            llm_response = self._call_llm(prompt)
            if not llm_response:
                return None
            
            # Parse LLM response
            decision = self._parse_llm_response(llm_response)
            
            # Prepare final decision data
            final_decision = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'date': analyses['date'],
                'decision': decision['decision'],
                'confidence': decision['confidence'],
                'reasoning': decision['reasoning'],
                'risks': decision['risks']
            }
            
            # Save decision
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{symbol}_reasoning_analysis_{timestamp}.json"
            filepath = os.path.join(self.output_dir, filename)
            
            os.makedirs(self.output_dir, exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(final_decision, f, indent=2)
            
            self.logger.info(f"Analysis saved to {filepath}")
            return final_decision
            
        except Exception as e:
            error_msg = f"Error making decision for {symbol}: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg) from e

def main():
    """Example usage of ReasoningAgent"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Make final trading decisions using all available analyses")
    parser.add_argument("symbol", help="Stock symbol to analyze")
    parser.add_argument("--data-dir", default=".", help="Base directory containing analysis data")
    parser.add_argument("--api-key", help="OpenAI API key. If not provided, will try to use OPENAI_API_KEY environment variable")
    
    args = parser.parse_args()
    
    agent = ReasoningAgent(data_dir=args.data_dir, api_key=args.api_key)
    
    # Simulate loading analyses for the example
    analyses = {
        'valuation_analysis': {
            'symbol': args.symbol,
            'current_price': 150.0,
            'price_trends': {'daily_change': 0.02, 'five_day_change': 0.05, 'monthly_change': 0.1},
            'volume_analysis': {'volume_ratio': 1.5},
            'volatility': {'beta': 1.2},
            'gpt_analysis': 'Good technical fundamentals'
        },
        'fundamental_analysis': {
            'company_info': {'company_name': 'Example Corp', 'sector': 'Technology', 'market_cap': 1000000000},
            'profitability': {'revenue': 1000000, 'net_income': 200000, 'net_profit_margin': 0.2},
            'financial_health': {'current_ratio': 1.8, 'debt_to_equity': 0.5},
            'valuation_metrics': {'pe_ratio': 20.0, 'eps': 5.0},
            'trading_recommendation': {'recommendation': 'BUY'}
        },
        'sentiment_analysis': {
            'price_context': {'current_price': 150.0, 'volume': 100000},
            'news_data': {'news_data': {'news': [{'title': 'Good news', 'sentiment': 'positive', 'source': 'News1'}, {'title': 'Bad news', 'sentiment': 'negative', 'source': 'News2'}]}},
            'current_analysis': {'decision': 'BUY', 'confidence': 90, 'reasoning': 'Good fundamentals and positive sentiment'}
        },
        'date': datetime.now().isoformat()
    }
    
    decision = agent.make_decision(args.symbol, analyses)
    
    if decision:
        print("\nFinal Decision:")
        print(json.dumps(decision, indent=2))
    else:
        print("\nNo decision made")

if __name__ == "__main__":
    main()
