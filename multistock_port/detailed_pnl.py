import json

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
                'position': position,
                'cash': cash
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
            'cash': cash
        })
        position = 0
        position_cost_basis = 0

# Get last price
last_price = get_price_from_date(data['end_date']) or 70.0

# Final value
final_value = cash + (position * last_price if position > 0 else 0)
total_return = final_value - 1000000
percent_return = (total_return / 1000000) * 100

print('=== DETAILED NVO BACKTEST ANALYSIS ===\n')
print(f'Starting Value: $1,000,000.00')
print(f'Final Value: ${final_value:,.2f}')
print(f'Total Return: ${total_return:,.2f} ({percent_return:.2f}%)\n')

buy_trades = [t for t in trades_executed if t['action'] == 'BUY']
sell_trades = [t for t in trades_executed if t['action'] == 'SELL']

print(f'BUY trades executed: {len(buy_trades)}')
print(f'SELL trades executed: {len(sell_trades)}')
print(f'Total trades executed: {len(trades_executed)}\n')

if sell_trades:
    print('--- SELL Trades ---')
    for t in sell_trades:
        print(f"{t['date']}: SOLD {t['shares']} shares @ ${t['price']:.2f} -> Proceeds: ${t['proceeds']:,.2f}, Profit: ${t['profit']:,.2f}")
else:
    print('--- NO SELL TRADES EXECUTED ---')
    print('(Agent had SELL decisions but no position to sell)\n')

print(f'\nFinal Position: {position} shares')
print(f'Final Cash: ${cash:,.2f}')

