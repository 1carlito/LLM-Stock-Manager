#!/usr/bin/env python3
"""
Script to track portfolio value over time from portfolio decisions JSON files.
Tracks positions as trades execute and calculates portfolio value using daily stock prices
from the stock data JSON file.
"""

import os
import json
import glob
import argparse
import csv
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import defaultdict

# Optional dependencies
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


def load_stock_data(data_dir: str) -> Dict[str, Dict]:
    """Load stock price data from the stock data JSON file"""
    quant_data_dir = os.path.join(data_dir, 'quant_data')
    
    # Try to find stock data file
    stock_data_file = os.path.join(quant_data_dir, 'mid_cap_stock_data_20250701_20251101_20251116_132209.json')
    
    if not os.path.exists(stock_data_file):
        # Try to find any mid_cap_stock_data file
        pattern = os.path.join(quant_data_dir, 'mid_cap_stock_data_*.json')
        files = glob.glob(pattern)
        if files:
            files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            stock_data_file = files[0]
        else:
            raise FileNotFoundError(f"Stock data file not found in {quant_data_dir}")
    
    print(f"📊 Loading stock data from: {stock_data_file}")
    
    with open(stock_data_file, 'r') as f:
        stock_data = json.load(f)
    
    # Create a date-indexed price lookup: {symbol: {date: price}}
    price_lookup = {}
    for symbol, data in stock_data.items():
        if not isinstance(data, dict):
            continue
        
        historical_prices = data.get('historical_prices', [])
        price_by_date = {}
        
        for price_entry in historical_prices:
            date_str = price_entry.get('date')
            close_price = price_entry.get('close')
            
            if date_str and close_price is not None:
                try:
                    price_by_date[date_str] = float(close_price)
                except (ValueError, TypeError):
                    continue
        
        if price_by_date:
            price_lookup[symbol] = price_by_date
    
    print(f"✅ Loaded price data for {len(price_lookup)} stocks")
    return price_lookup


def get_stock_price(symbol: str, date: str, price_lookup: Dict[str, Dict[str, float]]) -> Optional[float]:
    """Get stock price for a given symbol and date (or latest available price before that date)"""
    if symbol not in price_lookup:
        return None
    
    prices = price_lookup[symbol]
    
    # Exact match
    if date in prices:
        return prices[date]
    
    # Find latest price on or before this date
    date_obj = datetime.strptime(date, '%Y-%m-%d')
    latest_price = None
    latest_date = None
    
    for price_date_str, price in prices.items():
        try:
            price_date = datetime.strptime(price_date_str, '%Y-%m-%d')
            if price_date <= date_obj:
                if latest_date is None or price_date > latest_date:
                    latest_date = price_date
                    latest_price = price
        except ValueError:
            continue
    
    return latest_price


