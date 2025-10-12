#!/usr/bin/env python3

import os
import sys
import json
import logging
import argparse
import glob
from datetime import datetime, timedelta
import pandas_market_calendars as mcal
from ReasoningAgent import ReasoningAgent
from typing import List

class WorkingOrchestrator:
    def __init__(self, data_dir="/home/ubuntu"):
        self.data_dir = data_dir
        self.portfolio = {
            'cash': 1000000,  # $1M starting cash
            'positions': {},
            'theoretical_trades': []
        }
        
        # Initialize only the reasoning agent
        self.reasoning_agent = ReasoningAgent(data_dir=data_dir)
        
        # Set up logging
        log_dir = os.path.join(data_dir, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(log_dir, 'working_backtest.log')),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Load stock price data
        self.stock_data = self._load_stock_data()
        self.logger.info(f"Loaded price data for {len(self.stock_data)} stocks")

    def _load_stock_data(self):
        """Load stock price data from stock_data_90days.json"""
        stock_data_file = os.path.join(self.data_dir, 'stock_data_90days.json')
        try:
            with open(stock_data_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load stock data: {e}")
            return {}

    def _get_price_for_date(self, symbol, date, price_type='open'):
        """Get stock price for specific date"""
        if symbol not in self.stock_data:
            return None
            
        date_str = date.strftime('%Y-%m-%d')
        historical_data = self.stock_data[symbol].get('historical_data', [])
        
        for day_data in historical_data:
            if day_data.get('date') == date_str:
                return day_data.get(price_type)
        return None

    def _load_analysis_file(self, filepath):
        """Load and return analysis data from a JSON file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                return data
        except Exception as e:
            self.logger.warning(f"Failed to load {filepath}: {e}")
            return None

    def _get_latest_analysis(self, symbol, analysis_type):
        """Get the latest analysis file for a symbol and type"""
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
            
        # Get the most recent file
        latest_file = max(files, key=os.path.getmtime)
        return self._load_analysis_file(latest_file)

    def _execute_trade(self, symbol, decision, current_date):
        """Execute a trade decision"""
        current_price = self._get_price_for_date(symbol, current_date, 'open')
        
        if not current_price:
            self.logger.warning(f"No price data for {symbol} on {current_date.date()}")
            return False

        executed = False
        reason = ""

        if decision == 'BUY':
            # Buy $100k worth
            shares_to_buy = 100000 / current_price
            cost = shares_to_buy * current_price
            
            if self.portfolio['cash'] >= cost:
                if symbol in self.portfolio['positions']:
                    self.portfolio['positions'][symbol] += shares_to_buy
                else:
                    self.portfolio['positions'][symbol] = shares_to_buy
                
                self.portfolio['cash'] -= cost
                executed = True
                reason = f"Bought {shares_to_buy:.2f} shares at ${current_price:.2f}"
                self.logger.info(f"BUY EXECUTED: {symbol} - {reason}")
            else:
                reason = "Insufficient cash"
                
        elif decision == 'SELL':
            if symbol in self.portfolio['positions'] and self.portfolio['positions'][symbol] > 0:
                shares = self.portfolio['positions'][symbol]
                proceeds = shares * current_price
                
                self.portfolio['cash'] += proceeds
                del self.portfolio['positions'][symbol]
                executed = True
                reason = f"Sold {shares:.2f} shares at ${current_price:.2f} for ${proceeds:.2f}"
                self.logger.info(f"SELL EXECUTED: {symbol} - {reason}")
            else:
                reason = "No position to sell"

        # Log all decisions (executed or not)
        self.portfolio['theoretical_trades'].append({
            'date': current_date.isoformat(),
            'symbol': symbol,
            'decision': decision,
            'price': current_price,
            'executed': executed,
            'reason': reason
        })

        return executed

    def _calculate_portfolio_value(self, current_date):
        """Calculate current portfolio value using current prices"""
        total_value = self.portfolio['cash']
        
        for symbol, shares in self.portfolio['positions'].items():
            current_price = self._get_price_for_date(symbol, current_date, 'open')
            if current_price:
                position_value = shares * current_price
                total_value += position_value
                
        return total_value

    def run_backtest(self, symbols: List[str], start_date: str = "2025-09-10", end_date: str = "2025-09-19"):
        """Run the backtest workflow"""
        print(f"\nStarting backtest from {start_date} to {end_date}")
        
        # Get trading calendar
        nyse = mcal.get_calendar('NYSE')
        trading_days = nyse.schedule(start_date=start_date, end_date=end_date)
        
        # Core trading symbols - 7 focused stocks (TMO removed)
        core_symbols = ['GOOGL', 'NVDA', 'PLTR', 'ABBV', 'UNH', 'JPM', 'RKLB']
        
        decisions_made = 0
        trades_executed = 0
        
        for trading_date in trading_days.index:
            current_date = trading_date.to_pydatetime().replace(hour=0, minute=0, second=0, microsecond=0)
            self.logger.info(f"\n=== TRADING DAY: {current_date.date()} ===")
            
            # Calculate current portfolio value
            portfolio_value = self._calculate_portfolio_value(current_date)
            self.logger.info(f"Portfolio value: ${portfolio_value:,.2f}")
            
            # Process each symbol
            for symbol in core_symbols:
                self.logger.info(f"\nProcessing {symbol}...")
                
                # Load all three analysis types
                valuation_data = self._get_latest_analysis(symbol, 'valuation')
                fundamental_data = self._get_latest_analysis(symbol, 'fundamental')
                sentiment_data = self._get_latest_analysis(symbol, 'sentiment')
                
                # Check if we have all required data
                if valuation_data and fundamental_data and sentiment_data:
                    self.logger.info(f"All analyses found for {symbol} - calling reasoning agent")
                    
                    try:
                        # Call reasoning agent
                        decision_result = self.reasoning_agent.make_decision(
                            symbol, current_date, valuation_data, fundamental_data, sentiment_data
                        )
                        
                        decision = decision_result.get('decision', 'HOLD')
                        confidence = decision_result.get('confidence', 0)
                        
                        self.logger.info(f"DECISION: {symbol} = {decision} (confidence: {confidence})")
                        decisions_made += 1
                        
                        # Execute the trade
                        if decision in ['BUY', 'SELL']:
                            if self._execute_trade(symbol, decision, current_date):
                                trades_executed += 1
                                
                    except Exception as e:
                        self.logger.error(f"Error making decision for {symbol}: {e}")
                        
                else:
                    missing = []
                    if not valuation_data: missing.append("valuation")
                    if not fundamental_data: missing.append("fundamental") 
                    if not sentiment_data: missing.append("sentiment")
                    self.logger.warning(f"Missing analyses for {symbol}: {missing}")

        # Final results
        final_value = self._calculate_portfolio_value(end_date)
        total_return = ((final_value - 1000000) / 1000000) * 100
        
        self.logger.info(f"\n=== BACKTEST COMPLETE ===")
        self.logger.info(f"Final portfolio value: ${final_value:,.2f}")
        self.logger.info(f"Total return: {total_return:.2f}%")
        self.logger.info(f"Decisions made: {decisions_made}")
        self.logger.info(f"Trades executed: {trades_executed}")
        self.logger.info(f"Final positions: {len(self.portfolio['positions'])}")
        
        return {
            'final_value': final_value,
            'total_return': total_return,
            'decisions_made': decisions_made,
            'trades_executed': trades_executed,
            'portfolio': self.portfolio
        }

def main():
    parser = argparse.ArgumentParser(description='Run backtest')
    parser.add_argument('--data-dir', default='/home/ubuntu', help='Data directory')
    parser.add_argument('--start-date', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', required=True, help='End date (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
    
    orchestrator = WorkingOrchestrator(data_dir=args.data_dir)
    results = orchestrator.run_backtest(start_date, end_date)
    
    print(f"\n🎯 BACKTEST RESULTS:")
    print(f"Final Value: ${results['final_value']:,.2f}")
    print(f"Total Return: {results['total_return']:.2f}%")
    print(f"Decisions Made: {results['decisions_made']}")
    print(f"Trades Executed: {results['trades_executed']}")

if __name__ == "__main__":
    main()
