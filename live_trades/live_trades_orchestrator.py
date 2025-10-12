"""
Live Trades Orchestrator
====================

Coordinates the trading workflow across multiple agents for live trading analysis.
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Iterator, Optional, Dict, Any, List
import pandas as pd
import pandas_market_calendars as mcal
from dotenv import load_dotenv
import json
import glob
from logging.handlers import RotatingFileHandler
import numpy as np

# Add parent directory to Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Load environment variables from .env file
load_dotenv()

# Import agents
from ValuationAgent import ValuationAgent
from FundamentalAgent import FundamentalAgent
from SentimentAgent import SentimentAgent
from single_stock_test.ReasoningAgent import ReasoningAgent

def normalize_timestamp(ts: pd.Timestamp) -> pd.Timestamp:
    """Convert timestamp to naive (remove timezone info)"""
    if ts.tzinfo is not None:
        ts = ts.tz_localize(None)
    return ts

def load_stock_data() -> Dict:
    """Load stock data from valuation data file."""
    try:
        with open("live_trades/valuation_data/stock_data_valuation.json", "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading stock data: {e}")
        return {}

def get_historical_data(data: Dict, before_date: pd.Timestamp) -> List[Dict]:
    """Get historical data up to given date."""
    historical = []
    before_date = normalize_timestamp(before_date)
    
    for entry in data.get('historical_prices', []):
        entry_date = pd.Timestamp(entry['date'])
        if entry_date <= before_date:
            historical.append(entry)
    
    return historical

def get_daily_data(data: Dict, target_date: pd.Timestamp) -> Optional[Dict]:
    """Get data for specific date."""
    target_date = normalize_timestamp(target_date)
    target_str = target_date.strftime('%Y-%m-%d')
    
    for entry in data.get('historical_prices', []):
        if entry['date'] == target_str:
            return entry
    
    return None

class DateRangeIterator:
    """Iterator that yields trading days between start and end dates."""
    
    def __init__(self, start_date: str, end_date: str, trading_days_only: bool = True):
        """
        Initialize date range iterator.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            trading_days_only: If True, only yield trading days
        """
        self.start_date = pd.Timestamp(start_date)
        self.end_date = pd.Timestamp(end_date)
        self.trading_days_only = trading_days_only
        
        if trading_days_only:
            # Get NYSE calendar
            nyse = mcal.get_calendar('NYSE')
            self.trading_days = nyse.valid_days(
                start_date=self.start_date,
                end_date=self.end_date
            )
            self.current_idx = 0
        else:
            self.current_date = self.start_date
    
    def __iter__(self):
        return self
    
    def __next__(self) -> pd.Timestamp:
        """Get next trading day."""
        if self.trading_days_only:
            if self.current_idx >= len(self.trading_days):
                raise StopIteration
            next_day = self.trading_days[self.current_idx]
            self.current_idx += 1
            return normalize_timestamp(next_day)
        else:
            if self.current_date > self.end_date:
                raise StopIteration
            next_day = self.current_date
            self.current_date += timedelta(days=1)
            return normalize_timestamp(next_day)

class BacktestOrchestrator:
    """Orchestrates the backtesting workflow."""
    
    def __init__(
        self,
        data_dir: str = ".",
        start_date: str = "2025-09-05",
        end_date: str = "2025-09-19",
        stocks: List[str] = None
    ):
        """Initialize orchestrator."""
        self.data_dir = data_dir
        self.start_date = start_date
        self.end_date = end_date
        
        # Default stock list if none provided
        self.stocks = stocks or [
            "GOOGL",  # Alphabet Inc.
            "NVDA",   # NVIDIA Corporation  
            "PLTR",   # Palantir Technologies Inc.
            "ABBV",   # AbbVie Inc.
            "UNH",    # UnitedHealth Group Incorporated
            "JPM",    # JPMorgan Chase & Co.
            "RKLB"    # Rocket Lab USA, Inc.
        ]
        
        # Set up logging
        log_dir = os.path.join(data_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        self.logger = logging.getLogger("backtest")
        self.logger.setLevel(logging.INFO)
        
        # Add rotating file handler
        log_file = os.path.join(log_dir, "backtest.log")
        handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)
        
        # Add console handler
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(console)
        
        # Initialize agents
        self.valuation_agent = ValuationAgent(data_dir=data_dir)
        self.fundamental_agent = FundamentalAgent(data_dir=data_dir)
        self.sentiment_agent = SentimentAgent(data_dir=data_dir)
        self.reasoning_agent = ReasoningAgent(data_dir=data_dir)
        
        # Initialize portfolio tracking
        self.portfolio = {}
        self.trades = []
        self.cash = 1000000  # $1M starting capital
        
        # Load stock data
        self.stock_data = load_stock_data()
        
        self.logger.info(f"Initialized backtest orchestrator:")
        self.logger.info(f"- Date range: {start_date} to {end_date}")
        self.logger.info(f"- Stocks: {', '.join(self.stocks)}")
        self.logger.info(f"- Starting capital: ${self.cash:,.2f}")
    
    def _prepare_historical_context(self, symbol: str, before_date: pd.Timestamp) -> Dict:
        """Prepare historical context up to given date."""
        if symbol not in self.stock_data:
            return {}
            
        data = self.stock_data[symbol]
        historical_prices = get_historical_data(data, before_date)
        
        # Get fundamental data
        fundamental_file = os.path.join(self.data_dir, "fundamental_reports", f"{symbol}_fundamental_analysis_*.json")
        fundamental_files = glob.glob(fundamental_file)
        fundamental_data = None
        if fundamental_files:
            try:
                with open(fundamental_files[-1], 'r') as f:
                    fundamental_data = json.load(f)
            except Exception as e:
                self.logger.error(f"Error reading fundamental data for {symbol}: {e}")
        
        # Get sentiment data
        sentiment_file = os.path.join(self.data_dir, "sentiment_data", f"{symbol}_sentiment_analysis_*.json")
        sentiment_files = glob.glob(sentiment_file)
        sentiment_data = None
        if sentiment_files:
            try:
                with open(sentiment_files[-1], 'r') as f:
                    sentiment_data = json.load(f)
            except Exception as e:
                self.logger.error(f"Error reading sentiment data for {symbol}: {e}")
        
        return {
            'symbol': symbol,
            'historical_prices': historical_prices,
            'fundamental_data': fundamental_data,
            'sentiment_data': sentiment_data
        }
    
    def _prepare_daily_data(self, symbol: str, date: pd.Timestamp) -> Dict:
        """Prepare data for specific date."""
        if symbol not in self.stock_data:
            return {}
            
        data = self.stock_data[symbol]
        daily_price = get_daily_data(data, date)
        if not daily_price:
            return {}
        
        # Get fundamental data
        fundamental_file = os.path.join(self.data_dir, "fundamental_reports", f"{symbol}_fundamental_analysis_*.json")
        fundamental_files = glob.glob(fundamental_file)
        fundamental_data = None
        if fundamental_files:
            try:
                with open(fundamental_files[-1], 'r') as f:
                    fundamental_data = json.load(f)
            except Exception as e:
                self.logger.error(f"Error reading fundamental data for {symbol}: {e}")
        
        # Get sentiment data
        sentiment_file = os.path.join(self.data_dir, "sentiment_data", f"{symbol}_sentiment_analysis_*.json")
        sentiment_files = glob.glob(sentiment_file)
        sentiment_data = None
        if sentiment_files:
            try:
                with open(sentiment_files[-1], 'r') as f:
                    sentiment_data = json.load(f)
            except Exception as e:
                self.logger.error(f"Error reading sentiment data for {symbol}: {e}")
        
        return {
            'symbol': symbol,
            'daily_price': daily_price,
            'fundamental_data': fundamental_data,
            'sentiment_data': sentiment_data
        }
    
    def _get_stock_price(self, symbol: str, date: pd.Timestamp, price_type: str = 'close') -> float:
        """Get stock price for given date."""
        try:
            if symbol not in self.stock_data:
                return 0.0
            
            data = self.stock_data[symbol]
            daily_data = get_daily_data(data, date)
            if not daily_data:
                return 0.0
            
            return float(daily_data.get(price_type, 0.0))
            
        except Exception as e:
            self.logger.error(f"Error getting price for {symbol} on {date}: {e}")
            return 0.0
    
    def _update_portfolio(self, date: pd.Timestamp):
        """Update portfolio values based on current prices."""
        total_value = self.cash
        
        for symbol, position in self.portfolio.items():
            current_price = self._get_stock_price(symbol, date)
            position['current_price'] = current_price
            position['current_value'] = position['shares'] * current_price
            total_value += position['current_value']
            
        return total_value
    
    def _execute_trade(self, date: pd.Timestamp, symbol: str, decision: Dict):
        """Execute a trade based on agent decision."""
        action = decision.get('action', 'HOLD')
        confidence = float(decision.get('confidence', 0))
        price = self._get_stock_price(symbol, date, 'open')  # Use opening price
        
        if price <= 0:
            self.logger.warning(f"Invalid price ({price}) for {symbol} on {date}")
            return
            
        if action == 'BUY' and confidence >= 0.6:
            # Calculate position size based on confidence
            position_size = min(0.1 * self.cash, 0.1 * self.cash * confidence)
            shares = int(position_size / price)
            
            if shares > 0 and position_size <= self.cash:
                cost = shares * price
                self.cash -= cost
                
                if symbol not in self.portfolio:
                    self.portfolio[symbol] = {
                        'shares': shares,
                        'avg_price': price,
                        'cost_basis': cost
                    }
                else:
                    # Update existing position
                    position = self.portfolio[symbol]
                    total_shares = position['shares'] + shares
                    total_cost = position['cost_basis'] + cost
                    position['shares'] = total_shares
                    position['avg_price'] = total_cost / total_shares
                    position['cost_basis'] = total_cost
                
                self.trades.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'symbol': symbol,
                    'action': 'BUY',
                    'shares': shares,
                    'price': price,
                    'value': cost,
                    'confidence': confidence
                })
                
                self.logger.info(f"Bought {shares} shares of {symbol} at ${price:.2f}")
                
        elif action == 'SELL' and confidence >= 0.6:
            if symbol in self.portfolio and self.portfolio[symbol]['shares'] > 0:
                position = self.portfolio[symbol]
                shares = position['shares']
                value = shares * price
                gain = value - position['cost_basis']
                
                self.cash += value
                position['shares'] = 0
                position['current_value'] = 0
                
                self.trades.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'symbol': symbol,
                    'action': 'SELL',
                    'shares': shares,
                    'price': price,
                    'value': value,
                    'gain': gain,
                    'confidence': confidence
                })
                
                self.logger.info(f"Sold {shares} shares of {symbol} at ${price:.2f} for {'profit' if gain > 0 else 'loss'} of ${abs(gain):.2f}")
    
    def run(self):
        """Run the backtest."""
        self.logger.info("\nStarting backtest...")
        
        # Initialize metrics tracking
        daily_values = []
        dates = []
        
        # Iterate through trading days
        date_iterator = DateRangeIterator(self.start_date, self.end_date)
        
        # First day: establish historical context
        first_date = next(date_iterator)
        self.logger.info(f"\nEstablishing historical context up to {first_date.strftime('%Y-%m-%d')}:")
        
        # Process each stock with historical context
        for symbol in self.stocks:
            try:
                # Get historical context
                context = self._prepare_historical_context(symbol, first_date)
                if not context:
                    self.logger.warning(f"Missing historical data for {symbol}")
                    continue
                
                # Get trading decision
                decision = self.reasoning_agent.make_decision(
                    symbol=symbol,
                    historical_context=context,
                    current_date=first_date.strftime('%Y-%m-%d')
                )
                
                if decision:
                    self._execute_trade(first_date, symbol, decision)
                
            except Exception as e:
                self.logger.error(f"Error processing {symbol}: {e}")
                continue
        
        # Update portfolio value for first day
        total_value = self._update_portfolio(first_date)
        daily_values.append(total_value)
        dates.append(first_date)
        self.logger.info(f"Portfolio Value: ${total_value:,.2f}")
        
        # Process remaining days
        for current_date in date_iterator:
            self.logger.info(f"\nProcessing {current_date.strftime('%Y-%m-%d')}:")
            
            # Process each stock
            for symbol in self.stocks:
                try:
                    # Get daily data
                    daily_data = self._prepare_daily_data(symbol, current_date)
                    if not daily_data:
                        self.logger.warning(f"Missing daily data for {symbol}")
                        continue
                    
                    # Get trading decision
                    decision = self.reasoning_agent.make_decision(
                        symbol=symbol,
                        daily_data=daily_data,
                        current_date=current_date.strftime('%Y-%m-%d')
                    )
                    
                    if decision:
                        self._execute_trade(current_date, symbol, decision)
                    
                except Exception as e:
                    self.logger.error(f"Error processing {symbol}: {e}")
                    continue
            
            # Update portfolio value
            total_value = self._update_portfolio(current_date)
            daily_values.append(total_value)
            dates.append(current_date)
            self.logger.info(f"Portfolio Value: ${total_value:,.2f}")
        
        # Calculate final metrics
        initial_value = daily_values[0]
        final_value = daily_values[-1]
        total_return = (final_value - initial_value) / initial_value * 100
        
        # Calculate daily returns
        daily_returns = pd.Series(daily_values).pct_change().dropna()
        
        # Annualize metrics
        trading_days = len(dates)
        ann_return = ((1 + total_return/100) ** (252/trading_days) - 1) * 100
        ann_volatility = daily_returns.std() * np.sqrt(252) * 100
        sharpe_ratio = ann_return / ann_volatility if ann_volatility > 0 else 0
        
        # Calculate drawdown
        rolling_max = pd.Series(daily_values).expanding().max()
        drawdowns = (pd.Series(daily_values) - rolling_max) / rolling_max * 100
        max_drawdown = drawdowns.min()
        
        # Save results
        results = {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'initial_value': initial_value,
            'final_value': final_value,
            'total_return_pct': total_return,
            'annualized_return_pct': ann_return,
            'annualized_volatility_pct': ann_volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown_pct': max_drawdown,
            'trades': self.trades,
            'daily_values': list(zip([d.strftime('%Y-%m-%d') for d in dates], daily_values))
        }
        
        results_file = os.path.join(self.data_dir, "backtest_results.json")
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        self.logger.info("\nBacktest Complete!")
        self.logger.info("=" * 40)
        self.logger.info(f"Total Return: {total_return:.2f}%")
        self.logger.info(f"Annualized Return: {ann_return:.2f}%")
        self.logger.info(f"Annualized Volatility: {ann_volatility:.2f}%")
        self.logger.info(f"Sharpe Ratio: {sharpe_ratio:.2f}")
        self.logger.info(f"Maximum Drawdown: {max_drawdown:.2f}%")
        self.logger.info(f"Number of Trades: {len(self.trades)}")
        self.logger.info(f"\nResults saved to {results_file}")

def main():
    """Main function to run backtest."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run stock trading backtest")
    parser.add_argument("--data-dir", default=".", help="Directory containing data files")
    parser.add_argument("--start-date", default="2025-09-05", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", default="2025-09-19", help="End date (YYYY-MM-DD)")
    args = parser.parse_args()
    
    orchestrator = BacktestOrchestrator(
        data_dir=args.data_dir,
        start_date=args.start_date,
        end_date=args.end_date
    )
    
    orchestrator.run()

if __name__ == "__main__":
    main() 