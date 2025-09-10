#!/usr/bin/env python3
"""
Valuation Agent for Technical Stock Analysis
===========================================

This module provides a valuation agent that analyzes technical indicators,
price patterns, and volume trends to determine whether a stock is reasonably
priced and to identify potential buying or selling opportunities.
"""

import os
import json
from typing import Dict, Optional
from datetime import datetime
from dotenv import load_dotenv
import openai
from data_utils import DataManager

# Load environment variables
load_dotenv()

class ValuationAgent:
    """
    Valuation Agent for Technical Analysis of Stock Data
    Filters and prepares technical data for LLM analysis
    """

    def __init__(self, data_dir: str = "."):
        # Configure OpenAI
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        openai.api_key = api_key or os.getenv("OPENAI_API_KEY")
            
        self.data_manager = DataManager(base_dir=data_dir)
        self.output_dir = "valuation_reports"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Set cutoff date
        self.cutoff_date = datetime.strptime("2025-08-10", "%Y-%m-%d")

    def _load_stock_data(self, symbol: str) -> Optional[Dict]:
        """Load and filter technical data for a stock"""
        try:
            raw_data = self.data_manager.load_stock_data(symbol)
            if not raw_data:
                return None
            
            # Filter historical prices before cutoff
            filtered_prices = []
            for price_data in raw_data['historical_prices']:
                date = datetime.strptime(price_data['date'], "%Y-%m-%d")
                if date <= self.cutoff_date:
                    filtered_prices.append(price_data)
            
            # Sort by date descending
            filtered_prices.sort(key=lambda x: x['date'], reverse=True)
            
            technical_data = {
                'symbol': raw_data['symbol'],
                'current_price': filtered_prices[0]['close'],
                'historical_prices': filtered_prices[:30],  # Last 30 days
                'price_change_1d': filtered_prices[0]['changePercent'] / 100,
                'price_change_5d': (filtered_prices[0]['close'] - filtered_prices[5]['close']) / filtered_prices[5]['close'] if len(filtered_prices) > 5 else None,
                'price_change_1m': (filtered_prices[0]['close'] - filtered_prices[20]['close']) / filtered_prices[20]['close'] if len(filtered_prices) > 20 else None,
                'volume': filtered_prices[0]['volume'],
                'avg_volume': sum(p['volume'] for p in filtered_prices[:20]) / min(20, len(filtered_prices)),
                'beta': raw_data['beta'],
                'sector': raw_data['sector']
            }
            return technical_data
                
        except Exception as e:
            print(f"Error loading data for {symbol}: {str(e)}")
            return None

    def _analyze_with_gpt(self, analysis_data: Dict) -> Dict:
        """Use GPT-3.5 to analyze the valuation data"""
        try:
            prompt = f"""Analyze the following stock data and provide insights:
            Symbol: {analysis_data['symbol']}
            Sector: {analysis_data['sector']}
            Current Price: ${analysis_data['current_price']}
            Price Changes:
            - Daily: {analysis_data['price_trends']['daily_change']:.2%}
            - 5 Day: {analysis_data['price_trends']['five_day_change']:.2%}
            - Monthly: {analysis_data['price_trends']['monthly_change']:.2%}
            Volume Ratio: {analysis_data['volume_analysis']['volume_ratio']:.2f}x average
            Beta: {analysis_data['volatility']['beta']}

            Please provide:
            1. Technical analysis of price trends
            2. Volume analysis and its implications
            3. Risk assessment based on beta and price movements
            4. Overall valuation recommendation
            """

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional stock analyst focusing on technical analysis and valuation."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )

            analysis_data['gpt_analysis'] = response.choices[0].message.content
            return analysis_data
            
        except Exception as e:
            print(f"Error during GPT analysis: {str(e)}")
            analysis_data['gpt_analysis'] = f"Error during analysis: {str(e)}"
            return analysis_data

    def prepare_analysis_data(self, symbol: str) -> Optional[Dict]:
        """Prepare technical analysis data for LLM"""
        data = self._load_stock_data(symbol)
        if not data:
            return None

        current_volume = data['volume']
        avg_volume = data['avg_volume']
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
        
        analysis_data = {
            'symbol': data['symbol'],
            'sector': data['sector'],
            'current_price': data['current_price'],
            'price_trends': {
                'daily_change': data['price_change_1d'],
                'five_day_change': data['price_change_5d'],
                'monthly_change': data['price_change_1m']
            },
            'volume_analysis': {
                'current_volume': current_volume,
                'average_volume': avg_volume,
                'volume_ratio': volume_ratio
            },
            'volatility': {
                'beta': data['beta']
            },
            'historical_data': data['historical_prices'][:30]  # Last 30 days
        }
        
        # Get GPT analysis
        analysis_data = self._analyze_with_gpt(analysis_data)
        return analysis_data

    def save_analysis(self, symbol: str, analysis_data: Dict):
        """Save technical analysis results"""
        if not analysis_data:
            return
        
        self.data_manager.save_analysis_result(
            symbol=symbol,
            analysis_data=analysis_data,
            analysis_type='technical',
            output_dir=self.output_dir
        )

def main():
    """Example usage of ValuationAgent"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Technical analysis for stock valuation")
    parser.add_argument("symbol", help="Stock symbol to analyze")
    parser.add_argument("--data-dir", default=".", help="Directory containing stock data")
    
    args = parser.parse_args()
    
    agent = ValuationAgent(data_dir=args.data_dir)
    analysis = agent.prepare_analysis_data(args.symbol)
    
    if analysis:
        print(f"\nAnalysis completed for {args.symbol}")
        print(f"Current Price: ${analysis['current_price']:.2f}")
        print(f"Daily Change: {analysis['price_trends']['daily_change']:.2%}")
        print(f"Volume Ratio: {analysis['volume_analysis']['volume_ratio']:.2f}x average")
        agent.save_analysis(args.symbol, analysis)
    else:
        print(f"Could not analyze {args.symbol}")

if __name__ == "__main__":
    main() 