"""
Process All Stocks
================

Process collected stock data through valuation agent to create initial analyses.
Generates valuation analyses for all trading days in the date range.
"""

import os
import json
import argparse
from datetime import datetime, timedelta
from typing import List

# Import only Sentiment and Fundamental agents
from SentimentAgent import SentimentAgent
# from ValuationAgent import ValuationAgent
from FundamentalAgent import FundamentalAgent

# List of stocks to process for backtest
STOCKS = [
    "GOOGL",  # Alphabet Inc.
    "NVDA",   # NVIDIA Corporation  
    "PLTR",   # Palantir Technologies Inc.
    "ABBV",   # AbbVie Inc.
    "UNH",    # UnitedHealth Group Incorporated
    "JPM",    # JPMorgan Chase & Co.
]

def get_trading_days(start_date: str, end_date: str) -> List[str]:
    """Generate trading days (weekdays only) between start and end dates"""
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    trading_days = []
    current = start
    while current <= end:
        # Skip weekends (5=Saturday, 6=Sunday)
        if current.weekday() < 5:
            trading_days.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    
    return trading_days

def process_stock(symbol: str, data_dir: str = ".", start_date: str = "2025-07-01", end_date: str = "2025-10-01"):
    """Process a single stock through all agents for all trading days."""
    print(f"\n{'='*60}")
    print(f"Processing {symbol}")
    print(f"{'='*60}")
    
    try:
        # Initialize sentiment and fundamental agents
        # Prefer historical+fundamental dataset if available, otherwise fall back
        candidate_files = [
            os.path.join(data_dir, "raw_multidata", "stock_data_20251009_163317.json"),
            os.path.join(os.path.dirname(os.path.abspath(data_dir)), "multistock_port", "raw_multidata", "stock_data_20251009_163317.json"),
            os.path.join(data_dir, "stock_data.json"),
        ]
        stock_data_file = next((path for path in candidate_files if os.path.exists(path)), None)
        
        if not stock_data_file:
            print("❌ No stock data file found in expected locations:")
            for path in candidate_files:
                print(f"   - {path}")
            return False
        
        print(f"📄 Using stock data from {stock_data_file}")
        
        sentiment_agent = SentimentAgent(data_dir=data_dir, stock_data_path=stock_data_file)
        fundamental_agent = FundamentalAgent(data_dir=data_dir, stock_data_path=stock_data_file)
        
        # Get all trading days
        trading_days = get_trading_days(start_date, end_date)
        print(f"📅 Generating analyses for {len(trading_days)} trading days: {start_date} to {end_date}")
        print(f"  ✅ Running sentiment and fundamental analyses (skipping valuation)")
        
        # Generate analyses for each trading day
        successful_fundamentals = 0
        successful_sentiments = 0
        
        for i, current_date in enumerate(trading_days, 1):
            if i % 5 == 0 or i == 1:
                print(f"\n📅 Processing date {i}/{len(trading_days)}: {current_date}")
            
            # Run fundamental analysis
            try:
                fundamental = fundamental_agent.analyze_fundamentals(symbol, current_date)
                if fundamental:
                    successful_fundamentals += 1
            except Exception as e:
                print(f"  ❌ Fundamental error for {current_date}: {e}")
                
            # Run sentiment analysis
            try:
                sentiment = sentiment_agent.analyze_sentiment(symbol, current_date)
                if sentiment:
                    successful_sentiments += 1
            except Exception as e:
                print(f"  ❌ Sentiment error for {current_date}: {e}")
        
        print(f"\n✅ Completed processing {symbol}:")
        print(f"   Fundamental: {successful_fundamentals}/{len(trading_days)} analyses")
        print(f"   Sentiment: {successful_sentiments}/{len(trading_days)} analyses")
        
        # Consider successful if at least one type of analysis worked
        if successful_fundamentals > 0 or successful_sentiments > 0:
            return True
        else:
            print(f"⚠️  All analyses failed for {symbol}")
            return False
            
    except Exception as e:
        print(f"❌ Error processing {symbol}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Process stocks through the agents."""
    parser = argparse.ArgumentParser(description="Process stock data through analysis agents")
    parser.add_argument("--symbol", help="Process a single stock symbol")
    parser.add_argument("--data-dir", default=".", help="Data directory (defaults to current directory)")
    parser.add_argument("--start-date", default="2025-07-01", help="Start date for analysis (YYYY-MM-DD)")
    parser.add_argument("--end-date", default="2025-10-01", help="End date for analysis (YYYY-MM-DD)")
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"STOCK ANALYSIS GENERATION")
    print(f"{'='*60}")
    print(f"Date Range: {args.start_date} to {args.end_date}")
    print(f"Data Directory: {args.data_dir}")
    print(f"{'='*60}\n")
    
    if args.symbol:
        # Process single stock
        print(f"Processing single stock: {args.symbol}")
        process_stock(args.symbol, data_dir=args.data_dir, start_date=args.start_date, end_date=args.end_date)
    else:
        # Process all stocks
        print(f"Starting processing of {len(STOCKS)} stocks")
        
        successful = []
        failed = []
        
        for symbol in STOCKS:
            if process_stock(symbol, data_dir=args.data_dir, start_date=args.start_date, end_date=args.end_date):
                successful.append(symbol)
            else:
                failed.append(symbol)
        
        print(f"\n{'='*60}")
        print("PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"Successful: {len(successful)}/{len(STOCKS)}")
        if successful:
            print(f"✅ Successful stocks: {', '.join(successful)}")
        if failed:
            print(f"❌ Failed stocks: {', '.join(failed)}")
        print(f"{'='*60}\n")

if __name__ == "__main__":
    main()

