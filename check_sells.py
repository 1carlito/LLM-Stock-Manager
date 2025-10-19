import json

# Load results
with open('date_filtered_backtest_results.json', 'r') as f:
    data = json.load(f)

trades = data['portfolio']['theoretical_trades']

# Count decision types
buy_count = sum(1 for t in trades if t['decision'] == 'BUY')
sell_count = sum(1 for t in trades if t['decision'] == 'SELL')
hold_count = sum(1 for t in trades if t['decision'] == 'HOLD')

print(f'Total Decisions: {len(trades)}')
print(f'BUY decisions: {buy_count}')
print(f'SELL decisions: {sell_count}')
print(f'HOLD decisions: {hold_count}')

# Show some SELL decisions
print('\n--- Sample SELL Decisions ---')
sell_trades = [t for t in trades if t['decision'] == 'SELL']
for t in sell_trades[:5]:
    print(f"{t['date']}: SELL (confidence: {t['confidence']:.2f})")
    
print(f'\n--- All SELL Decision Dates ---')
for t in sell_trades:
    print(t['date'], end=' ')
print()