def load_portfolio_decisions(data_dir: str, backtest_name: str = None) -> List[Dict[str, Any]]:
    """Load all portfolio decision JSON files, sorted by date"""
    # Try different possible directory names
    possible_dirs = [
        os.path.join(data_dir, 'portfolio_decisions_DSeek'),
        os.path.join(data_dir, 'portfolio_decisions_D'),
        os.path.join(data_dir, 'portfolio_decisions_Claude'),
        os.path.join(data_dir, 'portfolio_decisions'),
    ]
    
    # Also check parent directory
    parent_dir = os.path.dirname(data_dir) if data_dir != '.' else '.'
    glob_pattern = os.path.join(parent_dir, 'portfolio_decisions*')
    matching_dirs = glob.glob(glob_pattern)
    if matching_dirs:
        possible_dirs.extend([d for d in matching_dirs if os.path.isdir(d)])
    
    decisions_dir = None
    for dir_path in possible_dirs:
        if os.path.exists(dir_path):
            decisions_dir = dir_path
            break
    
    if not decisions_dir:
        all_dirs = [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
        matching = [d for d in all_dirs if 'portfolio' in d.lower() or 'decision' in d.lower()]
        error_msg = f"Portfolio decisions directory not found.\n"
        error_msg += f"  Tried: {possible_dirs}\n"
        if matching:
            error_msg += f"  Found similar directories: {matching}\n"
        raise FileNotFoundError(error_msg)
    
    print(f"📂 Reading portfolio decisions from: {decisions_dir}")
    
    # Build file pattern
    if backtest_name:
        pattern = os.path.join(decisions_dir, f"portfolio_decision_*_{backtest_name}.json")
    else:
        pattern = os.path.join(decisions_dir, "portfolio_decision_*.json")
    
    files = glob.glob(pattern)
    
    if not files:
        print(f"⚠️  No files found matching pattern: {pattern}")
        return []
    
    print(f"📄 Found {len(files)} portfolio decision files")
    
    # Load all decision files
    decisions = []
    for file_path in files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Extract date from filename or data
            date_str = data.get('date')
            if not date_str:
                # Try to extract from filename
                filename = os.path.basename(file_path)
                parts = filename.replace('.json', '').split('_')
                if len(parts) >= 3:
                    date_str = parts[2]  # YYYYMMDD
                    try:
                        date_obj = datetime.strptime(date_str, '%Y%m%d')
                        date_str = date_obj.strftime('%Y-%m-%d')
                    except ValueError:
                        pass
            
            if date_str:
                data['date'] = date_str
                data['file_path'] = file_path
                decisions.append(data)
            
        except Exception as e:
            print(f"⚠️  Error loading {file_path}: {e}")
            continue
    
    # Sort by date
    decisions.sort(key=lambda x: x.get('date', ''))
    
    return decisions


def track_portfolio_value(decisions: List[Dict[str, Any]], price_lookup: Dict[str, Dict[str, float]], 
                         initial_cash: float = 100000) -> List[Dict[str, Any]]:
    """
    Track portfolio value over time by simulating trades and calculating values using stock prices.
    
    Args:
        decisions: List of portfolio decision dictionaries, sorted by date
        price_lookup: Dictionary mapping symbol -> {date -> price}
        initial_cash: Starting cash amount
    
    Returns:
        List of daily portfolio metrics
    """
    # Track positions
    long_positions = {}  # {symbol: {'shares': int, 'avg_price': float, 'cost_basis': float}}
    short_positions = {}  # {symbol: {'shares': int, 'avg_price': float, 'entry_value': float}}
    cash = initial_cash
    
    portfolio_history = []
    
    for decision in decisions:
        date = decision.get('date', '')
        if not date:
            continue
        
        portfolio_decisions = decision.get('portfolio_decisions', [])
        
        # Process trades for this day
        daily_trades = {
            'buy': [],
            'sell': [],
            'short': [],
            'cover': []
        }
        
        for pd_decision in portfolio_decisions:
            symbol = pd_decision.get('symbol', '').upper()
            action = pd_decision.get('action', '').upper()
            amount_usd = pd_decision.get('amount_usd', 0) or 0
            
            if not symbol or amount_usd <= 0:
                continue
            
            price = get_stock_price(symbol, date, price_lookup)
            if not price or price <= 0:
                continue
            
            if action == 'BUY':
                shares = int(amount_usd // price)
                if shares > 0:
                    cost = shares * price
                    
                    # Update long position
                    if symbol in long_positions:
                        old_shares = long_positions[symbol]['shares']
                        old_cost = long_positions[symbol]['cost_basis']
                        new_shares = old_shares + shares
                        new_cost = old_cost + cost
                        long_positions[symbol] = {
                            'shares': new_shares,
                            'avg_price': new_cost / new_shares if new_shares > 0 else price,
                            'cost_basis': new_cost
                        }
                    else:
                        long_positions[symbol] = {
                            'shares': shares,
                            'avg_price': price,
                            'cost_basis': cost
                        }
                    
                    cash -= cost
                    daily_trades['buy'].append({'symbol': symbol, 'shares': shares, 'amount': cost})
            
            elif action == 'SELL':
                if symbol in long_positions and long_positions[symbol]['shares'] > 0:
                    shares_to_sell = long_positions[symbol]['shares']
                    proceeds = shares_to_sell * price
                    cash += proceeds
                    del long_positions[symbol]
                    daily_trades['sell'].append({'symbol': symbol, 'shares': shares_to_sell, 'amount': proceeds})
            
            elif action == 'SHORT':
                # For CFD shorts, we just track the position, no margin reserved
                shares = int(amount_usd // price)
                if shares > 0:
                    entry_value = shares * price
                    
                    # Update short position
                    if symbol in short_positions:
                        old_shares = short_positions[symbol]['shares']
                        old_entry = short_positions[symbol]['entry_value']
                        new_shares = old_shares + shares
                        new_entry = old_entry + entry_value
                        short_positions[symbol] = {
                            'shares': new_shares,
                            'avg_price': new_entry / new_shares if new_shares > 0 else price,
                            'entry_value': new_entry
                        }
                    else:
                        short_positions[symbol] = {
                            'shares': shares,
                            'avg_price': price,
                            'entry_value': entry_value
                        }
                    
                    # For CFD: no margin deduction, only spread fee would be charged at execution
                    daily_trades['short'].append({'symbol': symbol, 'shares': shares, 'notional': entry_value})
            
            elif action in ('COVER', 'CLOSE'):
                if symbol in short_positions and short_positions[symbol]['shares'] > 0:
                    short_pos = short_positions[symbol]
                    shares_to_cover = short_pos['shares']
                    entry_price = short_pos['avg_price']
                    cover_cost = shares_to_cover * price
                    
                    # Short P&L = (Entry Price - Current Price) * Shares
                    pnl = (entry_price - price) * shares_to_cover
                    cash += pnl  # Add P&L to cash
                    
                    del short_positions[symbol]
                    daily_trades['cover'].append({'symbol': symbol, 'shares': shares_to_cover, 'pnl': pnl})
        
        # Calculate portfolio value at end of day
        long_value = 0
        long_unrealized_pnl = 0
        
        for symbol, pos in long_positions.items():
            price = get_stock_price(symbol, date, price_lookup)
            if price:
                position_value = pos['shares'] * price
                long_value += position_value
                long_unrealized_pnl += position_value - pos['cost_basis']
        
        short_value = 0
        short_unrealized_pnl = 0
        
        for symbol, short_pos in short_positions.items():
            price = get_stock_price(symbol, date, price_lookup)
            if price:
                entry_price = short_pos['avg_price']
                notional_value = short_pos['shares'] * price
                short_value += notional_value
                # Short P&L = (Entry Price - Current Price) * Shares
                pnl = (entry_price - price) * short_pos['shares']
                short_unrealized_pnl += pnl
        
        # Total portfolio value = Cash + Long Positions Value + Short P&L
        total_value = cash + long_value + short_unrealized_pnl
        
        # Calculate return
        initial_val = portfolio_history[0]['total_value'] if portfolio_history else initial_cash
        return_pct = ((total_value - initial_val) / initial_val * 100) if initial_val > 0 else 0
        
        portfolio_history.append({
            'date': date,
            'cash': cash,
            'long_value': long_value,
            'long_unrealized_pnl': long_unrealized_pnl,
            'short_notional_value': short_value,
            'short_unrealized_pnl': short_unrealized_pnl,
            'total_value': total_value,
            'portfolio_return_pct': return_pct,
            'num_long_positions': len(long_positions),
            'num_short_positions': len(short_positions),
            'buy_count': len(daily_trades['buy']),
            'sell_count': len(daily_trades['sell']),
            'short_count': len(daily_trades['short']),
            'cover_count': len(daily_trades['cover']),
        })
    
    return portfolio_history


def plot_portfolio_value(history: List[Dict[str, Any]], output_file: str = None):
    """Create visualization of portfolio value over time"""
    if not MATPLOTLIB_AVAILABLE:
        print("⚠️  matplotlib not available. Plotting disabled.")
        print("   Install with: pip install matplotlib")
        return
    
    if not history:
        print("⚠️  No data to plot")
        return
    
    # Convert to DataFrame for easier plotting
    if PANDAS_AVAILABLE:
        df = pd.DataFrame(history)
        df['date'] = pd.to_datetime(df['date'])
        dates = df['date']
        total_value = df['total_value']
        cash = df['cash']
        return_pct = df['portfolio_return_pct']
        buy_count = df['buy_count']
        sell_count = df['sell_count']
    else:
        dates = [datetime.strptime(h['date'], '%Y-%m-%d') for h in history]
        total_value = [h['total_value'] for h in history]
        cash = [h['cash'] for h in history]
        return_pct = [h['portfolio_return_pct'] for h in history]
        buy_count = [h['buy_count'] for h in history]
        sell_count = [h['sell_count'] for h in history]
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Portfolio Value Tracking Over Time', fontsize=16)
    
    # Plot 1: Portfolio Value
    ax1 = axes[0, 0]
    ax1.plot(dates, total_value, marker='o', linewidth=2, markersize=4)
    ax1.set_title('Portfolio Value Over Time')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Portfolio Value ($)')
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(axis='x', rotation=45)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1000:.0f}K'))
    
    # Plot 2: Cash
    ax2 = axes[0, 1]
    ax2.plot(dates, cash, marker='o', color='green', linewidth=2, markersize=4)
    ax2.set_title('Cash Balance Over Time')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Cash ($)')
    ax2.grid(True, alpha=0.3)
    ax2.tick_params(axis='x', rotation=45)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1000:.0f}K'))
    
    # Plot 3: Portfolio Return %
    ax3 = axes[1, 0]
    ax3.plot(dates, return_pct, marker='o', color='green', linewidth=2, markersize=4)
    ax3.axhline(y=0, color='r', linestyle='--', alpha=0.5)
    ax3.set_title('Portfolio Return %')
    ax3.set_xlabel('Date')
    ax3.set_ylabel('Return (%)')
    ax3.grid(True, alpha=0.3)
    ax3.tick_params(axis='x', rotation=45)
    
    # Plot 4: Trade Activity
    ax4 = axes[1, 1]
    ax4.plot(dates, buy_count, marker='o', label='BUY', linewidth=2, markersize=4)
    ax4.plot(dates, sell_count, marker='s', label='SELL', linewidth=2, markersize=4)
    ax4.set_title('Trade Activity Counts')
    ax4.set_xlabel('Date')
    ax4.set_ylabel('Number of Trades')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    ax4.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"📊 Plot saved to: {output_file}")
    else:
        plt.show()


