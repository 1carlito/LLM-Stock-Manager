#!/usr/bin/env python3
"""
Collect news data for multiple stocks and general market news.
"""

import os
from datetime import datetime
from convert_news_data import NewsDataManager

# List of stocks to collect news for
STOCKS = [
    "GOOGL",  # Alphabet Inc.
    "NVDA",   # NVIDIA Corporation  
    "PLTR",   # Palantir Technologies Inc.
    "ABBV",   # AbbVie Inc.
    "UNH",    # UnitedHealth Group Incorporated
    "JPM",    # JPMorgan Chase & Co.
    "RKLB"    # Rocket Lab USA, Inc.
]

def main():
    # Initialize news manager
    manager = NewsDataManager(output_dir="news_data")
    
    # Set date range
    end_date = "2025-10-01"
    start_date = "2025-07-01"
    
    print(f"\n🔄 Collecting news data from {start_date} to {end_date}")
    print("=" * 50)
    
    # Collect news for each stock
    for symbol in STOCKS:
        print(f"\n📰 Processing {symbol}...")
        
        # Fetch news data
        articles = manager.fetch_all_available_news(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        
        if articles:
            # Convert and save news data
            sentiment_data = manager.combine_news_data(symbol, [], days=90)
            if sentiment_data:
                print(f"✅ Successfully processed {symbol}")
            else:
                print(f"❌ Failed to process {symbol}")
        else:
            print(f"❌ No news found for {symbol}")
    
    # Collect general market news
    print("\n📰 Processing general market news...")
    market_articles = manager.fetch_all_available_news(
        symbol="",  # Empty symbol for general market news
        start_date=start_date,
        end_date=end_date
    )
    
    if market_articles:
        # Save general market news
        sentiment_data = manager.combine_news_data("MARKET", [], days=90)
        if sentiment_data:
            print("✅ Successfully processed general market news")
        else:
            print("❌ Failed to process general market news")
    else:
        print("❌ No general market news found")
    
    print("\n✅ News collection complete!")

if __name__ == "__main__":
    main()
