"""
Backtest Orchestrator
===================

Coordinates the backtesting workflow across multiple agents with AWS integration
for logging, monitoring, and error handling.
"""

import os
import boto3
from datetime import datetime, timedelta
from typing import Iterator, Optional, Dict, Any, List
import pandas as pd
import pandas_market_calendars as mcal
from dotenv import load_dotenv
import json
import glob
import logging
from logging.handlers import RotatingFileHandler
import numpy as np

# Load environment variables from .env file
load_dotenv()

from ValuationAgent import ValuationAgent
from FundamentalAgent import FundamentalAgent
from SentimentAgent import SentimentAgent
from single_stock_test.ReasoningAgent import ReasoningAgent

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
            return next_day
        else:
            if self.current_date > self.end_date:
                raise StopIteration
            next_day = self.current_date
            self.current_date += timedelta(days=1)
            return next_day

class ErrorHandler:
    """Handles errors during backtesting."""
    
    def __init__(self, logger: logging.Logger, sns_client=None, sns_topic: str = None):
        """
        Initialize error handler.
        
        Args:
            logger: Logger instance
            sns_client: Optional boto3 SNS client
            sns_topic: Optional SNS topic ARN for alerts
        """
        self.logger = logger
        self.sns = sns_client
        self.sns_topic = sns_topic
    
    def handle(self, error: Exception):
        """
        Handle an error.
        
        Args:
            error: The exception to handle
        """
        # Log the error
        self.logger.error(f"Error during backtest: {str(error)}", exc_info=True)
        
        # Send SNS notification if configured
        if self.sns and self.sns_topic:
            try:
                self.sns.publish(
                    TopicArn=self.sns_topic,
                    Subject="Backtest Error",
                    Message=f"Error during backtest: {str(error)}"
                )
            except Exception as e:
                self.logger.error(f"Failed to send SNS notification: {str(e)}")

class CloudWatchLogger:
    """Handles CloudWatch logging."""
    
    def __init__(self, log_group: str = "trading-agents", log_stream: str = None):
        """
        Initialize CloudWatch logger.
        
        Args:
            log_group: CloudWatch log group name
            log_stream: CloudWatch log stream name
        """
        self.logs_client = boto3.client('logs')
        self.log_group = log_group
        self.log_stream = log_stream or f"backtest-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Create log group if it doesn't exist
        try:
            self.logs_client.create_log_group(logGroupName=self.log_group)
        except self.logs_client.exceptions.ResourceAlreadyExistsException:
            pass
        
        # Create log stream
        try:
            self.logs_client.create_log_stream(
                logGroupName=self.log_group,
                logStreamName=self.log_stream
            )
        except self.logs_client.exceptions.ResourceAlreadyExistsException:
            pass
    
    def log(self, message: str, level: str = "INFO"):
        """Log message to CloudWatch."""
        try:
            self.logs_client.put_log_events(
                logGroupName=self.log_group,
                logStreamName=self.log_stream,
                logEvents=[{
                    'timestamp': int(datetime.now().timestamp() * 1000),
                    'message': f"[{level}] {message}"
                }]
            )
        except Exception as e:
            print(f"Failed to log to CloudWatch: {str(e)}")

