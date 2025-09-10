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

# Load environment variables from .env file
load_dotenv()

from ValuationAgent import ValuationAgent
from FundamentalAgent import FundamentalAgent
from SentimentAgent import SentimentAgent
from ReasoningAgent import ReasoningAgent

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
        # Use a 90-day period
        self.start_date = pd.Timestamp("2025-06-01")
        self.end_date = pd.Timestamp("2025-08-29")  # ~90 days from June 1st
        self.trading_days_only = trading_days_only
        
        if trading_days_only:
            # Get NYSE calendar
            nyse = mcal.get_calendar('NYSE')
            self.trading_days = nyse.valid_days(
                start_date=self.start_date,
                end_date=self.end_date
            )
            # Use all trading days in the 90-day period
            self.trading_days = self.trading_days[:]
    
    def __iter__(self) -> Iterator[pd.Timestamp]:
        """Yield dates in range."""
        if self.trading_days_only:
            yield from self.trading_days
        else:
            current = self.start_date
            while current <= self.end_date:
                yield current
                current += timedelta(days=1)

class CloudWatchLogger:
    """Handles logging to AWS CloudWatch."""
    
    def __init__(self, log_group: str = "/stock-agent/backtest"):
        """
        Initialize CloudWatch logger.
        
        Args:
            log_group: CloudWatch log group name
        """
        self.client = boto3.client('cloudwatch')
        self.logs_client = boto3.client('logs')
        self.log_group = log_group
        self.log_stream = datetime.now().strftime("%Y/%m/%d")
        
        # Ensure log group exists
        try:
            self.logs_client.create_log_group(logGroupName=log_group)
        except self.logs_client.exceptions.ResourceAlreadyExistsException:
            pass
            
        # Ensure log stream exists
        try:
            self.logs_client.create_log_stream(
                logGroupName=self.log_group,
                logStreamName=self.log_stream
            )
        except self.logs_client.exceptions.ResourceAlreadyExistsException:
            pass
    
    def info(self, message: str):
        """Log info message."""
        self._log("INFO", message)
    
    def error(self, message: str):
        """Log error message."""
        self._log("ERROR", message)
    
    def _log(self, level: str, message: str):
        """Internal logging method."""
        timestamp = int(datetime.now().timestamp() * 1000)
        try:
            # Get the sequence token for the stream
            try:
                response = self.logs_client.describe_log_streams(
                    logGroupName=self.log_group,
                    logStreamNamePrefix=self.log_stream
                )
                sequence_token = response['logStreams'][0].get('uploadSequenceToken')
            except (IndexError, KeyError):
                sequence_token = None
            
            # Put log events
            kwargs = {
                'logGroupName': self.log_group,
                'logStreamName': self.log_stream,
                'logEvents': [{
                    'timestamp': timestamp,
                    'message': f"[{level}] {message}"
                }]
            }
            if sequence_token:
                kwargs['sequenceToken'] = sequence_token
                
            self.logs_client.put_log_events(**kwargs)
            
        except Exception as e:
            print(f"Failed to log to CloudWatch: {str(e)}")
    
    def log_metrics(self, metrics_data: Dict[str, Any]):
        """Send metrics to CloudWatch."""
        try:
            metric_data = []
            for name, value in metrics_data.items():
                metric_data.append({
                    'MetricName': name,
                    'Value': value,
                    'Unit': 'None',
                    'Timestamp': datetime.now()
                })
            
            self.client.put_metric_data(
                Namespace='StockAgent/Backtest',
                MetricData=metric_data
            )
        except Exception as e:
            print(f"Failed to log metrics to CloudWatch: {str(e)}")

