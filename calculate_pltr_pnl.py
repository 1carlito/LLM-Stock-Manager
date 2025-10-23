import json
import re

# Load results from AWS (you'll need to copy the file first)
try:
    with open('single_stock_test/date_filtered_backtest_results.json', 'r') as f:
        data = json.load(f)
except FileNotFoundError:
    print("Error: Please copy date_filtered_backtest_results.json from AWS first")
    print("Run: scp -i ~/.ssh/stock-agent-key-new.pem ubuntu@13.40.97.5:~/single_stock_experiment/date_filtered_backtest_results.json single_stock_test/")
    exit(1)

trades = data['portfolio']['theoretical_trades']

# Extract price from reasoning text
def extract_price_from_reasoning(reasoning):
    """Extract price from reasoning text like 'current price of $68.14'"""
    try:
        # Try pattern: "current price of $X.XX"
        match = re.search(r'current price of \$(\d+\.?\d*)', reasoning)
        if match:
            return float(match.group(1))
        
        # Try pattern: "current price around $X.XX"
        match = re.search(r'current price around \$(\d+\.?\d*)', reasoning)
        if match:
            return float(match.group(1))
        
        # Try pattern: "current $X.XX"
        match = re.search(r'current \$(\d+\.?\d*)', reasoning)
        if match:
            return float(match.group(1))
            
        # Try pattern: "price of $X.XX"
        match = re.search(r'price of \$(\d+\.?\d*)', reasoning)
        if match:
            return float(match.group(1))
    except:
        pass
    return None

# Simulate portfolio with proper position sizing
cash = 1000000
position = 0
position_cost_basis = 0
trades_executed = []
last_known_price = 100.0  # Fallback

print('=== SIMULATED PLTR BACKTEST WITH EXTRACTED PRICES ===\n')

for i, trade in enumerate(trades):
    date = trade['date']
    decision = trade['decision']
    confidence = trade['confidence']
    reasoning = trade.get('reasoning', '')
    
    # Extract price from reasoning
    price = extract_price_from_reasoning(reasoning)
    
    if price is None or price <= 0:
        # Use last known price if extraction fails
        price = last_known_price
        print(f"Warning: Using last known price ${price:.2f} for {date}")
    else:
        last_known_price = price
    
    if decision == 'BUY':
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
                'portfolio_value': cash + (position * price),
                'confidence': confidence
            })
        elif cost > cash:
            print(f"Warning: Insufficient cash for BUY on {date} (needed ${cost:,.2f}, have ${cash:,.2f})")
            
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
            'portfolio_value': cash,
            'confidence': confidence
        })
        position = 0
        position_cost_basis = 0

# Final portfolio value
final_value = cash + (position * last_known_price if position > 0 else 0)
total_return = final_value - 1000000
percent_return = (total_return / 1000000) * 100

print(f'Starting Value: $1,000,000.00')
print(f'Final Value: ${final_value:,.2f}')
print(f'Total Return: ${total_return:,.2f} ({percent_return:.2f}%)')
print(f'\nFinal Cash: ${cash:,.2f}')
print(f'Final Position: {position} shares @ ${last_known_price:.2f}')
print(f'Position Value: ${position * last_known_price if position > 0 else 0:,.2f}')
print(f'\nTotal Executed Trades: {len(trades_executed)}')

# Show first few trades
if trades_executed:
    print(f'\n--- First 10 Trades ---')
    for t in trades_executed[:10]:
        action_details = f"{t['shares']} shares @ ${t['price']:.2f} (conf: {t['confidence']:.2f})"
        if 'profit' in t:
            action_details += f" (Profit: ${t['profit']:,.2f})"
        print(f"{t['date']}: {t['action']} {action_details} -> Portfolio: ${t['portfolio_value']:,.2f}")
    
    print(f'\n--- Last 10 Trades ---')
    for t in trades_executed[-10:]:
        action_details = f"{t['shares']} shares @ ${t['price']:.2f} (conf: {t['confidence']:.2f})"
        if 'profit' in t:
            action_details += f" (Profit: ${t['profit']:,.2f})"
        print(f"{t['date']}: {t['action']} {action_details} -> Portfolio: ${t['portfolio_value']:,.2f}")

# Trading statistics
buy_trades = [t for t in trades_executed if t['action'] == 'BUY']
sell_trades = [t for t in trades_executed if t['action'] == 'SELL']

print(f'\n--- Trading Statistics ---')
print(f'Total BUY trades: {len(buy_trades)}')
print(f'Total SELL trades: {len(sell_trades)}')

if sell_trades:
    profitable_sells = [t for t in sell_trades if t['profit'] > 0]
    print(f'Profitable trades: {len(profitable_sells)}/{len(sell_trades)} ({len(profitable_sells)/len(sell_trades)*100:.1f}%)')
    
    total_profit = sum(t['profit'] for t in sell_trades)
    avg_profit = total_profit / len(sell_trades)
    print(f'Total profit from closed trades: ${total_profit:,.2f}')
    print(f'Average profit per trade: ${avg_profit:,.2f}')
    
    if profitable_sells:
        avg_win = sum(t['profit'] for t in profitable_sells) / len(profitable_sells)
        print(f'Average winning trade: ${avg_win:,.2f}')
    
    losing_sells = [t for t in sell_trades if t['profit'] <= 0]
    if losing_sells:
        avg_loss = sum(t['profit'] for t in losing_sells) / len(losing_sells)
        print(f'Average losing trade: ${avg_loss:,.2f}')

# Show all SELL decision dates
print(f'\n--- All SELL Trades ---')
for t in sell_trades:
    print(f"{t['date']}: SELL {t['shares']} shares @ ${t['price']:.2f} -> Profit: ${t['profit']:,.2f}")




