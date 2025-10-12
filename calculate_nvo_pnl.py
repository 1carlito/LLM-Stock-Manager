import json
import re

# Load results
with open('date_filtered_backtest_results.json', 'r') as f:
    data = json.load(f)

trades = data['portfolio']['theoretical_trades']

# Load valuation files to get actual prices
def get_price_from_date(date):
    date_str = date.replace('-', '')
    try:
        with open(f'valuation_reports/NOVO_valuation_analysis_{date_str}.json', 'r') as f:
            val_data = json.load(f)
            # Try to extract price from price_target
            if val_data.get('price_target'):
                return float(val_data['price_target'])
    except:
        pass
    return None

# Simulate portfolio
cash = 1000000
position = 0
position_cost_basis = 0
trades_executed = []

print('=== SIMULATED NVO BACKTEST WITH ACTUAL PRICES ===\n')

for trade in trades:
    if not trade['executed']:
        continue
    
    date = trade['date']
    decision = trade['decision']
    confidence = trade['confidence']
    
    price = get_price_from_date(date)
    
    if price is None or price <= 0:
        continue
    
    if decision == 'BUY' and cash > 0:
        # Use 20% of portfolio value * confidence for position sizing
        portfolio_value = cash + (position * price if position > 0 else 0)
        position_size_value = portfolio_value * 0.2 * confidence
        shares_to_buy = int(position_size_value / price)
        cost = shares_to_buy * price
        
        if cost <= cash and shares_to_buy > 0:
            cash -= cost
            position += shares_to_buy
            position_cost_basis += cost
            trades_executed.append({
                'date': date,
                'action': 'BUY',
                'price': price,
                'shares': shares_to_buy,
                'cost': cost,
                'position': position,
                'cash': cash,
                'portfolio_value': cash + (position * price)
            })
            
    elif decision == 'SELL' and position > 0:
        proceeds = position * price
        cash += proceeds
        profit = proceeds - position_cost_basis
        trades_executed.append({
            'date': date,
            'action': 'SELL',
            'price': price,
            'shares': position,
            'proceeds': proceeds,
            'profit': profit,
            'position': 0,
            'cash': cash,
            'portfolio_value': cash
        })
        position = 0
        position_cost_basis = 0

# Get last known price
last_price = get_price_from_date(data['end_date'])
if last_price is None and trades_executed:
    last_price = trades_executed[-1].get('price', 0)

# Final portfolio value
final_value = cash + (position * last_price if position > 0 and last_price else 0)
total_return = final_value - 1000000
percent_return = (total_return / 1000000) * 100

print(f'Starting Value: $1,000,000.00')
print(f'Final Value: ${final_value:,.2f}')
print(f'Total Return: ${total_return:,.2f} ({percent_return:.2f}%)')
print(f'\nFinal Cash: ${cash:,.2f}')
print(f'Final Position: {position} shares @ ${last_price:.2f}')
print(f'Position Value: ${position * last_price if position > 0 and last_price else 0:,.2f}')
print(f'\nTotal Executed Trades: {len(trades_executed)}')

# Show first few trades
if trades_executed:
    print(f'\n--- First 5 Trades ---')
    for t in trades_executed[:5]:
        print(f"{t['date']}: {t['action']} {t['shares']} shares @ ${t['price']:.2f} -> Portfolio: ${t['portfolio_value']:,.2f}")
    
    print(f'\n--- Last 5 Trades ---')
    for t in trades_executed[-5:]:
        action_details = f"{t['shares']} shares @ ${t['price']:.2f}"
        if 'profit' in t:
            action_details += f" (Profit: ${t['profit']:,.2f})"
        print(f"{t['date']}: {t['action']} {action_details} -> Portfolio: ${t['portfolio_value']:,.2f}")