class ErrorHandler:
    """Handles errors during backtesting."""
    
    def __init__(self, logger: Optional[CloudWatchLogger] = None):
        """
        Initialize error handler.
        
        Args:
            logger: CloudWatch logger instance
        """
        self.logger = logger or CloudWatchLogger()
        self.sns = boto3.client('sns')
        self.topic_arn = os.getenv('SNS_TOPIC_ARN')
    
    def handle(self, error: Exception):
        """
        Handle an error.
        
        Args:
            error: The exception to handle
        """
        error_msg = str(error)
        self.logger.error(error_msg)
        
        if self.should_retry(error):
            return True  # Indicate retry is possible
        
        if self.topic_arn:
            try:
                self.sns.publish(
                    TopicArn=self.topic_arn,
                    Message=f"Backtest Error: {error_msg}",
                    Subject="Stock Agent Backtest Error"
                )
            except Exception as e:
                print(f"Failed to send SNS notification: {str(e)}")
        
        return False  # Indicate no retry
    
    def should_retry(self, error: Exception) -> bool:
        """
        Determine if error is retryable.
        
        Args:
            error: The exception to check
        
        Returns:
            True if error should be retried
        """
        # Add retry logic based on error types
        retryable_errors = (
            TimeoutError,
            ConnectionError,
            # Add other retryable errors
        )
        return isinstance(error, retryable_errors)

class MetricsTracker:
    """Tracks metrics during backtesting."""
    
    def __init__(self, logger: Optional[CloudWatchLogger] = None):
        """
        Initialize metrics tracker.
        
        Args:
            logger: CloudWatch logger instance
        """
        self.logger = logger or CloudWatchLogger()
        self.metrics = {
            'decisions_made': 0,
            'successful_runs': 0,
            'errors': 0,
            'avg_confidence': 0.0,
            'processing_time': 0.0
        }
    
    def update(self, decision_data: Dict[str, Any]):
        """
        Update metrics with new decision data.
        
        Args:
            decision_data: Decision data from ReasoningAgent
        """
        self.metrics['decisions_made'] += 1
        self.metrics['avg_confidence'] = (
            (self.metrics['avg_confidence'] * (self.metrics['decisions_made'] - 1) +
             decision_data.get('confidence', 0)) / self.metrics['decisions_made']
        )
        
        # Log metrics to CloudWatch
        self.logger.log_metrics(self.metrics)

