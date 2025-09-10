"""
Process All Stocks
================

Process collected stock data through all agents to create initial analyses.
"""

import os
import json
from datetime import datetime
from typing import List

from ValuationAgent import ValuationAgent
from FundamentalAgent import FundamentalAgent
from SentimentAgent import SentimentAgent

# List of all stocks to process
STOCKS = [
    # Technology
    "GOOGL", "NVDA", "PLTR",
    # Health and Pharma
    "ABBV", "TMO", "UNH",
    # Financial Services
    "JPM", "BAC", "WFC",
    # Energy
    "XOM", "CVX", "COP"
]

def process_stock(symbol: str):
    """Process a single stock through all agents."""
    print(f"\nProcessing {symbol}:")
    
    try:
        # Initialize agents
        valuation_agent = ValuationAgent()
        fundamental_agent = FundamentalAgent()
        sentiment_agent = SentimentAgent()
        
        # Run analyses
        print("- Running valuation analysis...")
        valuation = valuation_agent.prepare_analysis_data(symbol)
        if valuation:
            valuation_agent.save_analysis(symbol, valuation)
            print("  ✓ Valuation analysis complete")
        
        print("- Running fundamental analysis...")
        fundamental = fundamental_agent.prepare_fundamental_analysis(symbol)
        if fundamental:
            fundamental_agent.save_analysis(symbol, fundamental)
            print("  ✓ Fundamental analysis complete")
        
        print("- Running sentiment analysis...")
        sentiment = sentiment_agent.analyze_sentiment(symbol)
        if sentiment:
            print("  ✓ Sentiment analysis complete")
        
        if all([valuation, fundamental, sentiment]):
            print(f"✅ Successfully processed {symbol}")
            return True
        else:
            print(f"⚠️  Some analyses failed for {symbol}")
            return False
            
    except Exception as e:
        print(f"❌ Error processing {symbol}: {str(e)}")
        return False

def main():
    """Process all stocks through the agents."""
    print(f"Starting processing of {len(STOCKS)} stocks")
    print("=" * 40)
    
    successful = []
    failed = []
    
    for symbol in STOCKS:
        if process_stock(symbol):
            successful.append(symbol)
        else:
            failed.append(symbol)
    
    print("\nProcessing Complete")
    print("=" * 40)
    print(f"Successful: {len(successful)}/{len(STOCKS)}")
    if successful:
        print("Successful stocks:", ", ".join(successful))
    if failed:
        print("Failed stocks:", ", ".join(failed))

if __name__ == "__main__":
    main() 