import json

# Load results
with open('date_filtered_backtest_results.json', 'r') as f:
    data = json.load(f)

trades = data['portfolio']['theoretical_trades']

# Get last trade
print(f"Backtest end date: {data['end_date']}")
print(f"Last decision date: {trades[-1]['date']}")
print(f"Last decision: {trades[-1]['decision']}")
print(f"Total decisions: {len(trades)}")

# Load valuation files to get actual prices
def get_price_from_date(date):
    date_str = date.replace('-', '')
    try:
        with open(f'valuation_reports/NOVO_valuation_analysis_{date_str}.json', 'r') as f:
            val_data = json.load(f)
            if val_data.get('price_target'):
                return float(val_data['price_target'])
    except:
        pass
    return None

# Calculate average share price
cash = 1000000
position = 0
total_invested = 0

for trade in trades:
    if not trade['executed']:
        continue
    
    price = get_price_from_date(trade['date'])
    if price is None or price <= 0:
        continue
    
    decision = trade['decision']
    confidence = trade['confidence']
    
    if decision == 'BUY' and cash > 0:
        portfolio_value = cash + (position * price if position > 0 else 0)
        position_size_value = portfolio_value * 0.2 * confidence
        shares_to_buy = int(position_size_value / price)
        cost = shares_to_buy * price
        
        if cost <= cash and shares_to_buy > 0:
            cash -= cost
            position += shares_to_buy
            total_invested += cost
            
    elif decision == 'SELL' and position > 0:
        proceeds = position * price
        cash += proceeds
        position = 0
        total_invested = 0

# Final price
final_price = get_price_from_date('2025-09-18') or 70.0

# Calculate average cost basis
avg_cost_per_share = total_invested / position if position > 0 else 0

print(f'\n=== FINAL POSITION ===')
print(f'Shares held: {position:,}')
print(f'Total invested in current position: ${total_invested:,.2f}')
print(f'Average cost per share: ${avg_cost_per_share:.2f}')
print(f'Current price (Sep 18): ${final_price:.2f}')
if position > 0:
    unrealized_pnl = (position * final_price) - total_invested
    print(f'Unrealized P/L: ${unrealized_pnl:,.2f} ({(unrealized_pnl/total_invested)*100:.2f}%)')
print(f'\nFinal Cash: ${cash:,.2f}')