class HistoricalContext:
    """Manages historical data and previous decisions."""
    
    def __init__(self, lookback_days: int = 90):  # Changed from 10 to 90 for full testing
        """
        Initialize historical context manager.
        
        Args:
            lookback_days: Number of days of historical data to maintain
        """
        self.lookback_days = lookback_days
        self.decisions_history: List[Dict] = []
        self.max_decisions_to_keep = 30  # Changed from 10 to 30 for proper history tracking
    
    def _get_historical_valuation(self, symbol: str, start_date: pd.Timestamp, end_date: pd.Timestamp) -> Dict:
        """Get historical price data (open prices only)."""
        try:
            # Use ValuationAgent to get historical data
            agent = ValuationAgent()
            historical_data = []
            
            current_date = start_date
            while current_date <= end_date:
                if current_date.weekday() < 5:  # Only weekdays
                    try:
                        data = agent.analyze_valuation(symbol, date=current_date)
                        if data:
                            # Only keep relevant morning data
                            morning_data = {
                                'date': current_date.strftime('%Y-%m-%d'),
                                'open_price': data.get('current_price', 0),
                                'volume': data.get('volume_analysis', {}).get('current_volume', 0),
                                'beta': data.get('volatility', {}).get('beta', 0)
                            }
                            historical_data.append(morning_data)
                    except Exception as e:
                        print(f"Error getting valuation data for {current_date}: {str(e)}")
                current_date += pd.Timedelta(days=1)
            
            return {'price_history': historical_data}
            
        except Exception as e:
            print(f"Error in historical valuation: {str(e)}")
            return {'price_history': []}
    
    def _get_historical_fundamental(self, symbol: str, start_date: pd.Timestamp, end_date: pd.Timestamp) -> Dict:
        """Get historical fundamental data."""
        try:
            # Use FundamentalAgent to get data
            agent = FundamentalAgent()
            # For fundamentals, we only need the most recent data before start_date
            data = agent.analyze_fundamentals(symbol)
            
            if data:
                return {
                    'metrics': {
                        'pe_ratio': data.get('fundamental_analysis', {}).get('valuation_metrics', {}).get('metrics', {}).get('pe_ratio', 0),
                        'market_cap': data.get('fundamental_analysis', {}).get('valuation_metrics', {}).get('metrics', {}).get('market_cap', 0),
                        'revenue': data.get('fundamental_analysis', {}).get('profitability', {}).get('metrics', {}).get('revenue', 0),
                        'net_income': data.get('fundamental_analysis', {}).get('profitability', {}).get('metrics', {}).get('net_income', 0)
                    }
                }
            return {'metrics': {}}
            
        except Exception as e:
            print(f"Error in historical fundamental: {str(e)}")
            return {'metrics': {}}
    
    def _get_historical_sentiment(self, symbol: str, start_date: pd.Timestamp, end_date: pd.Timestamp) -> Dict:
        """Get historical sentiment data."""
        try:
            # Use SentimentAgent to get historical sentiment
            agent = SentimentAgent()
            sentiment_data = []
            
            current_date = start_date
            while current_date <= end_date:
                if current_date.weekday() < 5:  # Only weekdays
                    try:
                        data = agent.analyze_sentiment(symbol, date=current_date)
                        if data:
                            sentiment_data.append({
                                'date': current_date.strftime('%Y-%m-%d'),
                                'decision': data.get('current_analysis', {}).get('decision', 'HOLD'),
                                'confidence': data.get('current_analysis', {}).get('confidence', 0),
                                'news_count': len(data.get('news_data', {}).get('news', []))
                            })
                    except Exception as e:
                        print(f"Error getting sentiment data for {current_date}: {str(e)}")
                current_date += pd.Timedelta(days=1)
            
            return {'sentiment_history': sentiment_data}
            
        except Exception as e:
            print(f"Error in historical sentiment: {str(e)}")
            return {'sentiment_history': []}
    
    def _calculate_accuracy(self, decisions: List[Dict]) -> float:
        """
        Calculate decision accuracy based on next day's price movement.
        
        Args:
            decisions: List of historical decisions
            
        Returns:
            Accuracy as a percentage
        """
        if not decisions:
            return 0.0
            
        correct = 0
        total = 0
        
        for i, decision in enumerate(decisions[:-1]):  # Skip last decision as we don't have next day's data
            try:
                current_price = decision.get('price_context', {}).get('open_price', 0)
                next_price = decisions[i+1].get('price_context', {}).get('open_price', 0)
                
                if current_price and next_price:
                    price_change = (next_price - current_price) / current_price
                    
                    # Check if decision was correct
                    if (decision['decision'] == 'BUY' and price_change > 0) or \
                       (decision['decision'] == 'SELL' and price_change < 0) or \
                       (decision['decision'] == 'HOLD' and abs(price_change) < 0.01):  # 1% threshold for HOLD
                        correct += 1
                    total += 1
                    
            except Exception as e:
                print(f"Error calculating accuracy for decision: {str(e)}")
                continue
                
        return (correct / total * 100) if total > 0 else 0.0
    
    def _get_decision_distribution(self, decisions: List[Dict]) -> Dict:
        """Get distribution of decisions (BUY/SELL/HOLD)."""
        distribution = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        for decision in decisions:
            decision_type = decision.get('decision', 'HOLD')
            distribution[decision_type] += 1
        return distribution

