#!/usr/bin/env python3
"""
Remove historical price data from stock_data.json, keeping only fundamental data
"""

import json
import os
import sys

def remove_historical_prices(file_path: str):
    """Remove historical_prices and price-related fields from stock_data.json"""
    print(f"📂 Loading {file_path}...")
    
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    print(f"📊 Found {len(data)} symbols")
    
    # Fields to remove (price-related data)
    fields_to_remove = [
        'historical_prices',
        # Keep current_price as it's needed for fundamental analysis reference
        # Keep price_change_1d, price_change_5d, price_change_1m as they're summary metrics
        # Keep volume, avg_volume as they're trading metrics
    ]
    
    removed_count = 0
    for symbol, stock_data in data.items():
        if isinstance(stock_data, dict):
            for field in fields_to_remove:
                if field in stock_data:
                    del stock_data[field]
                    removed_count += 1
                    print(f"  ✅ Removed '{field}' from {symbol}")
    
    # Create backup
    backup_path = file_path + ".backup"
    print(f"\n💾 Creating backup: {backup_path}")
    with open(backup_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    # Save cleaned data
    print(f"💾 Saving cleaned data to {file_path}...")
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n✅ Complete! Removed {removed_count} historical_prices entries")
    print(f"📁 Backup saved to: {backup_path}")

if __name__ == "__main__":
    file_path = "/Users/pc/stock_agent_eval/stock_agent_eval_clean/aws/multistock_port_2.0/stock_data.json"
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        sys.exit(1)
    
    remove_historical_prices(file_path)