class BacktestOrchestrator:
    """Orchestrates the backtesting workflow across all agents."""
    
    def __init__(self, data_dir: str = "/home/ubuntu"):
        """Initialize the orchestrator."""
        # Set data directory for AWS environment
        self.data_dir = data_dir
        
        # Set up logging
        self.logger = self._setup_logger()
        
        # Initialize agents with data directory
        self.valuation_agent = ValuationAgent(data_dir=self.data_dir)
        self.fundamental_agent = FundamentalAgent(data_dir=self.data_dir)
        self.sentiment_agent = SentimentAgent(data_dir=self.data_dir)
        self.reasoning_agent = ReasoningAgent(data_dir=self.data_dir)
        
        # Initialize AWS services
        self.cloudwatch_logger = CloudWatchLogger()
        self.error_handler = ErrorHandler(self.logger)
        
        # Initialize portfolio
        self.portfolio = {
            'cash': 1000000,  # Start with $1M
            'positions': {},  # {symbol: {'shares': int, 'cost_basis': float}}
            'history': [],     # List of all transactions
            'theoretical_trades': [],  # All decisions, including hypothetical
            'metrics': {      # Performance metrics
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'calmar_ratio': 0,
                'daily_returns': [],
                'cumulative_returns': []
            }
        }
        
        # Track daily portfolio values for metrics calculation
        self.daily_portfolio_values = []
    
    def _setup_logger(self) -> logging.Logger:
        """Set up logging configuration."""
        logger = logging.getLogger('backtest_orchestrator')
        logger.setLevel(logging.INFO)
        
        # Create logs directory if it doesn't exist
        log_dir = os.path.join(self.data_dir, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # File handler
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, 'backtest_orchestrator.log'),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def _get_latest_analysis_before_date(self, symbol: str, analysis_type: str, directory: str, current_date: str) -> Optional[Dict]:
        """
        Load the latest analysis file for a symbol that was created before or on the current date.
        This ensures we don't use future data (avoiding look-ahead bias).
        """
        # Construct directory path
        dir_path = os.path.join(self.data_dir, directory)
        if not os.path.exists(dir_path):
            self.logger.warning(f"Directory {dir_path} does not exist")
            return None
        
        # Get the current date as pd.Timestamp for comparison
        current_timestamp = pd.Timestamp(current_date)
        
        # Find all analysis files for this symbol
        pattern = f"{symbol}_{analysis_type}_analysis_*.json"
        files = glob.glob(os.path.join(dir_path, pattern))
        
        if not files:
            self.logger.warning(f"No {analysis_type} files found for {symbol} in {dir_path}")
            return None
        
        valid_files = []
        
        for file_path in files:
        try:
                # Load the file to read the date field
                with open(file_path, 'r') as f:
                data = json.load(f)
                
                # Get the date from the data
                file_date_str = data.get('date')
                if not file_date_str:
                    self.logger.warning(f"No date field found in {file_path}")
                    continue
                
                file_date = pd.Timestamp(file_date_str)
                
                # Only consider files with dates on or before current date
                if file_date <= current_timestamp:
                    valid_files.append((file_date, file_path, data))
                
            except Exception as e:
                self.logger.error(f"Error reading {file_path}: {str(e)}")
                continue
        
        if not valid_files:
            self.logger.warning(f"No valid {analysis_type} files found for {symbol} before {current_date}")
            return None
        
        # Get the latest valid file
        latest_file = max(valid_files, key=lambda x: x[0])
        self.logger.info(f"Using {analysis_type} analysis from {latest_file[1]} (date: {latest_file[0]})")
        
        return latest_file[2]  # Return the loaded data
    
    def _load_stock_data(self) -> Dict:
        """Load the main stock data file with historical prices."""
        try:
            stock_data_file = os.path.join(self.data_dir, 'stock_data_90days.json')
            if not os.path.exists(stock_data_file):
                self.logger.error(f"Stock data file not found: {stock_data_file}")
                return {}
            
            with open(stock_data_file, 'r') as f:
                stock_data = json.load(f)
            
            self.logger.info(f"Loaded stock data for {len(stock_data)} symbols")
            return stock_data
        except Exception as e:
            self.logger.error(f"Error loading stock data: {str(e)}")
            return {}

    def _get_price_for_date(self, symbol: str, date: str, price_type: str = 'close') -> Optional[float]:
        """Get the price for a symbol on a specific date from the main stock data.
        
        Args:
            symbol: Stock symbol
            date: Date in YYYY-MM-DD format
            price_type: 'open', 'close', 'high', 'low'
        """
        try:
            if not hasattr(self, '_stock_data'):
                self._stock_data = self._load_stock_data()
            
            if symbol not in self._stock_data:
                self.logger.warning(f"No stock data found for {symbol}")
                return None
            
            historical_data = self._stock_data[symbol].get('historical_data', [])
            
            # Convert date to match the format in stock data
            target_date = pd.Timestamp(date).strftime('%Y-%m-%d')
            
            for point in historical_data:
                point_date = point.get('date', '')
                # Handle different date formats
                if point_date == target_date or point_date == date:
                    price = point.get(price_type)
                    if price:
                        return float(price)
            
            # If exact date not found, find the closest previous date
            valid_points = []
            for point in historical_data:
                point_date = point.get('date', '')
                try:
                    point_timestamp = pd.Timestamp(point_date)
                    target_timestamp = pd.Timestamp(date)
                    if point_timestamp <= target_timestamp:
                        valid_points.append((point_timestamp, point))
                except:
                    continue
            
            if valid_points:
                # Get the most recent price before or on the target date
                latest_point = max(valid_points, key=lambda x: x[0])[1]
                price = latest_point.get(price_type)
                if price:
                    self.logger.debug(f"Using closest price for {symbol} on {date}: ${price}")
                    return float(price)
            
            self.logger.warning(f"No price data found for {symbol} on {date}")
            return None
                
        except Exception as e:
            self.logger.error(f"Error getting price for {symbol} on {date}: {str(e)}")
            return None
    
    def _get_opening_price_for_date(self, symbol: str, date: str) -> Optional[float]:
        """Get the opening price for a symbol on a specific date."""
        return self._get_price_for_date(symbol, date, 'open')

    def _get_closing_price_for_date(self, symbol: str, date: str) -> Optional[float]:
        """Get the closing price for a symbol on a specific date."""
        return self._get_price_for_date(symbol, date, 'close')

    def _calculate_portfolio_value(self, current_date: str = None) -> float:
        """Calculate total portfolio value including positions.
        
        Args:
            current_date: If provided, use current market prices from this date for positions.
                         If None, use cost basis (for final calculations).
        """
        total_value = self.portfolio['cash']
        
        for symbol, position in self.portfolio['positions'].items():
            if current_date:
                # Use current day's market price for realistic P&L
                current_price = self._get_closing_price_for_date(symbol, current_date)
                if current_price:
                    position_value = position['shares'] * current_price
                    self.logger.debug(f"{symbol}: {position['shares']} shares × ${current_price:.2f} (market) = ${position_value:,.2f}")
                else:
                    # Fallback to cost basis if no market price available
                    position_value = position['shares'] * position['cost_basis']
                    self.logger.warning(f"No market price for {symbol} on {current_date}, using cost basis")
            else:
                # Use cost basis for final calculations or when no date provided
                position_value = position['shares'] * position['cost_basis']
            
            total_value += position_value
        
        return total_value

    def _update_portfolio(self, symbol: str, decision: Dict, valuation: Dict):
        """Update portfolio based on trading decision."""
        action = decision['decision'].upper()
        current_date = decision.get('date', datetime.now().isoformat()[:10])  # Ensure YYYY-MM-DD format
        
        # Get current market price instead of using valuation current_price
        current_price = self._get_closing_price_for_date(symbol, current_date)
        if not current_price:
            # Fallback to valuation price if no market data
            current_price = valuation.get('current_price', 0)
            self.logger.warning(f"Using valuation price for {symbol}: ${current_price}")
        
        # Log all decisions in theoretical trades
        theoretical_trade = {
            'date': current_date,
            'symbol': symbol,
            'action': action,
            'price': current_price,
            'confidence': decision.get('confidence', 0),
            'executed': False,  # Whether the trade was actually executed
            'reason': ''  # Why a trade wasn't executed
        }
        
        if action == 'BUY':
            # Calculate position size (10% of portfolio per position)
            max_position = self.portfolio['cash'] * 0.10
            shares_to_buy = int(max_position / current_price)
            
            if shares_to_buy > 0:
                cost = shares_to_buy * current_price
                if cost <= self.portfolio['cash']:
                    # Add new position
                    if symbol not in self.portfolio['positions']:
                        self.portfolio['positions'][symbol] = {
                            'shares': shares_to_buy,
                            'cost_basis': current_price
                        }
                    else:
                        # Average down existing position
                        current_shares = self.portfolio['positions'][symbol]['shares']
                        current_cost = self.portfolio['positions'][symbol]['cost_basis']
                        new_shares = current_shares + shares_to_buy
                        new_cost = ((current_shares * current_cost) + (shares_to_buy * current_price)) / new_shares
                        self.portfolio['positions'][symbol] = {
                            'shares': new_shares,
                            'cost_basis': new_cost
                        }
                    
                    # Update cash
                    self.portfolio['cash'] -= cost
                    
                    # Log actual transaction
                    trade = {
                        'date': current_date,
                        'symbol': symbol,
                        'action': 'BUY',
                        'shares': shares_to_buy,
                        'price': current_price,
                        'total': cost
                    }
                    self.portfolio['history'].append(trade)
                    
                    # Update theoretical trade
                    theoretical_trade.update({
                        'executed': True,
                        'shares': shares_to_buy,
                        'total': cost
                    })
                    
                    print(f"    ✅ Bought {shares_to_buy} shares of {symbol} @ ${current_price:.2f}")
                else:
                    theoretical_trade['reason'] = 'Insufficient cash'
                    print(f"    ⚠️  Insufficient cash to buy {symbol}")
            else:
                theoretical_trade['reason'] = 'Position size too small'
                print(f"    ⚠️  Position size too small for {symbol}")
                
        elif action == 'SELL':
            # Calculate theoretical sell for tracking
            theoretical_shares = 0
            if symbol in self.portfolio['positions']:
                position = self.portfolio['positions'][symbol]
                theoretical_shares = position['shares']
                proceeds = theoretical_shares * current_price
                
                # Remove position and update cash
                del self.portfolio['positions'][symbol]
                self.portfolio['cash'] += proceeds
                
                # Log actual transaction
                trade = {
                    'date': current_date,
                    'symbol': symbol,
                    'action': 'SELL',
                    'shares': theoretical_shares,
                    'price': current_price,
                    'total': proceeds
                }
                self.portfolio['history'].append(trade)
                
                # Update theoretical trade
                theoretical_trade.update({
                    'executed': True,
                    'shares': theoretical_shares,
                    'total': proceeds
                })
                
                print(f"    ✅ Sold {theoretical_shares} shares of {symbol} @ ${current_price:.2f}")
            else:
                # Log theoretical sell for non-held position
                theoretical_trade.update({
                    'shares': 0,
                    'total': 0,
                    'reason': 'Position not held'
                })
                print(f"    ℹ️  Sell signal for {symbol} (not held) @ ${current_price:.2f}")
        
        elif action == 'HOLD':
            theoretical_trade['reason'] = 'Hold decision'
            print(f"    ✅ Holding {symbol}")
        
        # Always log the theoretical trade
        self.portfolio['theoretical_trades'].append(theoretical_trade)

    def run_workflow(self, symbols: List[str], start_date: str = "2025-06-12", end_date: str = "2025-06-15"):
        """Run complete backtest workflow using pre-computed analyses."""
        try:
            print(f"\nStarting backtest from {start_date} to {end_date}")
            print(f"Data directory: {self.data_dir}")
            print(f"Tracking {len(symbols)} symbols: {', '.join(symbols)}")
            print("\nInitial Portfolio:")
            print(f"💰 Cash: ${self.portfolio['cash']:,.2f}")
            print("📊 Positions: None")
            print("\n" + "="*50)
            
            self.logger.info(f"Starting backtest for {len(symbols)} symbols from {start_date} to {end_date}")
            
            for date in DateRangeIterator(start_date, end_date):
                current_date = date.strftime('%Y-%m-%d')
                print(f"\n📅 Trading Day: {current_date}")
                print("="*50)
                daily_decisions = []
                
                for symbol in symbols:
                    print(f"\n📈 Analyzing {symbol}:")
                    
                    # Load pre-computed analyses that were available before this date
                    print("  - Loading valuation analysis...")
                    valuation = self._get_latest_analysis_before_date(
                        symbol, 'technical', 'valuation_reports', current_date
                    )
                    if valuation:
                        print("    ✓ Valuation loaded")
                    
                    print("  - Loading fundamental analysis...")
                    fundamental = self._get_latest_analysis_before_date(
                        symbol, 'fundamental', 'fundamental_reports', current_date
                    )
                    if fundamental:
                        print("    ✓ Fundamental loaded")
                    
                    print("  - Loading sentiment analysis...")
                    sentiment = self._get_latest_analysis_before_date(
                        symbol, 'sentiment', 'sentiment_data', current_date
                    )
                    if sentiment:
                        print("    ✓ Sentiment loaded")
                    
                    # Only proceed if we have all analyses
                    if all([valuation, fundamental, sentiment]):
                        print("  - Getting final decision...")
                        
                        # Prepare context with all analyses
                        context = {
                            'valuation_analysis': valuation,
                            'fundamental_analysis': fundamental,
                            'sentiment_analysis': sentiment,
                            'date': current_date
                        }
                        
                        # Get final decision from ReasoningAgent
                        decision = self.reasoning_agent.make_decision(
                            symbol=symbol,
                            analyses=context
                        )
                        
                        if decision:
                            daily_decisions.append((symbol, decision))
                            self._update_portfolio(symbol, decision, valuation)
                        else:
                            print("    ⚠️  No decision made")
                    else:
                        missing = []
                        if not valuation: missing.append("valuation")
                        if not fundamental: missing.append("fundamental")
                        if not sentiment: missing.append("sentiment")
                        print(f"    ⚠️  Missing analyses: {', '.join(missing)}")
                
                # Calculate and track daily portfolio value using current day's opening prices
                daily_value = self._calculate_portfolio_value(current_date)
                self.daily_portfolio_values.append({
                    'date': current_date,
                    'portfolio_value': daily_value,
                    'cash': self.portfolio['cash'],
                    'positions': dict(self.portfolio['positions']),
                    'trades': [h for h in self.portfolio['history'] if h.get('date', '').startswith(current_date)]
                })
                
                # Print end of day summary
                print("\n📊 End of Day Summary:")
                print(f"  Portfolio Value: ${daily_value:,.2f}")
                print(f"  Cash Balance: ${self.portfolio['cash']:,.2f}")
                if self.portfolio['positions']:
                    print("\n  Current Positions:")
                    for symbol, position in self.portfolio['positions'].items():
                        print(f"    {symbol}: {position['shares']:,} shares @ ${position['cost_basis']:.2f}")
                else:
                    print("\n  No open positions")
                print("\n" + "="*50)
            
            # Calculate comprehensive metrics
            # self._calculate_metrics() # Removed as per edit hint
            
        except Exception as e:
            print(f"\n❌ Error during backtest: {str(e)}")
            self.error_handler.handle(e)

    def _calculate_final_metrics(self):
        """Calculate comprehensive portfolio performance metrics."""
        initial_value = 1000000  # Starting cash
        final_value = self._calculate_portfolio_value()  # Use cost basis for final calculation
        
        print("\n🏁 Backtest Complete!")
        print("=" * 50)
        print(f"Initial Value: ${initial_value:,.2f}")
        print(f"Final Value: ${final_value:,.2f}")
        
        # S1.2.1. Cumulative Return (CR)
        cumulative_return = ((final_value - initial_value) / initial_value) * 100
        print(f"Cumulative Return: {cumulative_return:.2f}%")
        
        # S1.2.2. Annualized Return (AR)
        days = len(self.daily_portfolio_values)
        years = days / 365.25
        annualized_return = (((final_value / initial_value) ** (1 / years)) - 1) * 100
        print(f"Annualized Return: {annualized_return:.2f}%")
        
        # Calculate daily returns for risk metrics
        portfolio_values = [pv['portfolio_value'] for pv in self.daily_portfolio_values]
        daily_returns = []
        for i in range(1, len(portfolio_values)):
            daily_return = (portfolio_values[i] - portfolio_values[i-1]) / portfolio_values[i-1]
            daily_returns.append(daily_return)
        
        if daily_returns:
            # S1.2.3. Sharpe Ratio (SR)
            risk_free_rate = 0.05  # 5% annual risk-free rate
            daily_risk_free = risk_free_rate / 365.25
            excess_returns = [r - daily_risk_free for r in daily_returns]
            
            if np.std(daily_returns) > 0:
                sharpe_ratio = np.mean(excess_returns) / np.std(daily_returns) * np.sqrt(365.25)
                print(f"Sharpe Ratio: {sharpe_ratio:.2f}")
            else:
                print("Sharpe Ratio: N/A (no volatility)")
            
            # S1.2.4. Maximum Drawdown (MDD)
            running_max = np.maximum.accumulate(portfolio_values)
            drawdowns = (np.array(portfolio_values) - running_max) / running_max
            max_drawdown = np.min(drawdowns) * 100
            print(f"Maximum Drawdown: {max_drawdown:.2f}%")
            
            # Additional metrics
            volatility = np.std(daily_returns) * np.sqrt(365.25) * 100
            print(f"Volatility: {volatility:.2f}%")
        
        # Trading metrics
        total_trades = len(self.portfolio['history'])
        print(f"Total Trades: {total_trades}")
        
        if self.portfolio['positions']:
            print("\nFinal Positions:")
            for symbol, position in self.portfolio['positions'].items():
                print(f"  {symbol}: {position['shares']:,} shares @ ${position['cost_basis']:.2f}")
        
        # Save comprehensive results
        results = {
            'initial_value': initial_value,
            'final_value': final_value,
            'cumulative_return': cumulative_return,
            'annualized_return': annualized_return,
            'sharpe_ratio': sharpe_ratio if daily_returns and np.std(daily_returns) > 0 else None,
            'max_drawdown': max_drawdown if daily_returns else None,
            'volatility': volatility if daily_returns else None,
            'total_trades': total_trades,
            'daily_portfolio_values': self.daily_portfolio_values,
            'transaction_history': self.portfolio['history'],
            'final_positions': self.portfolio['positions'],
            'cash_balance': self.portfolio['cash']
        }
        
        results_file = os.path.join(self.data_dir, 'backtest_results.json')
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to {results_file}")
        print("=" * 50)

def main():
    """Run backtest with all stocks"""
    import argparse
    
    # List of all stocks to process
    STOCKS = [
        # Technology
        "GOOGL", "NVDA", "PLTR",
        # Health and Pharma
        "ABBV", "TMO", "UNH",
        # Financial Services
        "JPM", "BAC", "WFC",
        # Energy
        "XOM", "CVX", "COP"
    ]
    
    parser = argparse.ArgumentParser(description="Run stock analysis backtest")
    parser.add_argument("--data-dir", default="/home/ubuntu", help="Base directory for data")
    parser.add_argument("--start-date", default="2025-06-12", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", default="2025-06-15", help="End date (YYYY-MM-DD)")
    args = parser.parse_args()
    
    # Initialize and run orchestrator
    orchestrator = BacktestOrchestrator(data_dir=args.data_dir)
    orchestrator.run_workflow(STOCKS, start_date=args.start_date, end_date=args.end_date)

if __name__ == "__main__":
    main()
