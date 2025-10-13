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
import pandas_market_calendars as mcal

from ValuationAgent import ValuationAgent
from FundamentalAgent import FundamentalAgent
# from SentimentAgent import SentimentAgent  # ABLATION: Not needed for valuation+fundamental only test

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

def process_stock(symbol: str, data_dir: str = ".", start_date: str = "2025-07-01", end_date: str = "2025-10-01", fundamental_interval: int = 5):
    """Process a single stock through all agents."""
    print(f"\nProcessing {symbol}:")
    print(f"  Fundamental analysis interval: Every {fundamental_interval} trading days")
    
    try:
        # Initialize agents with current directory
        valuation_agent = ValuationAgent(data_dir=data_dir)
        fundamental_agent = FundamentalAgent(data_dir=data_dir, start_date=start_date, end_date=end_date)
        # sentiment_agent = SentimentAgent(data_dir=data_dir)  # ABLATION: Commented out for valuation+fundamental only
        
        # Get trading calendar to determine analysis dates
        nyse = mcal.get_calendar('NYSE')
        trading_days = nyse.schedule(start_date=start_date, end_date=end_date)
        
        # Select every Nth trading day for fundamental analysis
        fundamental_dates = []
        for i, trading_date in enumerate(trading_days.index):
            if i % fundamental_interval == 0:
                fundamental_dates.append(trading_date.strftime('%Y-%m-%d'))
        
        print(f"  Fundamental analysis dates ({len(fundamental_dates)}): {', '.join(fundamental_dates[:5])}...")
        
        # Generate DAILY valuation analyses
        all_trading_dates = [d.strftime('%Y-%m-%d') for d in trading_days.index]
        print(f"\n- Generating {len(all_trading_dates)} valuation analyses (daily)...")
        successful_valuations = 0
        for i, target_date in enumerate(all_trading_dates, 1):
            result = valuation_agent.analyze_valuation(symbol, target_date)
            if result:
                successful_valuations += 1
                if i % 10 == 0:
                    print(f"  Progress: {i}/{len(all_trading_dates)}")
        print(f"  ✓ {successful_valuations}/{len(all_trading_dates)} valuation analyses complete")
        
        # Run fundamental analyses on multiple dates (every 5 days)
        print(f"\n- Generating {len(fundamental_dates)} fundamental analyses (every {fundamental_interval} days)...")
        fundamental_results = fundamental_agent.analyze_fundamentals_multi_date(symbol, fundamental_dates)
        successful_fundamentals = sum(1 for r in fundamental_results if r is not None)
        print(f"  ✓ {successful_fundamentals}/{len(fundamental_dates)} fundamental analyses complete")
        
        # ABLATION: Sentiment analysis commented out for valuation+fundamental only test
        
        if successful_valuations > 0 and successful_fundamentals > 0:
            print(f"✅ Successfully processed {symbol}")
            print(f"   Valuation: {successful_valuations} analyses")
            print(f"   Fundamental: {successful_fundamentals} analyses")
            return True
        else:
            print(f"⚠️  Analysis generation incomplete for {symbol}")
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
    parser.add_argument("--fundamental-interval", type=int, default=5, help="Generate fundamental analysis every N trading days")
    args = parser.parse_args()
    
    print(f"Analysis Date Range: {args.start_date} to {args.end_date}")
    print(f"Data Directory: {args.data_dir}")
    print(f"Fundamental Analysis Interval: Every {args.fundamental_interval} trading days")
    
    if args.symbol:
        # Process single stock
        print(f"Processing single stock: {args.symbol}")
        print("=" * 40)
        process_stock(args.symbol, data_dir=args.data_dir, start_date=args.start_date, end_date=args.end_date, fundamental_interval=args.fundamental_interval)
    else:
        # Process all stocks
        print(f"Starting processing of {len(STOCKS)} stocks")
        print("=" * 40)
        
        successful = []
        failed = []
        
        for symbol in STOCKS:
            if process_stock(symbol, data_dir=args.data_dir, start_date=args.start_date, end_date=args.end_date, fundamental_interval=args.fundamental_interval):
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
