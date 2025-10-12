"""
Process All Stocks
================

Process collected stock data through all agents to create initial analyses.
"""

import os
import json
import argparse
from datetime import datetime
from typing import List

from ValuationAgent import ValuationAgent
from FundamentalAgent import FundamentalAgent
from SentimentAgent import SentimentAgent

# List of all stocks to process - Core 7 stocks for focused analysis
STOCKS = [
    "GOOGL",  # Alphabet Inc.
    "NVDA",   # NVIDIA Corporation  
    "PLTR",   # Palantir Technologies Inc.
    "ABBV",   # AbbVie Inc.
    "UNH",    # UnitedHealth Group Incorporated
    "JPM",    # JPMorgan Chase & Co.
    "RKLB"    # Rocket Lab USA, Inc.
]

def process_stock(symbol: str):
    """Process a single stock through all agents."""
    print(f"\nProcessing {symbol}:")
    
    try:
        # Initialize agents with live_trades directory
        data_dir = "live_trades"
        valuation_agent = ValuationAgent(data_dir=data_dir)
        fundamental_agent = FundamentalAgent(data_dir=data_dir)
        sentiment_agent = SentimentAgent(data_dir=data_dir)
        
        # Run analyses
        print("- Running valuation analysis...")
        valuation = valuation_agent.prepare_analysis_data(symbol)
        if valuation:
            valuation_agent.save_analysis(symbol, valuation)
            print("  ✓ Valuation analysis complete")
        
        # Run fundamental analysis
        print("- Running fundamental analysis...")
        fundamental_result = fundamental_agent.analyze_fundamentals(symbol)
        if fundamental_result:
            print("  ✓ Fundamental analysis complete")
        else:
            print("  ✗ Fundamental analysis failed")
            failed = True
        
        print("- Running sentiment analysis...")
        sentiment = sentiment_agent.analyze_sentiment(symbol, "2025-09-19")  # Updated to present date
        if sentiment:
            print("  ✓ Sentiment analysis complete")
        
        if all([valuation, fundamental_result, sentiment]):
            print(f"✅ Successfully processed {symbol}")
            return True
        else:
            print(f"⚠️  Some analyses failed for {symbol}")
            return False
            
    except Exception as e:
        print(f"❌ Error processing {symbol}: {str(e)}")
        return False

def main():
    """Process stocks through the agents."""
    parser = argparse.ArgumentParser(description="Process stock data through analysis agents")
    parser.add_argument("--symbol", help="Process a single stock symbol")
    args = parser.parse_args()
    
    if args.symbol:
        # Process single stock
        print(f"Processing single stock: {args.symbol}")
        print("=" * 40)
        process_stock(args.symbol)
    else:
        # Process all stocks
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
