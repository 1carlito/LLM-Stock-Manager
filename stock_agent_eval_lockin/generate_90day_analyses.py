#!/usr/bin/env python3
"""
Generate 90-day analyses for all stocks
"""

import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from ValuationAgent import ValuationAgent
from FundamentalAgent import FundamentalAgent
from SentimentAgent import SentimentAgent

# Load environment variables
load_dotenv()

def generate_analyses():
    """Generate all analyses for the 90-day period"""
    
    # Load the collected data
    with open('backtest_data_90days/stock_data_20250909_164019.json', 'r') as f:
        stock_data = json.load(f)
    
    with open('backtest_data_90days/financial_data_20250909_164019.json', 'r') as f:
        financial_data = json.load(f)
    
    # Initialize agents
    valuation_agent = ValuationAgent(data_dir="backtest_data_90days")
    fundamental_agent = FundamentalAgent(data_dir="backtest_data_90days")
    sentiment_agent = SentimentAgent(data_dir="backtest_data_90days")
    
    # Get all symbols
    symbols = list(stock_data.keys())
    print(f"Generating analyses for {len(symbols)} stocks: {symbols}")
    
    # Generate analyses for each symbol
    for symbol in symbols:
        print(f"\n📈 Processing {symbol}...")
        
        try:
            # Generate valuation analysis
            print(f"  - Generating valuation analysis...")
            valuation_result = valuation_agent.prepare_analysis_data(symbol)
            if valuation_result:
                valuation_agent.save_analysis(symbol, valuation_result)
                print(f"    ✅ Valuation analysis saved")
            else:
                print(f"    ❌ Valuation analysis failed")
            
            # Generate fundamental analysis
            print(f"  - Generating fundamental analysis...")
            fundamental_result = fundamental_agent.prepare_fundamental_analysis(symbol)
            if fundamental_result:
                fundamental_agent.save_analysis(symbol, fundamental_result)
                print(f"    ✅ Fundamental analysis saved")
            else:
                print(f"    ❌ Fundamental analysis failed")
            
            # Generate sentiment analysis
            print(f"  - Generating sentiment analysis...")
            sentiment_result = sentiment_agent.analyze_sentiment(symbol)
            if sentiment_result:
                sentiment_agent.save_analysis(symbol, sentiment_result)
                print(f"    ✅ Sentiment analysis saved")
            else:
                print(f"    ❌ Sentiment analysis failed")
                
        except Exception as e:
            print(f"    ❌ Error processing {symbol}: {str(e)}")
    
    print(f"\n🎉 Analysis generation complete!")

if __name__ == "__main__":
    generate_analyses()
