"""
Reasoning Agent
==============

Aggregates and analyzes outputs from Valuation, Fundamental, and Sentiment agents
to make final trading decisions using LLM reasoning.
"""

import os
import json
from typing import Dict, Optional, List
from datetime import datetime
from data_utils import DataManager
import openai
import openai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class ReasoningAgent:
    """
    Meta-agent that combines analyses from other agents and makes final trading decisions
    using LLM-based reasoning that considers all available information.
    """
    
    def __init__(self, data_dir: str = ".", api_key: Optional[str] = None):
        """
        Initialize the Reasoning Agent
        
        Args:
            data_dir: Base directory containing analysis data
            api_key: OpenAI API key. If None, will try to get from OPENAI_API_KEY environment variable
        """
        self.data_manager = DataManager(base_dir=data_dir)
        self.output_dir = "reasoning_decisions"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Directories for other agents' analysis files
        self.valuation_dir = "valuation_reports"
        self.fundamental_dir = "fundamental_reports"
        self.sentiment_dir = "sentiment_data"
        
        # Initialize OpenAI client
        openai.api_key = api_key or os.getenv("OPENAI_API_KEY")
    
    def _load_latest_analysis(self, symbol: str, analysis_type: str, directory: str) -> Optional[Dict]:
        """Load the latest analysis file of a specific type"""
        try:
            # Look for analysis files matching the pattern
            pattern = f"{symbol}_{analysis_type}_analysis_*.json"
            files = []
            
            # List all matching files in the directory
            for file in os.listdir(directory):
                if file.startswith(f"{symbol}_{analysis_type}_analysis_") and file.endswith(".json"):
                    files.append(os.path.join(directory, file))
            
            if not files:
                print(f"No {analysis_type} analysis found for {symbol}")
                return None
            
            # Sort by modification time to get the latest
            latest_file = max(files, key=os.path.getmtime)
            
            with open(latest_file, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            print(f"Error loading {analysis_type} analysis: {str(e)}")
            return None
    
    def _load_all_analyses(self, symbol: str) -> Dict:
        """Load latest analyses from all agents"""
        analyses = {
            'valuation': self._load_latest_analysis(symbol, 'technical', self.valuation_dir),
            'fundamental': self._load_latest_analysis(symbol, 'fundamental', self.fundamental_dir),
            'sentiment': self._load_latest_analysis(symbol, 'sentiment', self.sentiment_dir)
        }
        
        # Add metadata
        analyses['meta'] = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'available_analyses': [k for k, v in analyses.items() if v is not None and k != 'meta']
        }
        
        return analyses
    
    def _prepare_llm_prompt(self, analyses: Dict) -> str:
        """Prepare prompt for LLM reasoning"""
        symbol = analyses['valuation_analysis']['symbol']
        date = analyses['date']
        
        prompt = f"""
You are a master trading strategist tasked with making a final trading decision for {symbol} stock on {date}.
You have access to the following analyses:

"""
        # Add valuation analysis
        valuation = analyses['valuation_analysis']
        prompt += f"""
TECHNICAL ANALYSIS:
- Current Price: ${valuation.get('current_price', 0):.2f}
- Price Trends:
  * Daily Change: {valuation.get('price_trends', {}).get('daily_change', 0):.1%}
  * 5-Day Change: {valuation.get('price_trends', {}).get('five_day_change', 0):.1%}
  * Monthly Change: {valuation.get('price_trends', {}).get('monthly_change', 0):.1%}
- Volume: {valuation.get('volume_analysis', {}).get('volume_ratio', 0):.1f}x average
- Beta: {valuation.get('volatility', {}).get('beta', 0):.2f}
- Technical Analysis: {valuation.get('gpt_analysis', 'No analysis available')}
"""

        # Add fundamental analysis
        fundamental = analyses['fundamental_analysis']
        company_info = fundamental.get('company_info', {})
        fund_analysis = fundamental.get('fundamental_analysis', {})
        profitability = fund_analysis.get('profitability', {}).get('metrics', {})
        financial_health = fund_analysis.get('financial_health', {}).get('metrics', {})
        valuation_metrics = fund_analysis.get('valuation_metrics', {}).get('metrics', {})
        recommendation = fundamental.get('trading_recommendation', {})
        
        prompt += f"""
FUNDAMENTAL ANALYSIS:
- Company Info:
  * Name: {company_info.get('company_name', 'Unknown')}
  * Sector: {company_info.get('sector', 'Unknown')}
  * Market Cap: ${company_info.get('market_cap', 0):,.0f}
- Profitability:
  * Revenue: ${profitability.get('revenue', 0):,.0f}
  * Net Income: ${profitability.get('net_income', 0):,.0f}
  * Net Profit Margin: {profitability.get('net_profit_margin', 0):.1%}
- Financial Health:
  * Current Ratio: {financial_health.get('current_ratio', 0):.2f}
  * Debt/Equity: {financial_health.get('debt_to_equity', 0):.2f}
- Valuation:
  * P/E Ratio: {valuation_metrics.get('pe_ratio', 0):.2f}
  * EPS: ${valuation_metrics.get('eps', 0):.2f}
- Recommendation: {recommendation.get('recommendation', 'No recommendation available')}
"""

        # Add sentiment analysis
        sentiment = analyses['sentiment_analysis']
        price_context = sentiment.get('price_context', {})
        news_data = sentiment.get('news_data', {})
        current_analysis = sentiment.get('current_analysis', {})
        
        prompt += f"""
        
SENTIMENT ANALYSIS:
- Price Context:
  * Current Price: ${price_context.get('current_price', 0):.2f}
  * Volume: {price_context.get('volume', 0):,.0f}
- News Analysis: {len(news_data.get('news_data', {}).get('news', []))} articles analyzed
- Sentiment Decision:
  * Decision: {current_analysis.get('decision', 'No decision')}
  * Confidence: {current_analysis.get('confidence', 0)}%
  * Reasoning: {current_analysis.get('reasoning', 'No reasoning available')}
"""

        prompt += """
Based on all available analyses, please provide:
1. A final risk neutral trading decision (BUY, SELL, or HOLD)
2. Confidence level (0-100%)
3. Comprehensive reasoning that considers all available data
4. Key risks to your recommendation

Your response should follow this exact format:
DECISION: [BUY/SELL/HOLD]
CONFIDENCE: [0-100]
REASONING:
[Your detailed reasoning here, considering all available analyses]
KEY RISKS:
- [Risk 1]
- [Risk 2]
- [Risk 3]
"""
        return prompt
    
    def _call_llm(self, prompt: str) -> Optional[str]:
        """
        Call LLM API for reasoning
        
        Args:
            prompt: The prepared prompt for analysis
            
        Returns:
            The LLM's response as a string, or None if the call fails
        """
        try:
            response = openai.ChatCompletion.create(
                model="o3",
                messages=[
                    {"role": "system", "content": "You are a professional stock market analyst and trading strategist. Your task is to analyze market data and make trading decisions based on technical, fundamental, and sentiment analysis."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=2000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error calling API: {str(e)}")
            return None
    
    def _parse_llm_response(self, response: str) -> Dict:
        """Parse LLM response into structured format"""
        if not response:
            return {
                'decision': 'HOLD',
                'confidence': 0,
                'reasoning': 'Failed to get LLM response',
                'risks': []
            }
            
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
            print(f"Error parsing LLM response: {str(e)}")
            return {
                'decision': 'HOLD',
                'confidence': 0,
                'reasoning': 'Failed to parse LLM response',
                'risks': []
            }
    
    def make_decision(self, symbol: str, analyses: Dict) -> Optional[Dict]:
        """
        Make final trading decision based on all available analyses
        
        Args:
            symbol: Stock symbol to analyze
            analyses: Dictionary containing all agent analyses and date
            
        Returns:
            Dictionary containing final decision and reasoning
        """
        try:
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
            self.data_manager.save_analysis_result(
                symbol=symbol,
                analysis_data=final_decision,
                analysis_type='reasoning',
                output_dir=self.output_dir
            )
            
            return final_decision
            
        except Exception as e:
            print(f"Error making decision for {symbol}: {str(e)}")
            return None

def main():
    """Example usage of ReasoningAgent"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Make final trading decisions using all available analyses")
    parser.add_argument("symbol", help="Stock symbol to analyze")
    parser.add_argument("--data-dir", default=".", help="Base directory containing analysis data")
    parser.add_argument("--api-key", help="OpenAI API key. If not provided, will try to use OPENAI_API_KEY environment variable")
    
    args = parser.parse_args()
    
    agent = ReasoningAgent(data_dir=args.data_dir, api_key=args.api_key)
    # The original main function called agent.make_decision(args.symbol)
    # This will now require passing analyses to the make_decision method.
    # For a simple example, we'll just call it without analyses for now,
    # but in a real scenario, you'd load analyses first.
    # For now, we'll simulate loading analyses or pass a dummy structure.
    # A more robust example would involve loading all analysis files for the symbol.
    
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
        print(f"\nFinal Decision for {args.symbol}:")
        print(f"Action: {decision['decision']}")
        print(f"Confidence: {decision['confidence']}%")
        print("\nReasoning:")
        print(decision['reasoning'])
        print("\nKey Risks:")
        for risk in decision['risks']:
            print(f"- {risk}")
    else:
        print(f"Could not make decision for {args.symbol}")

if __name__ == "__main__":
    main() 