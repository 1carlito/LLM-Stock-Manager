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
            
        self.data_dir = data_dir
        self.data_manager = DataManager(base_dir=data_dir)
        self.output_dir = os.path.join(data_dir, "valuation_reports")
        os.makedirs(self.output_dir, exist_ok=True)

    def _load_stock_data(self, symbol: str, target_date: Optional[str] = None) -> Optional[Dict]:
        """Load and filter technical data for a stock for a specific date"""
        try:
            raw_data = self.data_manager.load_stock_data(symbol)
            if not raw_data:
                return None
            
            # If no target_date provided, use default behavior (first available data)
            if target_date is None:
                # Use the first available price data
                filtered_prices = raw_data['historical_prices']
                if not filtered_prices:
                    return None
                # Sort by date ascending to get the earliest data
                filtered_prices.sort(key=lambda x: x['date'])
                current_price = filtered_prices[0]['close']
                target_data = filtered_prices[0]
            else:
                # Find data for the specific target date
                target_data = None
                for price_data in raw_data['historical_prices']:
                    if price_data['date'] == target_date:
                        target_data = price_data
                        break
                
                if not target_data:
                    # If exact date not found, find the closest date before target_date
                    available_dates = [p for p in raw_data['historical_prices'] if p['date'] <= target_date]
                    if not available_dates:
                        return None
                    available_dates.sort(key=lambda x: x['date'], reverse=True)
                    target_data = available_dates[0]
                
                current_price = target_data['close']
            
            # Get historical context (30 days before target date)
            all_prices = raw_data['historical_prices']
            all_prices.sort(key=lambda x: x['date'])
            
            # Find the index of our target data
            target_index = None
            for i, price_data in enumerate(all_prices):
                if price_data['date'] == target_data['date']:
                    target_index = i
                    break
            
            if target_index is None:
                return None
            
            # Get up to 30 days of historical data before target date
            historical_start = max(0, target_index - 29)
            historical_prices = all_prices[historical_start:target_index + 1]
            
            # Calculate price changes
            price_change_1d = target_data['changePercent'] / 100 if 'changePercent' in target_data else 0
            
            price_change_5d = None
            if len(historical_prices) > 5:
                five_days_ago = historical_prices[-6]
                price_change_5d = (current_price - five_days_ago['close']) / five_days_ago['close']
            
            price_change_1m = None
            if len(historical_prices) > 20:
                month_ago = historical_prices[-21]
                price_change_1m = (current_price - month_ago['close']) / month_ago['close']
            
            technical_data = {
                'symbol': raw_data['symbol'],
                'current_price': current_price,
                'date': target_data['date'],
                'historical_prices': historical_prices,
                'price_change_1d': price_change_1d,
                'price_change_5d': price_change_5d,
                'price_change_1m': price_change_1m,
                'volume': target_data['volume'],
                'avg_volume': sum(p['volume'] for p in historical_prices[-20:]) / min(20, len(historical_prices)),
                'beta': raw_data.get('beta', 1.0),
                'sector': raw_data.get('sector', 'Unknown')
            }
            return technical_data
                
        except Exception as e:
            print(f"Error loading data for {symbol}: {str(e)}")
            return None

    def analyze_valuation(self, symbol: str, date=None) -> Optional[Dict]:
        """
        Analyze valuation for a specific stock and date.
        This method is called by the backtest orchestrator.
        
        Args:
            symbol: Stock symbol to analyze
            date: Target date for analysis (pandas Timestamp or string)
            
        Returns:
            Dict with valuation analysis or None if no data available
        """
        # Convert date to string format if it's a pandas Timestamp
        target_date = None
        if date is not None:
            if hasattr(date, 'strftime'):
                target_date = date.strftime('%Y-%m-%d')
            else:
                target_date = str(date)
        
        return self.prepare_analysis_data(symbol, target_date)

    def _analyze_with_gpt(self, analysis_data: Dict) -> Dict:
        """Use GPT-3.5 to analyze the valuation data"""
        try:
            prompt = f"""Analyze the following stock data and provide insights:
            Symbol: {analysis_data['symbol']}
            Sector: {analysis_data['sector']}
            Current Price: ${analysis_data['current_price']}
            Date: {analysis_data.get('date', 'N/A')}
            Price Changes:
            - Daily: {analysis_data['price_trends']['daily_change']:.2%}
            - 5 Day: {analysis_data['price_trends']['five_day_change']:.2%} if available
            - Monthly: {analysis_data['price_trends']['monthly_change']:.2%} if available
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

    def prepare_analysis_data(self, symbol: str, target_date: Optional[str] = None) -> Optional[Dict]:
        """Prepare technical analysis data for LLM"""
        data = self._load_stock_data(symbol, target_date)
        if not data:
            return None

        current_volume = data['volume']
        avg_volume = data['avg_volume']
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
        
        analysis_data = {
            'symbol': data['symbol'],
            'sector': data['sector'],
            'current_price': data['current_price'],
            'date': data.get('date'),
            'price_trends': {
                'daily_change': data['price_change_1d'] or 0,
                'five_day_change': data['price_change_5d'] or 0,
                'monthly_change': data['price_change_1m'] or 0
            },
            'volume_analysis': {
                'current_volume': current_volume,
                'average_volume': avg_volume,
                'volume_ratio': volume_ratio
            },
            'volatility': {
                'beta': data['beta']
            },
            'historical_data': data['historical_prices'][-30:]  # Last 30 days
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
    parser.add_argument("--date", help="Target date for analysis (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    agent = ValuationAgent(data_dir=args.data_dir)
    analysis = agent.prepare_analysis_data(args.symbol, args.date)
    
    if analysis:
        print(f"\nAnalysis completed for {args.symbol}")
        print(f"Date: {analysis.get('date', 'N/A')}")
        print(f"Current Price: ${analysis['current_price']:.2f}")
        print(f"Daily Change: {analysis['price_trends']['daily_change']:.2%}")
        print(f"Volume Ratio: {analysis['volume_analysis']['volume_ratio']:.2f}x average")
        agent.save_analysis(args.symbol, analysis)
    else:
        print(f"Could not analyze {args.symbol}")

if __name__ == "__main__":
    main() 