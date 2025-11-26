"""
Script to fetch historical market capitalization data and add it to the mid cap JSON file
"""

import os
import json
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add parent directory to path to import StockData_FmpApi
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from StockData_FmpApi import StockDataFmpApi

# Load environment variables
load_dotenv()

def get_trading_days(start_date: str, end_date: str) -> list:
    """Get list of trading days (weekdays) between start and end date"""
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    trading_days = []
    current = start
    while current <= end:
        # Monday = 0, Sunday = 6
        if current.weekday() < 5:  # Monday to Friday
            trading_days.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    
    return trading_days

def update_market_cap_in_json(json_file_path: str, start_date: str, end_date: str):
    """
    Fetch market cap data for all stocks and update the JSON file
    
    Args:
        json_file_path: Path to the mid cap JSON file
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    """
    # Load API key
    api_key = os.getenv('FMP_API_KEY')
    if not api_key:
        raise ValueError("FMP_API_KEY environment variable not set")
    
    # Initialize API client
    client = StockDataFmpApi(api_key)
    
    # Load existing JSON file
    print(f"📂 Loading JSON file: {json_file_path}")
    with open(json_file_path, 'r') as f:
        data = json.load(f)
    
    symbols = list(data.keys())
    print(f"📊 Found {len(symbols)} symbols: {', '.join(symbols)}")
    
    # Get trading days
    trading_days = get_trading_days(start_date, end_date)
    print(f"📅 Fetching market cap for {len(trading_days)} trading days ({start_date} to {end_date})")
    
    # Create a date-to-market-cap mapping for each symbol
    for idx, symbol in enumerate(symbols, 1):
        print(f"\n[{idx}/{len(symbols)}] Processing {symbol}...")
        
        try:
            # Fetch historical market cap data
            print(f"  🔍 Fetching market cap data for {symbol}...")
            market_cap_data = client.get_market_capitalization(symbol)
            
            if not market_cap_data:
                print(f"  ⚠️  No market cap data returned for {symbol}")
                continue
            
            # Create a dictionary mapping date to market cap
            market_cap_by_date = {}
            for entry in market_cap_data:
                date_str = entry.get('date', '')
                market_cap = entry.get('marketCap', 0)
                if date_str and market_cap:
                    market_cap_by_date[date_str] = market_cap
            
            print(f"  ✅ Retrieved {len(market_cap_by_date)} market cap entries")
            
            # Update historical_prices with market cap data
            if 'historical_prices' in data[symbol]:
                updated_count = 0
                for price_entry in data[symbol]['historical_prices']:
                    date_str = price_entry.get('date', '')
                    
                    # Only update dates in our target range
                    if date_str >= start_date and date_str <= end_date:
                        if date_str in market_cap_by_date:
                            price_entry['market_cap'] = market_cap_by_date[date_str]
                            updated_count += 1
                        else:
                            # If no exact match, find the closest previous date
                            # Sort available dates and find the most recent one <= current date
                            available_dates = sorted([d for d in market_cap_by_date.keys() if d <= date_str])
                            if available_dates:
                                closest_date = available_dates[-1]
                                price_entry['market_cap'] = market_cap_by_date[closest_date]
                                updated_count += 1
                            else:
                                # No market cap data available for this date
                                price_entry['market_cap'] = None
                
                print(f"  ✅ Updated {updated_count} price entries with market cap data")
            else:
                print(f"  ⚠️  No historical_prices found for {symbol}")
            
            # Small delay to respect rate limits
            import time
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  ❌ Error processing {symbol}: {e}")
            continue
    
    # Save updated JSON file
    print(f"\n💾 Saving updated JSON file...")
    with open(json_file_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Successfully updated {json_file_path}")
    print(f"📊 Market cap data added for {len(symbols)} symbols")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Update mid cap JSON file with historical market cap data")
    parser.add_argument("--json-file", 
                       default="aws/Mid_Cap/quant_data/mid_cap_stock_data_20250701_20251101_20251116_132209.json",
                       help="Path to the mid cap JSON file")
    parser.add_argument("--start-date", 
                       default="2025-07-14",
                       help="Start date in YYYY-MM-DD format (default: 2025-07-14)")
    parser.add_argument("--end-date", 
                       default="2025-11-14",
                       help="End date in YYYY-MM-DD format (default: 2025-11-14)")
    
    args = parser.parse_args()
    
    # Validate dates
    try:
        datetime.strptime(args.start_date, '%Y-%m-%d')
        datetime.strptime(args.end_date, '%Y-%m-%d')
    except ValueError:
        print("❌ Invalid date format. Use YYYY-MM-DD")
        return
    
    # Check if JSON file exists
    if not os.path.exists(args.json_file):
        print(f"❌ JSON file not found: {args.json_file}")
        return
    
    # Update market cap data
    update_market_cap_in_json(args.json_file, args.start_date, args.end_date)

if __name__ == "__main__":
    main()

