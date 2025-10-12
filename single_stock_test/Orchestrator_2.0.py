#!/usr/bin/env python3
"""
Script to run a date-filtered backtest using analysis files from AWS.
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
import json
import glob
import pandas_market_calendars as mcal
import logging
from logging.handlers import RotatingFileHandler
from collections import defaultdict

# Add current directory to path to ensure imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from ReasoningAgent import ReasoningAgent

class DateFilteredBacktest:
    """Run a backtest with date filtering using pre-generated analysis files."""
    
    def __init__(self, data_dir='.', start_date=None, end_date=None, lookback_window=4):
        self.data_dir = data_dir
        self.start_date = start_date
        self.end_date = end_date
        self.lookback_window = lookback_window  # Number of previous decisions to include
        
        # Set up logging
        log_dir = os.path.join(data_dir, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(log_dir, 'date_filtered_backtest.log')),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize portfolio
        self.portfolio = {
            'cash': 1000000,  # $1M starting cash
            'positions': {},
            'theoretical_trades': []
        }
        
        # Track previous decisions for each symbol
        self.previous_decisions = defaultdict(list)
        
        # Initialize ReasoningAgent
        self.reasoning_agent = ReasoningAgent(data_dir=data_dir)
        
        self.logger.info(f"Date Filtered Backtest initialized:")
        self.logger.info(f"- Date range: {start_date} to {end_date}")
        self.logger.info(f"- Data directory: {data_dir}")
        self.logger.info(f"- Lookback window: {lookback_window} days")
    
    def _get_latest_analysis(self, symbol, analysis_type, current_date):
        """Get the latest analysis file for a symbol and type before or on the current date."""
        # Map analysis types to directory names
        dir_mapping = {
            'valuation': 'valuation_reports',
            'fundamental': 'fundamental_reports', 
            'sentiment': 'sentiment_data'
        }
        
        if analysis_type not in dir_mapping:
            return None
            
        analysis_dir = os.path.join(self.data_dir, dir_mapping[analysis_type])
        if not os.path.exists(analysis_dir):
            return None
            
        # Find files for this symbol
        pattern = os.path.join(analysis_dir, f"{symbol}_*analysis*.json")
        files = glob.glob(pattern)
        
        if not files:
            return None
        
        current_date_obj = datetime.strptime(current_date, '%Y-%m-%d')
        valid_files = []
        
        # Read each file and check its actual analysis_date
        for file in files:
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    
                # Try all possible date field names
                target_date = data.get('target_date')
                analysis_date = data.get('analysis_date')
                simple_date = data.get('date')
                use_date = target_date or analysis_date or simple_date
                
                if not use_date:
                    continue
                    
                try:
                    # Handle both ISO format and simple date format
                    try:
                        date_obj = datetime.fromisoformat(use_date)
                    except ValueError:
                        try:
                            date_obj = datetime.strptime(use_date, '%Y-%m-%d')
                        except ValueError:
                            self.logger.warning(f"Invalid date format in {file}: {use_date}")
                            continue
                    
                    # Include file if its analysis date is before or on the current date
                    if date_obj.date() <= current_date_obj.date():
                        valid_files.append((file, date_obj, data))
                except Exception as e:
                    self.logger.warning(f"Failed to parse date in {file}: {analysis_date} - {str(e)}")
                    continue
                    
            except Exception as e:
                self.logger.warning(f"Failed to load or parse {file}: {e}")
                continue
        
        if not valid_files:
            return None
            
        # Get the file with the most recent analysis_date that's still <= current_date
        latest_valid = max(valid_files, key=lambda x: x[1])
        self.logger.info(f"Using {analysis_type} file: {os.path.basename(latest_valid[0])} with analysis_date: {latest_valid[1].strftime('%Y-%m-%d')}")
        return latest_valid[2]
    
    def _execute_trade(self, symbol, decision_result, current_date):
        """Execute a theoretical trade and update portfolio."""
        decision = decision_result.get('decision', 'HOLD')
        confidence = decision_result.get('confidence', 0.5)
        reasoning = decision_result.get('reasoning', '')
        
        # Extract price from valuation data (assuming it's in the reasoning)
        try:
            price_str = reasoning.split("current price of $")[1].split(")")[0].split(" ")[0]
            current_price = float(price_str)
        except:
            self.logger.warning(f"Could not extract price from reasoning, using last known price")
            current_price = self.portfolio.get('last_prices', {}).get(symbol, 100.0)
        
        # Update last known price
        if 'last_prices' not in self.portfolio:
            self.portfolio['last_prices'] = {}
        self.portfolio['last_prices'][symbol] = current_price
        
        # Calculate position size based on confidence and portfolio value
        portfolio_value = self.portfolio['cash']
        for sym, pos in self.portfolio['positions'].items():
            last_price = self.portfolio['last_prices'].get(sym, pos['price'])
            portfolio_value += pos['shares'] * last_price
        
        position_size = portfolio_value * 0.2 * confidence  # Base position on confidence
        
        executed = True
        shares = 0
        
        if decision == 'BUY':
            # Calculate number of shares to buy
            shares = int(position_size / current_price)
            cost = shares * current_price
            
            if cost <= self.portfolio['cash']:
                # Update portfolio
                if symbol not in self.portfolio['positions']:
                    self.portfolio['positions'][symbol] = {'shares': 0, 'price': 0}
                
                self.portfolio['positions'][symbol]['shares'] += shares
                self.portfolio['positions'][symbol]['price'] = current_price
                self.portfolio['cash'] -= cost
                
                reason = f"Bought {shares} shares at ${current_price:.2f} (cost: ${cost:.2f})"
            else:
                executed = False
                reason = "Insufficient cash for purchase"
                
        elif decision == 'SELL':
            if symbol in self.portfolio['positions']:
                shares = self.portfolio['positions'][symbol]['shares']
                if shares > 0:
                    proceeds = shares * current_price
                    self.portfolio['cash'] += proceeds
                    self.portfolio['positions'][symbol]['shares'] = 0
                    reason = f"Sold {shares} shares at ${current_price:.2f} (proceeds: ${proceeds:.2f})"
                else:
                    executed = False
                    reason = "No shares to sell"
            else:
                executed = False
                reason = "No position to sell"
        
        # Calculate current portfolio value
        current_value = self.portfolio['cash']
        for sym, pos in self.portfolio['positions'].items():
            last_price = self.portfolio['last_prices'].get(sym, pos['price'])
            current_value += pos['shares'] * last_price
        
        # Log the trade
        trade_record = {
            'date': current_date,
            'symbol': symbol,
            'decision': decision,
            'confidence': confidence,
            'reasoning': reasoning,
            'executed': executed,
            'reason': reason,
            'price': current_price,
            'shares': shares if executed else 0,
            'portfolio_value': current_value
        }
        
        # Add to portfolio trades
        self.portfolio['theoretical_trades'].append(trade_record)
        
        # Store in previous decisions for this symbol (limited by lookback window)
        self.previous_decisions[symbol].append(trade_record)
        if len(self.previous_decisions[symbol]) > self.lookback_window:
            self.previous_decisions[symbol].pop(0)  # Remove oldest decision
        
        self.logger.info(f"Trade recorded: {symbol} - {decision} (confidence: {confidence:.2f})")
        self.logger.info(f"Portfolio value: ${current_value:,.2f}")
        return executed
    
    def run_backtest(self, symbols=['NVO']):
        """Run the backtest for the specified date range."""
        self.logger.info(f"\nStarting date-filtered backtest from {self.start_date} to {self.end_date}")
        
        # Get trading calendar
        nyse = mcal.get_calendar('NYSE')
        trading_days = nyse.schedule(start_date=self.start_date, end_date=self.end_date)
        
        self.logger.info(f"Found {len(trading_days)} trading days")
        
        decisions_made = 0
        trades_executed = 0
        
        # Process each trading day
        for trading_date in trading_days.index:
            current_date = trading_date.strftime('%Y-%m-%d')
            self.logger.info(f"\n=== TRADING DAY: {current_date} ===")
            
            # Process each symbol
            for symbol in symbols:
                self.logger.info(f"\nProcessing {symbol}...")
                
                # Load all three analysis types
                valuation_data = self._get_latest_analysis(symbol, 'valuation', current_date)
                fundamental_data = self._get_latest_analysis(symbol, 'fundamental', current_date)
                sentiment_data = self._get_latest_analysis(symbol, 'sentiment', current_date)
                
                # Check if we have all required data
                if valuation_data and fundamental_data and sentiment_data:
                    self.logger.info(f"All analyses found for {symbol} - calling reasoning agent")
                    
                    try:
                        # Get previous decisions for context
                        previous_decisions = self.previous_decisions.get(symbol, [])
                        self.logger.info(f"Including {len(previous_decisions)} previous decisions as context")
                        
                        # Call reasoning agent with previous decisions as context
                        decision_result = self.reasoning_agent.make_decision(
                            symbol, current_date, valuation_data, fundamental_data, sentiment_data, 
                            previous_decisions=previous_decisions
                        )
                        
                        decision = decision_result.get('decision', 'HOLD')
                        confidence = decision_result.get('confidence', 0)
                        
                        self.logger.info(f"DECISION: {symbol} = {decision} (confidence: {confidence})")
                        decisions_made += 1
                        
                        # Execute the trade
                        if decision in ['BUY', 'SELL']:
                            if self._execute_trade(symbol, decision_result, current_date):
                                trades_executed += 1
                                
                    except Exception as e:
                        self.logger.error(f"Error making decision for {symbol}: {e}")
                        
                else:
                    missing = []
                    if not valuation_data: missing.append("valuation")
                    if not fundamental_data: missing.append("fundamental") 
                    if not sentiment_data: missing.append("sentiment")
                    self.logger.warning(f"Missing analyses for {symbol}: {missing}")
        
        # Calculate final portfolio value and performance
        final_value = self.portfolio['cash']
        for symbol, position in self.portfolio['positions'].items():
            final_value += position['shares'] * self.portfolio['last_prices'].get(symbol, position['price'])
        
        initial_value = 1000000  # Starting cash
        total_return = final_value - initial_value
        percent_return = (total_return / initial_value) * 100
        
        # Final results
        self.logger.info(f"\n=== BACKTEST COMPLETE ===")
        self.logger.info(f"Date range: {self.start_date} to {self.end_date}")
        self.logger.info(f"Decisions made: {decisions_made}")
        self.logger.info(f"Trades executed: {trades_executed}")
        self.logger.info(f"\nPORTFOLIO PERFORMANCE:")
        self.logger.info(f"Starting value: ${initial_value:,.2f}")
        self.logger.info(f"Final value: ${final_value:,.2f}")
        self.logger.info(f"Total return: ${total_return:,.2f} ({percent_return:.2f}%)")
        self.logger.info(f"\nFinal positions:")
        for symbol, position in self.portfolio['positions'].items():
            if position['shares'] > 0:
                value = position['shares'] * self.portfolio['last_prices'].get(symbol, position['price'])
                self.logger.info(f"- {symbol}: {position['shares']} shares @ ${self.portfolio['last_prices'].get(symbol, position['price']):.2f} = ${value:,.2f}")
        self.logger.info(f"Cash: ${self.portfolio['cash']:,.2f}")
        
        return {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'decisions_made': decisions_made,
            'trades_executed': trades_executed,
            'portfolio': self.portfolio,
            'performance': {
                'initial_value': initial_value,
                'final_value': final_value,
                'total_return': total_return,
                'percent_return': percent_return
            }
        }

def main():
    parser = argparse.ArgumentParser(description='Run date-filtered backtest')
    parser.add_argument('--data-dir', default=os.path.dirname(os.path.abspath(__file__)), 
                      help='Data directory (defaults to script directory)')
    parser.add_argument('--start-date', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--symbols', default='NVO', help='Comma-separated list of symbols to test')
    parser.add_argument('--lookback', type=int, default=4, help='Number of previous decisions to include as context')
    
    args = parser.parse_args()
    
    # Check if we have the required analysis files
    data_dir = args.data_dir
    symbols = args.symbols.split(',')
    
    # Verify that we have at least some analysis files for each symbol
    for symbol in symbols:
        valuation_pattern = os.path.join(data_dir, 'valuation_reports', f"{symbol}_*analysis*.json")
        fundamental_pattern = os.path.join(data_dir, 'fundamental_reports', f"{symbol}_*analysis*.json")
        sentiment_pattern = os.path.join(data_dir, 'sentiment_data', f"{symbol}_*analysis*.json")
        
        if not (glob.glob(valuation_pattern) and glob.glob(fundamental_pattern) and glob.glob(sentiment_pattern)):
            print(f"Warning: Missing some analysis files for {symbol}.")
    
    # Initialize and run backtest
    backtest = DateFilteredBacktest(
        data_dir=data_dir,
        start_date=args.start_date,
        end_date=args.end_date,
        lookback_window=args.lookback
    )
    
    results = backtest.run_backtest(symbols=symbols)
    
    # Save results to file
    results_file = os.path.join(data_dir, 'date_filtered_backtest_results.json')
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nTest complete! Results saved to {results_file}")
    print(f"Date range: {results['start_date']} to {results['end_date']}")
    print(f"Decisions made: {results['decisions_made']}")
    print(f"Trades executed: {results['trades_executed']}")
    print(f"\nPORTFOLIO PERFORMANCE:")
    print(f"Starting value: ${results['performance']['initial_value']:,.2f}")
    print(f"Final value: ${results['performance']['final_value']:,.2f}")
    print(f"Total return: ${results['performance']['total_return']:,.2f} ({results['performance']['percent_return']:.2f}%)")

if __name__ == "__main__":
    main()
