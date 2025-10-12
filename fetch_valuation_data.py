"""
Fetch Valuation Data
===================

Fetches stock price and valuation data for the specified period.
"""

import os
import json
from datetime import datetime
from StockData_FmpApi import StockDataFmpApi

# List of stocks to fetch data for
STOCKS = [
    "GOOGL",  # Alphabet Inc.
    "NVDA",   # NVIDIA Corporation  
    "PLTR",   # Palantir Technologies Inc.
    "ABBV",   # AbbVie Inc.
    "UNH",    # UnitedHealth Group Incorporated
    "JPM",    # JPMorgan Chase & Co.
    "RKLB"    # Rocket Lab USA, Inc.
]

# Date range
FROM_DATE = "2025-07-01"
TO_DATE = "2025-09-19"

def main():
    """Fetch valuation data for all stocks."""
    # Set API key
    os.environ['FMP_API_KEY'] = 'ycgZTG3ZghcrJBNwLsqWUckPXyK8sB5Z'
    
    # Initialize API client
    api_client = StockDataFmpApi()
    
    # Create output directory
    os.makedirs("live_trades/valuation_data", exist_ok=True)
    
    print(f"\nFetching valuation data from {FROM_DATE} to {TO_DATE}")
    print("=" * 50)
    
    all_data = {}
    
    for symbol in STOCKS:
        print(f"\nProcessing {symbol}:")
        try:
            # Fetch data without financials
            data = api_client.fetch_stock_data(
                symbol=symbol,
                from_date=FROM_DATE,
                to_date=TO_DATE,
                include_financials=False
            )
            
            if data:
                # Convert to dictionary and store
                all_data[symbol] = data.to_dict()
                print(f"✅ Successfully fetched data for {symbol}")
            else:
                print(f"❌ Failed to fetch data for {symbol}")
                
        except Exception as e:
            print(f"❌ Error processing {symbol}: {str(e)}")
    
    # Save all data to a single file
    output_file = "live_trades/valuation_data/stock_data_valuation.json"
    with open(output_file, "w") as f:
        json.dump(all_data, f, indent=2)
    
    print(f"\nData saved to {output_file}")

if __name__ == "__main__":
    main() 