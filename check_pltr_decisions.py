import json

# Load results from AWS
try:
    with open('single_stock_test/date_filtered_backtest_results.json', 'r') as f:
        data = json.load(f)
except FileNotFoundError:
    print("Error: Please copy date_filtered_backtest_results.json from AWS first")
    print("Run: scp -i ~/.ssh/stock-agent-key-new.pem ubuntu@13.40.97.5:~/single_stock_experiment/date_filtered_backtest_results.json single_stock_test/")
    exit(1)

trades = data['portfolio']['theoretical_trades']

# Count decision types
buy_count = sum(1 for t in trades if t['decision'] == 'BUY')
sell_count = sum(1 for t in trades if t['decision'] == 'SELL')
hold_count = sum(1 for t in trades if t['decision'] == 'HOLD')

print(f'=== PLTR DECISION SUMMARY ===')
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

# Show decision timeline
print('\n--- Decision Timeline (First 20 days) ---')
for t in trades[:20]:
    print(f"{t['date']}: {t['decision']} (conf: {t['confidence']:.2f})")

print('\n--- Decision Timeline (Last 20 days) ---')
for t in trades[-20:]:
    print(f"{t['date']}: {t['decision']} (conf: {t['confidence']:.2f})")

