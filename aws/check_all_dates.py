import json

def print_date_range(data, symbol):
    prices = data[symbol]['historical_prices']
    prices.sort(key=lambda x: x['date'])  # Sort by date ascending
    print(f"\n{symbol} date range:")
    print(f"First date: {prices[0]['date']} - ${prices[0]['close']}")
    print(f"Last date: {prices[-1]['date']} - ${prices[-1]['close']}")
    
    # Print June 1-3 prices if they exist
    june_prices = [p for p in prices if p['date'].startswith('2025-06')]
    if june_prices:
        print("\nJune 2025 prices:")
        for p in june_prices[:5]:  # First 5 June dates
            print(f"{p['date']}: ${p['close']}")

with open('../backtest_data_90days/stock_data_20250910_202056.json', 'r') as f:
    data = json.load(f)

# Check GOOGL as example
print_date_range(data, 'GOOGL')
