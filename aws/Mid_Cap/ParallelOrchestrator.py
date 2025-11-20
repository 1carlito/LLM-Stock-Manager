#!/usr/bin/env python3
"""
Parallel Orchestrator - Runs stock analysis in parallel with separate API keys
and uses Portfolio Manager for final allocation decisions.
"""

import os
import sys
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import glob
import pandas_market_calendars as mcal
import logging
from collections import defaultdict
from typing import List, Dict, Any

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from ReasoningAgent import ReasoningAgent
from SentimentAgent import SentimentAgent
from ValuationAgent import ValuationAgent
from FundamentalAgent import FundamentalAgent
from PortfolioManagerAgent import PortfolioManagerAgent


class ParallelBacktest:
    """
    Run a backtest with parallel stock analysis and portfolio-level decision making.
    Each stock gets its own API key to avoid rate limiting.
    """
    
    def __init__(self, data_dir='.', start_date=None, end_date=None, lookback_window=4,
                 use_sentiment=True, use_valuation=True, use_fundamental=True,
                 backtest_name="parallel", api_keys=None, max_workers=None):
        self.data_dir = data_dir
        self.start_date = start_date
        self.end_date = end_date
        self.lookback_window = lookback_window
        self.use_sentiment = use_sentiment
        self.use_valuation = use_valuation
        self.use_fundamental = use_fundamental
        self.backtest_name = backtest_name
        
        # API key configuration
        self.api_keys = api_keys or self._load_api_keys()
        self.max_workers = max_workers or min(len(self.api_keys), 10)
        
        # Set up logging
        log_dir = os.path.join(data_dir, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(log_dir, f'parallel_backtest_{backtest_name}.log')),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize portfolio
        self.portfolio = {
            'cash': 1000000,  # $1M starting cash
            'positions': {},
            'last_prices': {},
            'theoretical_trades': []
        }
        
        # Track previous decisions for each symbol
        self.previous_decisions = defaultdict(list)
        
        # Initialize Portfolio Manager (uses separate API key)
        self.portfolio_manager = PortfolioManagerAgent(data_dir=data_dir)
        
        # Initialize shared analysis agents (sentiment, valuation, fundamental)
        # These are shared across all stocks since they don't have rate limits typically
        if use_sentiment:
            self.sentiment_agent = SentimentAgent(data_dir=data_dir)
            self.logger.info("Sentiment Agent initialized")
        else:
            self.sentiment_agent = None
            
        if use_valuation:
            self.valuation_agent = ValuationAgent(data_dir=data_dir)
            self.logger.info("Valuation Agent initialized")
        else:
            self.valuation_agent = None
            
        if use_fundamental:
            self.fundamental_agent = FundamentalAgent(data_dir=data_dir)
            self.logger.info("Fundamental Agent initialized")
        else:
            self.fundamental_agent = None
        
        # Log configuration
        agent_config = []
        if use_sentiment: agent_config.append("Sentiment")
        if use_valuation: agent_config.append("Valuation")
        if use_fundamental: agent_config.append("Fundamental")
        
        self.logger.info(f"Parallel Backtest initialized:")
        self.logger.info(f"- Date range: {start_date} to {end_date}")
        self.logger.info(f"- Data directory: {data_dir}")
        self.logger.info(f"- Claude API keys available: {len(self.api_keys)}")
        self.logger.info(f"- Max parallel workers: {self.max_workers}")
        self.logger.info(f"- Lookback window: {lookback_window} days")
        self.logger.info(f"- Agent configuration: {' + '.join(agent_config)}")
    
    def _load_api_keys(self):
        """Load API keys from environment variables for ReasoningAgent (Claude API keys)"""
        from dotenv import load_dotenv
        load_dotenv()
        
        keys = []
        
        # Try to load numbered Claude API keys (STOCK_*_CLAUDE_API_KEY)
        for i in range(1, 7):  # Support up to 6 API keys
            key = os.getenv(f"STOCK_{i}_CLAUDE_API_KEY")
            if key:
                keys.append(key)
        
        # If still no keys, try the default Claude API key
        if not keys:
            default_key = os.getenv("ANTHROPIC_API_KEY")
            if default_key:
                keys.append(default_key)
        
        if not keys:
            raise ValueError("No Claude API keys found. Set STOCK_1_CLAUDE_API_KEY through STOCK_6_CLAUDE_API_KEY in .env")
        
        # Note: Logger not available yet during initialization, will log later
        print(f"Loaded {len(keys)} Claude API key(s) for ReasoningAgent")
        return keys
    
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
                            continue
                    
                    # Include file if its analysis date is before or on the current date
                    if date_obj.date() <= current_date_obj.date():
                        valid_files.append((file, date_obj, data))
                except Exception:
                    continue
                    
            except Exception:
                continue
        
        if not valid_files:
            return None
            
        # Get the file with the most recent analysis_date that's still <= current_date
        latest_valid = max(valid_files, key=lambda x: x[1])
        return latest_valid[2]
    
    def _load_previous_decisions(self, symbol, current_date):
        """Load previous decisions for a symbol up to the current date"""
        try:
            decisions_dir = os.path.join(self.data_dir, 'reasoning_decisions_Claude')
            if not os.path.exists(decisions_dir):
                return []
            
            # Find all decision files for this symbol and backtest
            pattern = os.path.join(decisions_dir, f"{symbol}_decision_*_{self.backtest_name}.json")
            files = glob.glob(pattern)
            
            if not files:
                # Fall back to any decisions for this symbol
                pattern = os.path.join(decisions_dir, f"{symbol}_decision_*.json")
                files = glob.glob(pattern)
                
            if not files:
                return []
            
            current_date_obj = datetime.strptime(current_date, '%Y-%m-%d')
            previous_decisions = []
            
            # Load decisions from files
            for file in files:
                try:
                    with open(file, 'r') as f:
                        decision = json.load(f)
                    
                    # Check if decision is before current date
                    decision_date = datetime.strptime(decision['date'], '%Y-%m-%d')
                    if decision_date < current_date_obj:
                        previous_decisions.append(decision)
                        
                except Exception:
                    continue
            
            # Sort by date and return the most recent ones (up to lookback_window)
            previous_decisions.sort(key=lambda x: x['date'])
            return previous_decisions[-self.lookback_window:]
            
        except Exception as e:
            self.logger.error(f"Error loading previous decisions for {symbol}: {e}")
            return []
    
    def _load_previous_portfolio_decisions(self, current_date):
        """Load previous portfolio allocation decisions (up to 4) before current date"""
        try:
            decisions_dir = os.path.join(self.data_dir, 'portfolio_decisions_Claude')
            if not os.path.exists(decisions_dir):
                return []
            
            # Find all portfolio decision files for this backtest
            pattern = os.path.join(decisions_dir, f"portfolio_decision_*_{self.backtest_name}.json")
            files = glob.glob(pattern)
            
            if not files:
                # Fall back to any portfolio decisions
                pattern = os.path.join(decisions_dir, f"portfolio_decision_*.json")
                files = glob.glob(pattern)
                
            if not files:
                return []
            
            current_date_obj = datetime.strptime(current_date, '%Y-%m-%d')
            previous_portfolio_decisions = []
            
            # Load decisions from files
            for file in files:
                try:
                    with open(file, 'r') as f:
                        decision = json.load(f)
                    
                    # Skip decisions without a date field
                    decision_date_str = decision.get('date')
                    if not decision_date_str:
                        continue
                    
                    # Check if decision is before current date
                    try:
                        decision_date = datetime.strptime(decision_date_str, '%Y-%m-%d')
                        if decision_date < current_date_obj:
                            previous_portfolio_decisions.append(decision)
                    except ValueError:
                        # Skip if date format is invalid
                        continue
                        
                except Exception:
                    continue
            
            # Sort by date and return the most recent ones (up to 4)
            # Only sort decisions that have valid dates
            previous_portfolio_decisions.sort(key=lambda x: x.get('date', ''))
            return previous_portfolio_decisions[-4:]
            
        except Exception as e:
            self.logger.error(f"Error loading previous portfolio decisions: {e}")
            return []

    def _save_portfolio_decision(self, portfolio_decisions, current_date):
        """Save portfolio decision record to file for future context"""
        try:
            decisions_dir = os.path.join(self.data_dir, 'portfolio_decisions_Claude')
            os.makedirs(decisions_dir, exist_ok=True)
            
            # Create filename with date and backtest name
            filename = f"portfolio_decision_{current_date}_{self.backtest_name}.json"
            filepath = os.path.join(decisions_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(portfolio_decisions, f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(f"Error saving portfolio decision: {e}")
    
    def _analyze_single_stock(self, symbol, current_date, api_key):
        """
        Analyze a single stock and make a decision using the assigned API key.
        This function is designed to run in parallel.
        """
        try:
            self.logger.info(f"[{symbol}] Starting analysis...")
            
            # Initialize data containers
            sentiment_data = None
            valuation_data = None
            fundamental_data = None
            price_data = None
            
            # Load sentiment analysis if enabled
            if self.use_sentiment:
                sentiment_data = self._get_latest_analysis(symbol, 'sentiment', current_date)
                
                # If sentiment data is missing, try to generate it
                if not sentiment_data and self.sentiment_agent:
                    try:
                        sentiment_data = self.sentiment_agent.analyze_sentiment(symbol, current_date)
                    except Exception as e:
                        self.logger.error(f"[{symbol}] Error generating sentiment: {e}")
                
                # Store price data from sentiment analysis if available
                if sentiment_data and 'current_price' in sentiment_data:
                    price_data = sentiment_data
            
            # Load valuation analysis if enabled
            if self.use_valuation:
                valuation_data = self._get_latest_analysis(symbol, 'valuation', current_date)
                
                # If valuation data is missing, try to generate it
                if not valuation_data and self.valuation_agent:
                    try:
                        valuation_data = self.valuation_agent.analyze_valuation(symbol, current_date)
                    except Exception as e:
                        self.logger.error(f"[{symbol}] Error generating valuation: {e}")
                
                # Store price data from valuation analysis if available
                if valuation_data and 'current_price' in valuation_data and not price_data:
                    price_data = valuation_data
            
            # Load fundamental analysis if enabled
            if self.use_fundamental:
                fundamental_data = self._get_latest_analysis(symbol, 'fundamental', current_date)
                
                # If fundamental data is missing, try to generate it
                if not fundamental_data and self.fundamental_agent:
                    try:
                        fundamental_data = self.fundamental_agent.analyze_fundamentals(symbol, current_date)
                    except Exception as e:
                        self.logger.error(f"[{symbol}] Error generating fundamental: {e}")
                
                # Store price data from fundamental analysis if available
                if fundamental_data and 'current_price' in fundamental_data and not price_data:
                    price_data = fundamental_data
            
            # Check if we have all required data
            required_data_present = True
            if self.use_sentiment and not sentiment_data:
                self.logger.warning(f"[{symbol}] Missing sentiment analysis")
                required_data_present = False
            
            if self.use_valuation and not valuation_data:
                self.logger.warning(f"[{symbol}] Missing valuation analysis")
                required_data_present = False
            
            if self.use_fundamental and not fundamental_data:
                self.logger.warning(f"[{symbol}] Missing fundamental analysis")
                required_data_present = False
            
            if not required_data_present:
                return None
            
            # Get previous decisions for context
            previous_decisions = self._load_previous_decisions(symbol, current_date)
            
            # Create a ReasoningAgent with the assigned API key
            reasoning_agent = ReasoningAgent(data_dir=self.data_dir, api_key_override=api_key)
            
            # Call reasoning agent
            decision_result = reasoning_agent.make_decision(
                symbol, current_date, valuation_data, fundamental_data, sentiment_data,
                previous_decisions=previous_decisions
            )
            
            # Add price data to decision
            if price_data and 'current_price' in price_data:
                decision_result['current_price'] = price_data['current_price']
            else:
                decision_result['current_price'] = self.portfolio.get('last_prices', {}).get(symbol, 100.0)
            
            # Add analysis data to decision
            if sentiment_data:
                decision_result['sentiment_data'] = sentiment_data.get('sentiment', 'Unknown')
            if valuation_data:
                decision_result['valuation_data'] = valuation_data.get('recommendation', 'Unknown')
            if fundamental_data:
                decision_result['fundamental_data'] = fundamental_data.get('recommendation', 'Unknown')
            
            self.logger.info(f"[{symbol}] ✅ Decision: {decision_result.get('decision')} "
                           f"(confidence: {decision_result.get('confidence', 0):.2f})")
            
            return decision_result
            
        except Exception as e:
            self.logger.error(f"[{symbol}] ❌ Error in analysis: {e}")
            return None
    
    def _save_decision(self, symbol, decision_record):
        """Save a decision record to file for future context"""
        try:
            decisions_dir = os.path.join(self.data_dir, 'reasoning_decisions_Claude')
            os.makedirs(decisions_dir, exist_ok=True)
            
            # Create filename with date and backtest name
            date_str = decision_record['date']
            filename = f"{symbol}_decision_{date_str}_{self.backtest_name}.json"
            filepath = os.path.join(decisions_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(decision_record, f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(f"Error saving decision for {symbol}: {e}")
    
    def _execute_portfolio_trades(self, portfolio_decisions, current_date):
        """Execute trades based on Portfolio Manager decisions"""
        trades_executed = 0
        
        for decision in portfolio_decisions.get('portfolio_decisions', []):
            symbol = decision.get('symbol')
            action = decision.get('action')
            amount_usd = decision.get('amount_usd', 0)
            reasoning = decision.get('reasoning', '')
            
            if action == 'BUY' and amount_usd > 0:
                # Get current price
                current_price = self.portfolio['last_prices'].get(symbol, 100.0)
                
                # Calculate shares to buy
                shares = int(amount_usd / current_price)
                cost = shares * current_price
                
                if cost <= self.portfolio['cash']:
                    # Update portfolio
                    if symbol not in self.portfolio['positions']:
                        self.portfolio['positions'][symbol] = {'shares': 0, 'avg_price': 0}
                    
                    # Calculate new average price
                    old_shares = self.portfolio['positions'][symbol]['shares']
                    old_avg = self.portfolio['positions'][symbol].get('avg_price', 0)
                    new_shares = old_shares + shares
                    new_avg = ((old_shares * old_avg) + (shares * current_price)) / new_shares if new_shares > 0 else current_price
                    
                    self.portfolio['positions'][symbol]['shares'] = new_shares
                    self.portfolio['positions'][symbol]['avg_price'] = new_avg
                    self.portfolio['cash'] -= cost
                    
                    # Record trade
                    trade_record = {
                        'date': current_date,
                        'symbol': symbol,
                        'action': 'BUY',
                        'shares': shares,
                        'price': current_price,
                        'cost': cost,
                        'reasoning': reasoning,
                        'portfolio_value': self._calculate_portfolio_value()
                    }
                    self.portfolio['theoretical_trades'].append(trade_record)
                    trades_executed += 1
                    
                    self.logger.info(f"✅ BUY {symbol}: {shares} shares @ ${current_price:.2f} = ${cost:,.2f}")
                else:
                    self.logger.warning(f"❌ BUY {symbol}: Insufficient cash (need ${cost:,.2f}, have ${self.portfolio['cash']:,.2f})")
            
            elif action == 'SELL':
                if symbol in self.portfolio['positions'] and self.portfolio['positions'][symbol]['shares'] > 0:
                    shares = self.portfolio['positions'][symbol]['shares']
                    current_price = self.portfolio['last_prices'].get(symbol, self.portfolio['positions'][symbol].get('avg_price', 0))
                    proceeds = shares * current_price
                    
                    self.portfolio['cash'] += proceeds
                    self.portfolio['positions'][symbol]['shares'] = 0
                    
                    # Record trade
                    trade_record = {
                        'date': current_date,
                        'symbol': symbol,
                        'action': 'SELL',
                        'shares': shares,
                        'price': current_price,
                        'proceeds': proceeds,
                        'reasoning': reasoning,
                        'portfolio_value': self._calculate_portfolio_value()
                    }
                    self.portfolio['theoretical_trades'].append(trade_record)
                    trades_executed += 1
                    
                    self.logger.info(f"✅ SELL {symbol}: {shares} shares @ ${current_price:.2f} = ${proceeds:,.2f}")
                else:
                    self.logger.warning(f"❌ SELL {symbol}: No position to sell")
        
        return trades_executed
    
    def _calculate_portfolio_value(self):
        """Calculate total portfolio value"""
        total_value = self.portfolio['cash']
        for symbol, pos in self.portfolio['positions'].items():
            if pos['shares'] > 0:
                current_price = self.portfolio['last_prices'].get(symbol, pos.get('avg_price', 0))
                total_value += pos['shares'] * current_price
        return total_value
    
    def run_backtest(self, symbols=['PLTR', 'NVDA', 'GOOGL']):
        """Run the parallel backtest for the specified date range."""
        self.logger.info(f"\n🚀 Starting PARALLEL backtest from {self.start_date} to {self.end_date}")
        self.logger.info(f"📊 Analyzing {len(symbols)} stocks in parallel")
        
        # Get trading calendar
        nyse = mcal.get_calendar('NYSE')
        trading_days = nyse.schedule(start_date=self.start_date, end_date=self.end_date)
        
        self.logger.info(f"📅 Found {len(trading_days)} trading days")
        
        total_decisions_made = 0
        total_trades_executed = 0
        
        # Process each trading day
        for trading_date in trading_days.index:
            current_date = trading_date.strftime('%Y-%m-%d')
            self.logger.info(f"\n{'='*80}")
            self.logger.info(f"📅 TRADING DAY: {current_date}")
            self.logger.info(f"{'='*80}")
            
            # Run stock analysis in parallel
            stock_decisions = []
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all stock analysis tasks
                future_to_symbol = {}
                for idx, symbol in enumerate(symbols):
                    # Assign API key in round-robin fashion
                    api_key = self.api_keys[idx % len(self.api_keys)]
                    future = executor.submit(self._analyze_single_stock, symbol, current_date, api_key)
                    future_to_symbol[future] = symbol
                
                # Collect results as they complete
                for future in as_completed(future_to_symbol):
                    symbol = future_to_symbol[future]
                    try:
                        decision_result = future.result()
                        if decision_result:
                            stock_decisions.append(decision_result)
                            
                            # Save decision for future context
                            self._save_decision(symbol, decision_result)
                            
                            # Update last known price
                            if 'current_price' in decision_result:
                                self.portfolio['last_prices'][symbol] = decision_result['current_price']
                    except Exception as e:
                        self.logger.error(f"[{symbol}] Exception in parallel execution: {e}")
            
            # Log all decisions
            self.logger.info(f"\n📊 Collected {len(stock_decisions)} stock decisions:")
            for decision in stock_decisions:
                self.logger.info(f"  {decision['symbol']}: {decision['decision']} "
                              f"(confidence: {decision.get('confidence', 0):.2f})")
            
            total_decisions_made += len(stock_decisions)
            
            # Call Portfolio Manager to make allocation decisions
            if stock_decisions:
                self.logger.info(f"\n💼 Calling Portfolio Manager for allocation decisions...")
                
                # Calculate current portfolio state
                portfolio_state = {
                    'cash': self.portfolio['cash'],
                    'positions': self.portfolio['positions'],
                    'last_prices': self.portfolio['last_prices'],
                    'total_value': self._calculate_portfolio_value()
                }
                
                # Get previous portfolio decisions for context
                previous_portfolio_decisions = self._load_previous_portfolio_decisions(current_date)
                
                # Get portfolio-level decisions
                portfolio_decisions = self.portfolio_manager.make_portfolio_decisions(
                    stock_decisions, portfolio_state, current_date, previous_portfolio_decisions
                )
                
                # Log portfolio manager decisions
                self.logger.info(f"\n💰 Portfolio Manager Decisions:")
                for pd in portfolio_decisions.get('portfolio_decisions', []):
                    self.logger.info(f"  {pd['symbol']}: {pd['action']} ${pd.get('amount_usd', 0):,.0f} "
                                   f"(target: {pd.get('portfolio_weight_target', 0):.1f}%)")
                
                summary = portfolio_decisions.get('portfolio_summary', {})
                self.logger.info(f"\n📈 Portfolio Summary:")
                self.logger.info(f"  Total Allocation: ${summary.get('total_allocation', 0):,.2f}")
                self.logger.info(f"  Cash Reserved: ${summary.get('cash_reserved', 0):,.2f}")
                self.logger.info(f"  Risk Assessment: {summary.get('risk_assessment', 'N/A')}")
                
                # Execute trades based on portfolio manager decisions
                trades_executed = self._execute_portfolio_trades(portfolio_decisions, current_date)
                total_trades_executed += trades_executed
                
                # Save portfolio decision for future context
                self._save_portfolio_decision(portfolio_decisions, current_date)
                
                # Log portfolio value
                portfolio_value = self._calculate_portfolio_value()
                self.logger.info(f"\n💼 Portfolio Value: ${portfolio_value:,.2f}")
        
        # Calculate final portfolio value and performance
        final_value = self._calculate_portfolio_value()
        initial_value = 1000000
        total_return = final_value - initial_value
        percent_return = (total_return / initial_value) * 100
        
        # Final results
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"🎉 PARALLEL BACKTEST COMPLETE!")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"📅 Date range: {self.start_date} to {self.end_date}")
        self.logger.info(f"📊 Total decisions made: {total_decisions_made}")
        self.logger.info(f"💰 Total trades executed: {total_trades_executed}")
        self.logger.info(f"\n📈 PORTFOLIO PERFORMANCE:")
        self.logger.info(f"  Starting value: ${initial_value:,.2f}")
        self.logger.info(f"  Final value: ${final_value:,.2f}")
        self.logger.info(f"  Total return: ${total_return:,.2f} ({percent_return:.2f}%)")
        self.logger.info(f"\n💼 Final positions:")
        for symbol, position in self.portfolio['positions'].items():
            if position['shares'] > 0:
                current_price = self.portfolio['last_prices'].get(symbol, position.get('avg_price', 0))
                value = position['shares'] * current_price
                pct = (value / final_value * 100) if final_value > 0 else 0
                self.logger.info(f"  {symbol}: {position['shares']} shares @ ${current_price:.2f} "
                              f"= ${value:,.2f} ({pct:.1f}%)")
        self.logger.info(f"  Cash: ${self.portfolio['cash']:,.2f} "
                        f"({self.portfolio['cash']/final_value*100:.1f}%)")
        
        return {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'decisions_made': total_decisions_made,
            'trades_executed': total_trades_executed,
            'portfolio': self.portfolio,
            'performance': {
                'initial_value': initial_value,
                'final_value': final_value,
                'total_return': total_return,
                'percent_return': percent_return
            }
        }


def main():
    parser = argparse.ArgumentParser(description='Run parallel backtest with portfolio management')
    parser.add_argument('--data-dir', default=os.path.dirname(os.path.abspath(__file__)),
                      help='Data directory (defaults to script directory)')
    parser.add_argument('--start-date', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--symbols', default='PLTR,NVDA,GOOGL', 
                      help='Comma-separated list of symbols to test')
    parser.add_argument('--lookback', type=int, default=4, 
                      help='Number of previous decisions to include as context')
    parser.add_argument('--backtest-name', default='parallel', 
                      help='Name for this backtest run')
    parser.add_argument('--max-workers', type=int, default=None,
                      help='Maximum number of parallel workers (defaults to number of API keys)')
    
    # Agent configuration
    parser.add_argument('--sentiment', action='store_true', help='Use sentiment analysis')
    parser.add_argument('--valuation', action='store_true', help='Use valuation analysis')
    parser.add_argument('--fundamental', action='store_true', help='Use fundamental analysis')
    parser.add_argument('--all-agents', action='store_true', help='Use all available agents')
    
    args = parser.parse_args()
    
    # Process agent configuration
    use_sentiment = args.sentiment or args.all_agents
    use_valuation = args.valuation or args.all_agents
    use_fundamental = args.fundamental or args.all_agents
    
    # Default to sentiment+valuation if no agents specified
    if not (use_sentiment or use_valuation or use_fundamental):
        use_sentiment = True
        use_valuation = True
        print("No agents specified, defaulting to Sentiment+Valuation combination")
    
    # Process symbols
    symbols = [s.strip() for s in args.symbols.split(',')]
    
    print(f"\n{'='*80}")
    print(f"🚀 PARALLEL BACKTEST CONFIGURATION")
    print(f"{'='*80}")
    print(f"📅 Date Range: {args.start_date} to {args.end_date}")
    print(f"📊 Symbols: {', '.join(symbols)}")
    print(f"🤖 Agents: {', '.join([a for a in ['Sentiment' if use_sentiment else None, 'Valuation' if use_valuation else None, 'Fundamental' if use_fundamental else None] if a])}")
    print(f"{'='*80}\n")
    
    # Initialize and run backtest
    backtest = ParallelBacktest(
        data_dir=args.data_dir,
        start_date=args.start_date,
        end_date=args.end_date,
        lookback_window=args.lookback,
        use_sentiment=use_sentiment,
        use_valuation=use_valuation,
        use_fundamental=use_fundamental,
        backtest_name=args.backtest_name,
        max_workers=args.max_workers
    )
    
    results = backtest.run_backtest(symbols=symbols)
    
    # Save results to file
    results_file = os.path.join(args.data_dir, f'parallel_backtest_{args.backtest_name}_results.json')
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n✅ Test complete! Results saved to {results_file}")
    print(f"\n📊 FINAL SUMMARY:")
    print(f"  Date range: {results['start_date']} to {results['end_date']}")
    print(f"  Decisions made: {results['decisions_made']}")
    print(f"  Trades executed: {results['trades_executed']}")
    print(f"\n💰 PORTFOLIO PERFORMANCE:")
    print(f"  Starting value: ${results['performance']['initial_value']:,.2f}")
    print(f"  Final value: ${results['performance']['final_value']:,.2f}")
    print(f"  Total return: ${results['performance']['total_return']:,.2f} "
          f"({results['performance']['percent_return']:.2f}%)")


if __name__ == "__main__":
    main()

