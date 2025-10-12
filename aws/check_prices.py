import json
with open('backtest_data_90days/stock_data_20250910_202056.json', 'r') as f:
    data = json.load(f)
googl_data = data['GOOGL']
print('GOOGL historical prices (first 5):')
for i, price in enumerate(googl_data['historical_prices'][:5]):
    print(f'{i}: {price["date"]} - Close: ${price["close"]}')
