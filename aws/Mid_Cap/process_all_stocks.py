"""
Process All Stocks
================

Process collected stock data through all 3 analysis agents (Sentiment, Fundamental, Valuation).
Generates analyses for all trading days in the date range.
"""

import os
import json
import argparse
import glob
from datetime import datetime, timedelta
from typing import List

# Import agents
from SentimentAgent import SentimentAgent
from FundamentalAgent import FundamentalAgent
from ValuationAgent import ValuationAgent


def get_stocks_from_data(data_dir: str = ".") -> List[str]:
    """Extract stock symbols from the quant_data JSON file"""
    try:
        # Try to find the mid_cap_stock_data file
        quant_data_dir = os.path.join(data_dir, "quant_data")
        primary_file = os.path.join(quant_data_dir, "mid_cap_stock_data_20250701_20251101_20251116_132209.json")

        # If primary file doesn't exist, try to find any mid_cap_stock_data file
        if not os.path.exists(primary_file):
            mid_cap_files = glob.glob(os.path.join(quant_data_dir, "mid_cap_stock_data_*.json"))
            if mid_cap_files:
                mid_cap_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                primary_file = mid_cap_files[0]

        if os.path.exists(primary_file):
            with open(primary_file, 'r') as f:
                data = json.load(f)

            if isinstance(data, dict):
                stocks = sorted([symbol for symbol in data.keys() if symbol])
                print(f"📊 Found {len(stocks)} stocks in {primary_file}")
                return stocks

        print(f"⚠️ Could not find stock data file. Tried: {primary_file}")
        return []

    except Exception as e:
        print(f"❌ Error extracting stocks from data file: {e}")
        return []


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


def process_stock(symbol: str, data_dir: str = ".", start_date: str = "2025-08-02", end_date: str = "2025-11-14"):
    """Process a single stock through Sentiment, Fundamental, and Valuation agents for all trading days."""
    print(f"\n{'='*60}")
    print(f"Processing {symbol}")
    print(f"{'='*60}")

    try:
        # Initialize agents with date range
        sentiment_agent = SentimentAgent(data_dir=data_dir, stock_data_path=None)
        fundamental_agent = FundamentalAgent(data_dir=data_dir, start_date=start_date, end_date=end_date)
        valuation_agent = ValuationAgent(data_dir=data_dir)

        # Get all trading days
        trading_days = get_trading_days(start_date, end_date)
        print(f"📅 Generating analyses for {len(trading_days)} trading days: {start_date} to {end_date}")
        print(f"  ✅ Running sentiment, fundamental, and valuation analysis")

        # Generate analyses for each trading day
        successful_sentiments = 0
        successful_fundamentals = 0
        successful_valuations = 0

        for i, current_date in enumerate(trading_days, 1):
            if i % 5 == 0 or i == 1:
                print(f"\n📅 Processing date {i}/{len(trading_days)}: {current_date}")

            # Run sentiment analysis
            try:
                sentiment = sentiment_agent.analyze_sentiment(symbol, current_date)
                if sentiment:
                    successful_sentiments += 1
            except Exception as e:
                print(f"  ❌ Sentiment error for {current_date}: {e}")

            # Run fundamental analysis
            try:
                fundamental = fundamental_agent.analyze_fundamentals(symbol, current_date)
                if fundamental:
                    successful_fundamentals += 1
            except Exception as e:
                print(f"  ❌ Fundamental error for {current_date}: {e}")

            # Run valuation analysis
            try:
                valuation = valuation_agent.analyze_valuation(symbol, current_date)
                if valuation:
                    successful_valuations += 1
            except Exception as e:
                print(f"  ❌ Valuation error for {current_date}: {e}")

        print(f"\n✅ Completed processing {symbol}:")
        print(f"   Sentiment:   {successful_sentiments}/{len(trading_days)} analyses")
        print(f"   Fundamental: {successful_fundamentals}/{len(trading_days)} analyses")
        print(f"   Valuation:   {successful_valuations}/{len(trading_days)} analyses")

        # Consider successful if at least one analysis worked
        if successful_sentiments > 0 or successful_fundamentals > 0 or successful_valuations > 0:
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
    parser.add_argument("--start-date", default="2025-08-02", help="Start date for analysis (YYYY-MM-DD)")
    parser.add_argument("--end-date", default="2025-11-14", help="End date for analysis (YYYY-MM-DD)")
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
        # Get stocks dynamically from data file
        stocks = get_stocks_from_data(data_dir=args.data_dir)

        if not stocks:
            print("❌ No stocks found in data file. Cannot proceed.")
            return

        # Process all stocks
        print(f"Starting processing of {len(stocks)} stocks: {', '.join(stocks)}")

        successful = []
        failed = []

        for symbol in stocks:
            if process_stock(symbol, data_dir=args.data_dir, start_date=args.start_date, end_date=args.end_date):
                successful.append(symbol)
            else:
                failed.append(symbol)

        print(f"\n{'='*60}")
        print("PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"Successful: {len(successful)}/{len(stocks)}")
        if successful:
            print(f"✅ Successful stocks: {', '.join(successful)}")
        if failed:
            print(f"❌ Failed stocks: {', '.join(failed)}")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    main()