def main():
    parser = argparse.ArgumentParser(description='Track portfolio value over time using actual stock prices')
    parser.add_argument('--data-dir', default=os.path.dirname(os.path.abspath(__file__)),
                      help='Data directory containing portfolio_decisions and quant_data (defaults to script directory)')
    parser.add_argument('--backtest-name', default=None,
                      help='Optional: Filter by backtest name')
    parser.add_argument('--initial-cash', type=float, default=100000,
                      help='Initial cash amount (default: 100000)')
    parser.add_argument('--output-csv', default=None,
                      help='Optional: Output CSV file path')
    parser.add_argument('--output-plot', default=None,
                      help='Optional: Output plot file path')
    parser.add_argument('--show-plot', action='store_true',
                      help='Show the plot interactively')
    parser.add_argument('--no-plot', action='store_true',
                      help='Skip plotting (only generate CSV)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("📈 Portfolio Value Tracker (Using Actual Stock Prices)")
    print("=" * 80)
    
    try:
        # Load stock price data
        print("\n📊 Loading stock price data...")
        price_lookup = load_stock_data(args.data_dir)
        
        # Load portfolio decisions
        print("\n📂 Loading portfolio decisions...")
        decisions = load_portfolio_decisions(args.data_dir, args.backtest_name)
        
        if not decisions:
            print("❌ No portfolio decisions found. Exiting.")
            return
        
        print(f"✅ Loaded {len(decisions)} portfolio decision files")
        
        # Track portfolio value over time
        print("\n💼 Tracking portfolio value over time...")
        history = track_portfolio_value(decisions, price_lookup, args.initial_cash)
        
        if not history:
            print("❌ No portfolio history generated. Exiting.")
            return
        
        print(f"✅ Generated portfolio history for {len(history)} days")
        
        # Display summary
        print("\n" + "=" * 80)
        print("📊 Summary Statistics")
        print("=" * 80)
        
        first_day = history[0]
        last_day = history[-1]
        
        print(f"Date Range: {first_day['date']} to {last_day['date']}")
        print(f"Days Tracked: {len(history)}")
        print(f"\nPortfolio Value:")
        print(f"  Initial: ${first_day['total_value']:,.2f}")
        print(f"  Final: ${last_day['total_value']:,.2f}")
        print(f"  Total Return: ${last_day['total_value'] - first_day['total_value']:,.2f} ({last_day['portfolio_return_pct']:.2f}%)")
        print(f"\nFinal State:")
        print(f"  Cash: ${last_day['cash']:,.2f}")
        print(f"  Long Positions Value: ${last_day['long_value']:,.2f}")
        print(f"  Long Unrealized P&L: ${last_day['long_unrealized_pnl']:,.2f}")
        print(f"  Short Notional Value: ${last_day['short_notional_value']:,.2f}")
        print(f"  Short Unrealized P&L: ${last_day['short_unrealized_pnl']:,.2f}")
        
        # Save CSV
        output_path = args.output_csv or os.path.join(args.data_dir, 'portfolio_value_history.csv')
        
        with open(output_path, 'w', newline='') as f:
            fieldnames = history[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(history)
        
        print(f"\n✅ CSV saved to: {output_path}")
        
        # Create plot
        if not args.no_plot:
            if args.output_plot:
                plot_portfolio_value(history, args.output_plot)
            elif args.show_plot:
                plot_portfolio_value(history)
            else:
                default_plot = os.path.join(args.data_dir, 'portfolio_value_plot.png')
                plot_portfolio_value(history, default_plot)
        
        print("\n" + "=" * 80)
        print("✅ Portfolio tracking complete!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