class BacktestOrchestrator:
    """Main orchestrator for backtesting workflow."""
    
    def __init__(self, data_dir: str = "."):
        self.logger = CloudWatchLogger()
        self.error_handler = ErrorHandler(self.logger)
        self.metrics = MetricsTracker(self.logger)
        self.historical_context = HistoricalContext()
        
        # Initialize agents
        self.valuation_agent = ValuationAgent(data_dir=data_dir)
        self.fundamental_agent = FundamentalAgent(data_dir=data_dir)
        self.sentiment_agent = SentimentAgent(data_dir=data_dir)
        self.reasoning_agent = ReasoningAgent(data_dir=data_dir)
        
        # Track portfolio performance
        self.portfolio = {
            'cash': 1000000,  # Start with $1M
            'positions': {},  # {symbol: {'shares': n, 'cost_basis': price}}
            'history': []     # List of trades and daily values
        }
    
    def run_with_retry(self, agent: Any, date: pd.Timestamp, max_retries: int = 3, context: Optional[Dict] = None) -> Optional[Dict]:
        """
        Run agent analysis with retry logic.
        
        Args:
            agent: Agent instance to run
            date: Date to analyze
            max_retries: Maximum number of retry attempts
            context: Context to pass to the agent (e.g., historical data)
        
        Returns:
            Analysis results or None if all retries fail
        """
        retries = 0
        while retries < max_retries:
            try:
                if isinstance(agent, ReasoningAgent):
                    # For ReasoningAgent, make a decision using all analyses
                    return agent.make_decision(
                        symbol=context['valuation_analysis']['symbol'],
                        analyses=context
                    )
                elif isinstance(agent, ValuationAgent):
                    return agent.prepare_analysis_data(symbol)
                elif isinstance(agent, FundamentalAgent):
                    return agent.prepare_fundamental_analysis(symbol)
                elif isinstance(agent, SentimentAgent):
                    return agent.analyze_sentiment(symbol)
            except Exception as e:
                retries += 1
                if not self.error_handler.should_retry(e) or retries >= max_retries:
                    self.error_handler.handle(e)
                    return None
                self.logger.info(f"Retry {retries} of {max_retries}")
        return None
    
    def store_results(self, date: pd.Timestamp, decision: Dict[str, Any]):
        """
        Store backtest results.
        
        Args:
            date: Date of decision
            decision: Decision data from ReasoningAgent
        """
        # Store to S3
        s3 = boto3.client('s3')
        bucket = os.getenv('RESULTS_BUCKET')
        if bucket:
            try:
                key = f"backtest_results/{date.strftime('%Y/%m/%d')}/decision.json"
                s3.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=json.dumps(decision)
                )
            except Exception as e:
                self.logger.error(f"Failed to store results to S3: {str(e)}")
    
    def _get_morning_data(self, symbol: str, date: pd.Timestamp) -> Dict:
        """
        Get morning data for given date (opening prices only).
        
        Args:
            symbol: Stock symbol
            date: Date to get data for
            
        Returns:
            Dictionary containing morning data
        """
        try:
            # Load the latest analyses that were available before this date
            valuation_file = self._get_latest_analysis_before_date(
                symbol, 'valuation_reports', date
            )
            fundamental_file = self._get_latest_analysis_before_date(
                symbol, 'fundamental_reports', date
            )
            sentiment_file = self._get_latest_analysis_before_date(
                symbol, 'sentiment_data', date
            )
            
            if not all([valuation_file, fundamental_file, sentiment_file]):
                print("  Missing required analysis files")
                return {}
            
            # Load the analysis files
            with open(valuation_file, 'r') as f:
                valuation_data = json.load(f)
            with open(fundamental_file, 'r') as f:
                fundamental_data = json.load(f)
            with open(sentiment_file, 'r') as f:
                sentiment_data = json.load(f)
            
            # Extract only morning/opening data
            morning_data = {
                'date': date.strftime('%Y-%m-%d'),
                'price_data': {
                    'open_price': valuation_data.get('current_price', 0),
                    'volume': valuation_data.get('volume_analysis', {}).get('current_volume', 0),
                    'beta': valuation_data.get('volatility', {}).get('beta', 0)
                },
                'fundamental_data': {
                    'pe_ratio': fundamental_data.get('fundamental_analysis', {}).get('valuation_metrics', {}).get('metrics', {}).get('pe_ratio', 0),
                    'market_cap': fundamental_data.get('fundamental_analysis', {}).get('valuation_metrics', {}).get('metrics', {}).get('market_cap', 0)
                },
                'sentiment_data': {
                    'news_count': len(sentiment_data.get('news_data', {}).get('news', [])),
                    'morning_sentiment': sentiment_data.get('current_analysis', {}).get('decision', 'HOLD')
                }
            }
            
            return morning_data
            
        except Exception as e:
            print(f"  Error getting morning data: {str(e)}")
            return {}
    
    def _get_latest_analysis_before_date(self, symbol: str, directory: str, date: pd.Timestamp) -> Optional[str]:
        """Get the latest analysis file before the given date."""
        try:
            files = []
            for file in os.listdir(directory):
                if file.startswith(f"{symbol}_") and file.endswith('.json'):
                    file_date = pd.Timestamp(file.split('_')[-1].replace('.json', ''))
                    if file_date < date:
                        files.append((file_date, os.path.join(directory, file)))
            
            if not files:
                return None
                
            # Get the latest file before the date
            latest_file = max(files, key=lambda x: x[0])[1]
            return latest_file
            
        except Exception as e:
            print(f"Error finding analysis file: {str(e)}")
            return None
    
    def _update_portfolio(self, symbol: str, decision: Dict, valuation_data: Dict):
        """Update portfolio based on trading decision."""
        try:
            # Get current price directly from valuation data
            current_price = valuation_data.get('current_price', 0)
            if not current_price:
                print(f"  ⚠️  No price available for trade execution")
                return
                
            action = decision['decision']
            confidence = decision['confidence']
            
            print(f"\n  Trade Analysis for {symbol}:")
            print(f"  - Decision: {action}")
            print(f"  - Confidence: {confidence}%")
            print(f"  - Current Price: ${current_price:.2f}")
            
            # Only trade if confidence is high enough
            if confidence < 60:
                print("  ⚠️  Confidence too low for trade execution")
                return
            
            shares = 0
            if action == 'BUY':
                # Calculate position size based on confidence
                position_size = (confidence / 100) * (self.portfolio['cash'] * 0.1)  # Max 10% of cash per trade
                shares = int(position_size / current_price)
                
                if shares > 0:
                    cost = shares * current_price
                    if cost <= self.portfolio['cash']:
                        print(f"\n  🔵 EXECUTING BUY ORDER:")
                        print(f"  - Shares: {shares:,}")
                        print(f"  - Price: ${current_price:.2f}")
                        print(f"  - Total Cost: ${cost:,.2f}")
                        
                        self.portfolio['cash'] -= cost
                        if symbol not in self.portfolio['positions']:
                            self.portfolio['positions'][symbol] = {'shares': 0, 'cost_basis': 0}
                        
                        # Update position
                        total_cost = (self.portfolio['positions'][symbol]['shares'] * 
                                    self.portfolio['positions'][symbol]['cost_basis'] + cost)
                        total_shares = self.portfolio['positions'][symbol]['shares'] + shares
                        self.portfolio['positions'][symbol] = {
                            'shares': total_shares,
                            'cost_basis': total_cost / total_shares
                        }
                        
                        print(f"\n  Position Update:")
                        print(f"  - Total Shares: {total_shares:,}")
                        print(f"  - Average Cost: ${self.portfolio['positions'][symbol]['cost_basis']:.2f}")
                        
            elif action == 'SELL':
                if symbol in self.portfolio['positions'] and self.portfolio['positions'][symbol]['shares'] > 0:
                    shares = self.portfolio['positions'][symbol]['shares']
                    proceeds = shares * current_price
                    cost_basis = self.portfolio['positions'][symbol]['cost_basis']
                    profit_loss = proceeds - (shares * cost_basis)
                    
                    print(f"\n  🔴 EXECUTING SELL ORDER:")
                    print(f"  - Shares: {shares:,}")
                    print(f"  - Price: ${current_price:.2f}")
                    print(f"  - Total Proceeds: ${proceeds:,.2f}")
                    print(f"  - Profit/Loss: ${profit_loss:,.2f} ({(profit_loss/proceeds)*100:.1f}%)")
                    
                    self.portfolio['cash'] += proceeds
                    del self.portfolio['positions'][symbol]
            
            # Record the trade
            if shares != 0:  # Only log if we actually executed a trade
                trade = {
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'symbol': symbol,
                    'action': action,
                    'shares': shares if action == 'BUY' else -shares,
                    'execution_price': current_price,
                    'confidence': confidence,
                    'cost_or_proceeds': -shares * current_price if action == 'BUY' else shares * current_price,
                    'cash_after_trade': self.portfolio['cash'],
                    'positions_after_trade': self.portfolio['positions'].copy(),
                    'reasoning': decision.get('reasoning', 'No reasoning provided')
                }
                
                self.portfolio['history'].append(trade)
                
                # Save trade to daily summary
                self._update_daily_summary(trade)
                
                print(f"\n  💰 Portfolio Update:")
                print(f"  - Cash Balance: ${self.portfolio['cash']:,.2f}")
                print(f"  - Number of Positions: {len(self.portfolio['positions'])}")
            
        except Exception as e:
            print(f"  ❌ Error updating portfolio: {str(e)}")
            return

    def _update_daily_summary(self, trade: Dict):
        """Update the daily trading summary."""
        try:
            summary_file = f"trading_summary_{trade['date']}.json"
            
            # Load existing summary or create new one
            if os.path.exists(summary_file):
                with open(summary_file, 'r') as f:
                    summary = json.load(f)
            else:
                summary = {
                    'date': trade['date'],
                    'trades': [],
                    'portfolio_value': self.portfolio['cash'],
                    'cash_balance': self.portfolio['cash'],
                    'number_of_positions': len(self.portfolio['positions']),
                    'positions': self.portfolio['positions'].copy()
                }
            
            # Add new trade
            summary['trades'].append({
                'time': datetime.now().strftime('%H:%M:%S'),
                'symbol': trade['symbol'],
                'action': trade['action'],
                'shares': trade['shares'],
                'price': trade['execution_price'],
                'value': abs(trade['cost_or_proceeds']),
                'confidence': trade['confidence']
            })
            
            # Update summary
            total_value = self.portfolio['cash']
            for symbol, position in self.portfolio['positions'].items():
                # Use the last known price for the position
                total_value += position['shares'] * position['cost_basis']
            
            summary['portfolio_value'] = total_value
            summary['cash_balance'] = self.portfolio['cash']
            summary['number_of_positions'] = len(self.portfolio['positions'])
            summary['positions'] = self.portfolio['positions'].copy()
            
            # Save updated summary
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
                
        except Exception as e:
            print(f"  ⚠️  Error updating daily summary: {str(e)}")

    def run_workflow(self, symbols: List[str]):
        """Run complete backtest workflow."""
        try:
            print(f"\nStarting backtest from 2025-06-01 to 2025-08-29 (90-day period)")
            print(f"Tracking {len(symbols)} symbols: {', '.join(symbols)}")
            print("\nInitial Portfolio:")
            print(f"💰 Cash: ${self.portfolio['cash']:,.2f}")
            print("📊 Positions: None")
            print("\n" + "="*50)
            
            self.logger.info(f"Starting backtest for {len(symbols)} symbols")
            
            for date in DateRangeIterator("2025-06-01", "2025-08-29"):
                print(f"\n📅 Trading Day: {date.strftime('%Y-%m-%d')}")
                print("="*50)
                daily_decisions = []
                
                for symbol in symbols:
                    print(f"\n📈 Analyzing {symbol}:")
                    
                    # Run fresh analyses for this day
                    print("  - Running valuation analysis...")
                    valuation = self.valuation_agent.prepare_analysis_data(symbol)
                    if valuation:
                        self.valuation_agent.save_analysis(symbol, valuation)
                        print("    ✓ Valuation complete")
                    
                    print("  - Running fundamental analysis...")
                    fundamental = self.fundamental_agent.prepare_fundamental_analysis(symbol)
                    if fundamental:
                        self.fundamental_agent.save_analysis(symbol, fundamental)
                        print("    ✓ Fundamental complete")
                    
                    print("  - Running sentiment analysis...")
                    sentiment = self.sentiment_agent.analyze_sentiment(symbol)
                    if sentiment:
                        print("    ✓ Sentiment complete")
                    
                    # Only proceed if we have all analyses
                    if all([valuation, fundamental, sentiment]):
                        print("  - Getting final decision...")
                        
                        # Prepare context with all analyses
                        context = {
                            'valuation_analysis': valuation,
                            'fundamental_analysis': fundamental,
                            'sentiment_analysis': sentiment,
                            'date': date.strftime('%Y-%m-%d')
                        }
                        
                        # Get final decision from ReasoningAgent
                        decision = self.run_with_retry(
                            self.reasoning_agent,
                            date,
                            context=context
                        )
                        
                        if decision:
                            daily_decisions.append((symbol, decision))
                            self._update_portfolio(symbol, decision, valuation)
                        else:
                            print("    ⚠️  No decision made")
                    else:
                        print("    ⚠️  Missing required analyses")
                
                # Print end of day summary
                print("\n📊 End of Day Summary:")
                print(f"  Portfolio Value: ${self._calculate_portfolio_value():,.2f}")
                print(f"  Cash Balance: ${self.portfolio['cash']:,.2f}")
                if self.portfolio['positions']:
                    print("\n  Current Positions:")
                    for symbol, position in self.portfolio['positions'].items():
                        print(f"    {symbol}: {position['shares']:,} shares @ ${position['cost_basis']:.2f}")
                else:
                    print("\n  No open positions")
                print("\n" + "="*50)
            
            # Calculate final statistics
            initial_value = 1000000  # Starting cash
            final_value = self._calculate_portfolio_value()
            total_return = (final_value - initial_value) / initial_value * 100
            
            print("\n🏁 Backtest Complete!")
            print("=" * 50)
            print(f"Initial Value: ${initial_value:,.2f}")
            print(f"Final Value: ${final_value:,.2f}")
            print(f"Total Return: {total_return:.1f}%")
            
            if self.portfolio['positions']:
                print("\nFinal Positions:")
                for symbol, position in self.portfolio['positions'].items():
                    print(f"  {symbol}: {position['shares']:,} shares @ ${position['cost_basis']:.2f}")
            
            # Save results
            results = {
                'initial_value': initial_value,
                'final_value': final_value,
                'total_return': total_return,
                'history': self.portfolio['history'],
                'final_positions': self.portfolio['positions'],
                'cash_balance': self.portfolio['cash']
            }
            
            with open('backtest_results.json', 'w') as f:
                json.dump(results, f, indent=2)
            
            print("\nResults saved to backtest_results.json")
            
        except Exception as e:
            print(f"\n❌ Error during backtest: {str(e)}")
            self.error_handler.handle(e)
            
    def _calculate_portfolio_value(self) -> float:
        """Calculate total portfolio value including positions."""
        total_value = self.portfolio['cash']
        for symbol, position in self.portfolio['positions'].items():
            total_value += position['shares'] * position['cost_basis']
        return total_value

def main():
    """Run backtest for all tracked stocks."""
    import argparse
    
    # List of stocks to track
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
    parser.add_argument("--data-dir", default=".", help="Base directory for data")
    args = parser.parse_args()
    
    orchestrator = BacktestOrchestrator(data_dir="backtest_data_90days")
    orchestrator.run_workflow(STOCKS)

if __name__ == "__main__":
    main() 