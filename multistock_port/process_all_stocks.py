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

def process_stock(symbol: str, data_dir: str = ".", start_date: str = "2025-07-01", end_date: str = "2025-10-01"):
    """Process a single stock through all agents."""
    print(f"\nProcessing {symbol}:")
    
    try:
        # Initialize agents with current directory
        valuation_agent = ValuationAgent(data_dir=data_dir)
        fundamental_agent = FundamentalAgent(data_dir=data_dir, start_date=start_date, end_date=end_date)
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
        sentiment = sentiment_agent.analyze_sentiment(symbol, end_date)  # Use end_date for analysis
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
    parser.add_argument("--data-dir", default=".", help="Data directory (defaults to current directory)")
    parser.add_argument("--start-date", default="2025-07-01", help="Start date for analysis (YYYY-MM-DD)")
    parser.add_argument("--end-date", default="2025-10-01", help="End date for analysis (YYYY-MM-DD)")
    args = parser.parse_args()
    
    print(f"Analysis Date Range: {args.start_date} to {args.end_date}")
    print(f"Data Directory: {args.data_dir}")
    
    if args.symbol:
        # Process single stock
        print(f"Processing single stock: {args.symbol}")
        print("=" * 40)
        process_stock(args.symbol, data_dir=args.data_dir, start_date=args.start_date, end_date=args.end_date)
    else:
        # Process all stocks
        print(f"Starting processing of {len(STOCKS)} stocks")
        print("=" * 40)
        
        successful = []
        failed = []
        
        for symbol in STOCKS:
            if process_stock(symbol, data_dir=args.data_dir, start_date=args.start_date, end_date=args.end_date):
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
