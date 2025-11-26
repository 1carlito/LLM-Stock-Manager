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
import math

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from ReasoningAgent import ReasoningAgent
from SentimentAgent import SentimentAgent
from ValuationAgent import ValuationAgent
from FundamentalAgent import FundamentalAgent
from PortfolioManagerAgent import PortfolioManagerAgent


SHORT_SELLING_CONFIG = {
    'enabled': True,
    'max_short_allocation_pct': 25,
    'margin_requirement_pct': 50,
    'default_holding_period_days': 7, 
    'max_holding_period_days': 90, 
    'max_short_per_stock_pct': 25,
    'auto_close_enabled': True,
    'stop_loss_pct': None,
    'take_profit_pct': None,
    'overnight_fee_rate': 0.02
}


class ParallelBacktest:
    """
    Run a backtest with parallel stock analysis and portfolio-level decision making.
    """
    
    def __init__(self, data_dir='.', start_date=None, end_date=None, lookback_window=4,
                 use_sentiment=True, use_valuation=True, use_fundamental=True,
                 backtest_name=None, api_keys=None, max_workers=None):
        self.data_dir = data_dir
        self.start_date = start_date
        self.end_date = end_date
        self.lookback_window = lookback_window
        self.use_sentiment = use_sentiment
        self.use_valuation = use_valuation
        self.use_fundamental = use_fundamental
        self.backtest_name = backtest_name or 'backtest'
        
        # API key configuration
        self.api_keys = api_keys or self._load_api_keys()
        self.max_workers = max_workers or min(len(self.api_keys), 20)  # Support up to 20 parallel workers
        
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
            'cash': 100000,  # $100k starting capital 
            'positions': {}, # Long positions: {symbol: {'shares': X, 'avg_price': Y}}
            'last_prices': {},
            'theoretical_trades': [],
            'short_positions': {}, # Short positions: {symbol: {'shares': X, 'avg_price': Y}}
            'market_caps': {}
        }
        
        # Track previous decisions for each symbol
        self.previous_decisions = defaultdict(list)
        
        # Initialize Portfolio Manager
        self.portfolio_manager = PortfolioManagerAgent(data_dir=data_dir)
        
        # Initialize shared analysis agents 
        self.sentiment_agent = None
        self.valuation_agent = None
        self.fundamental_agent = None
        
        self.logger.info(f"Parallel Backtest initialized:")
        self.logger.info(f"- Date range: {start_date} to {end_date}")
    
    def _load_api_keys(self):
        """Load API tokens from environment variables for ReasoningAgent (Chutes/DeepSeek)."""
        from dotenv import load_dotenv
        load_dotenv()
        
        keys = []
        
        # Try to load numbered tokens (supporting multiple naming conventions)
        for i in range(1, 21):  # Support up to 20 API tokens
            candidate_names = [
                f"DEEPSEEK_API_KEY_{i}" # legacy fallback
            ]
            token = next((os.getenv(name) for name in candidate_names if os.getenv(name)), None)
            if token:
                keys.append(token)
        
        # If still no tokens, try the shared defaults
        if not keys:
            for fallback_name in (
                "PORTFOLIO_CHUTES_DEEPSEEK_API_KEY"
            ):
                default_token = os.getenv(fallback_name)
                if default_token:
                    keys.append(default_token)
                    break
        
        if not keys:
            raise ValueError(
                "No Chutes/DeepSeek API tokens found. Set DEEPSEEK_API_KEY_1 (or related variants) in the environment."
            )
        
        print(f"Loaded {len(keys)} Chutes token(s) for ReasoningAgent")
        return keys
    
    def _get_latest_analysis(self, symbol, analysis_type, current_date):
        """Get the latest analysis file for a symbol and type before or on the current date."""
        # Map analysis types to directory names
        # Paths are relative to aws/Mid_Cap/ directory
        dir_mapping = {
            'valuation': 'valuation_reports',
            'fundamental': 'fundamental_test_reports',
            'sentiment': 'sentiment_data'
        }
        
        if analysis_type not in dir_mapping:
            return None
        
        # Ensure we use the correct path relative to data_dir (which should be aws/Mid_Cap/)
        analysis_dir = os.path.join(self.data_dir, dir_mapping[analysis_type])
        # Convert to absolute path to ensure we're looking in the right place
        analysis_dir = os.path.abspath(analysis_dir)
        
        # Log the path being checked for debugging
        if not os.path.exists(analysis_dir):
            self.logger.warning(f"[{symbol}] Analysis directory not found: {analysis_dir}")
            # Try parent directory as fallback (aws/valuation_reports, aws/fundamental_reports, etc.)
            parent_dir = os.path.dirname(self.data_dir)
            fallback_dir = os.path.join(parent_dir, dir_mapping[analysis_type])
            fallback_dir = os.path.abspath(fallback_dir)
            if os.path.exists(fallback_dir):
                self.logger.info(f"[{symbol}] Using fallback directory: {fallback_dir}")
                analysis_dir = fallback_dir
            else:
                return None
        
        self.logger.debug(f"[{symbol}] Looking for {analysis_type} analysis in: {analysis_dir}")
            
        # Find files for this symbol - pattern matches: {symbol}_*analysis*.json or {symbol}.EXCHANGE_*analysis*.json
        # e.g., VKTX_fundamental_analysis_20251119_215808.json or HAG.DE_fundamental_analysis_20251119.json
        # Note: Date filtering is done by reading the date from INSIDE the JSON, not from filename
        # Try both with and without exchange suffix (e.g., HAG and HAG.DE)
        patterns = [
            os.path.join(analysis_dir, f"{symbol}_*analysis*.json"),  # Standard: HAG_*analysis*.json
            os.path.join(analysis_dir, f"{symbol}.*_*analysis*.json"),  # With exchange: HAG.DE_*analysis*.json
        ]
        
        files = []
        for pattern in patterns:
            files = glob.glob(pattern)
            if files:
                break
        
        if not files:
            self.logger.debug(f"[{symbol}] No {analysis_type} files found in {analysis_dir} with pattern: {pattern}")
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
            decisions_dir = os.path.join(self.data_dir, 'reasoning_decisions_DSeek')
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
            decisions_dir = os.path.join(self.data_dir, 'portfolio_decisions_DSeek')
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

    def _get_price_for_symbol(self, symbol, current_date):
        """
        Get current price for a symbol without full analysis.
        Used to update prices for positions that aren't in the daily analysis list.
        Tries historical stock data file first (most reliable), then cached analysis files.
        """
        try:
            # First try: Get price directly from historical stock data file (most reliable)
            price = self._get_price_from_stock_data(symbol, current_date)
            
            # Second try: Get price from existing analysis files (fallback)
            if not price:
                sentiment_data = self._get_latest_analysis(symbol, 'sentiment', current_date) if self.use_sentiment else None
                valuation_data = self._get_latest_analysis(symbol, 'valuation', current_date) if self.use_valuation else None
                fundamental_data = self._get_latest_analysis(symbol, 'fundamental', current_date) if self.use_fundamental else None
                
                # Extract Price (Priority: Sentiment -> Valuation -> Fundamental)
                if sentiment_data: price = sentiment_data.get('current_price')
                if not price and valuation_data: price = valuation_data.get('current_price')
                if not price and fundamental_data: price = fundamental_data.get('current_price')
            
            return price
        except Exception as e:
            self.logger.debug(f"[{symbol}] Could not fetch price: {e}")
            return None
    
    def _get_price_from_stock_data(self, symbol, current_date):
        """Get price directly from historical stock data file (quant_data)"""
        try:
            import glob
            from datetime import datetime
            
            # Find stock data file (same pattern as other agents)
            quant_data_dir = os.path.join(self.data_dir, "quant_data")
            primary_file = os.path.join(quant_data_dir, "mid_cap_stock_data_20250701_20251101_20251116_132209.json")
            
            if not os.path.exists(primary_file):
                # Try to find any mid_cap_stock_data file
                mid_cap_files = glob.glob(os.path.join(quant_data_dir, "mid_cap_stock_data_*.json"))
                if mid_cap_files:
                    mid_cap_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                    primary_file = mid_cap_files[0]
            
            if not os.path.exists(primary_file):
                return None
            
            # Load stock data
            with open(primary_file, 'r') as f:
                stock_data = json.load(f)
            
            if symbol not in stock_data:
                return None
            
            # Get historical prices for this symbol
            historical_prices = stock_data[symbol].get('historical_prices', [])
            if not historical_prices:
                return None
            
            # Find price for current_date (or latest before it)
            target_date_obj = datetime.strptime(current_date, '%Y-%m-%d')
            sorted_prices = sorted(historical_prices, key=lambda x: x.get('date', ''))
            valid_prices = []
            
            for price_data in sorted_prices:
                price_date_str = price_data.get('date', '')
                if price_date_str:
                    try:
                        price_date = datetime.strptime(price_date_str, '%Y-%m-%d')
                        if price_date <= target_date_obj:
                            valid_prices.append(price_data)
                    except ValueError:
                        continue
            
            if valid_prices:
                latest_price = valid_prices[-1].get('close')
                if isinstance(latest_price, (int, float)):
                    return float(latest_price)
            
            return None
        except Exception as e:
            self.logger.debug(f"[{symbol}] Error getting price from stock data: {e}")
            return None
            
    def _analyze_single_stock(self, symbol, current_date, api_key):
        """
        Analyze a single stock. Returns the decision AND the price found in the analysis.
        """
        try:
            # Load Data
            sentiment_data = self._get_latest_analysis(symbol, 'sentiment', current_date) if self.use_sentiment else None
            valuation_data = self._get_latest_analysis(symbol, 'valuation', current_date) if self.use_valuation else None
            fundamental_data = self._get_latest_analysis(symbol, 'fundamental', current_date) if self.use_fundamental else None
            
            # Extract Price (Priority: Sentiment -> Valuation -> Fundamental)
            price = None
            if sentiment_data: price = sentiment_data.get('current_price')
            if not price and valuation_data: price = valuation_data.get('current_price')
            if not price and fundamental_data: price = fundamental_data.get('current_price')
            
            # Default to last known if completely missing
            if not price:
                price = self.portfolio.get('last_prices', {}).get(symbol, 100.0)

            # --- MARKET CAP LOGIC ---
            # (Preserved from original)
            try:
                data_sources = [x for x in [sentiment_data, valuation_data, fundamental_data] if x]
                for data in data_sources:
                    mc = data.get('market_cap') or data.get('marketCap') or data.get('market_cap_bil')
                    if mc:
                        market_cap_bil = (mc / 1_000_000_000.0) if mc > 1e6 else mc
                        self.portfolio.setdefault('market_caps', {})[symbol] = float(market_cap_bil)
                        break
            except: pass

            previous_decisions = self._load_previous_decisions(symbol, current_date)
            reasoning_agent = ReasoningAgent(data_dir=self.data_dir, api_key_override=api_key)
            
            decision_result = reasoning_agent.make_decision(
                symbol, current_date, valuation_data, fundamental_data, sentiment_data,
                previous_decisions=previous_decisions
            )
            
            # Attach the price we found to the decision object
            decision_result['current_price'] = price
            
            return decision_result
            
        except Exception as e:
            self.logger.error(f"[{symbol}] ❌ Error in analysis: {e}")
            return None
    
    def _calculate_portfolio_value(self):
        """
        Calculate total portfolio value: Cash + Long Positions Value + Short Notional + Short P&L
        CFD Model (No Leverage): Short notional is tied-up collateral, so it counts toward portfolio value.
        Uses current day's prices from last_prices, falling back to avg_price if not available.
        """
        total_value = self.portfolio['cash']
        
        # Add long positions value
        for symbol, pos in self.portfolio['positions'].items():
            if pos.get('shares', 0) > 0:
                current_price = self.portfolio['last_prices'].get(symbol, pos.get('avg_price', 0))
                if current_price <= 0:
                    # Fallback to avg_price if no current price available
                    current_price = pos.get('avg_price', 0)
                position_value = pos['shares'] * current_price
                total_value += position_value
        
        # Add short positions notional + P&L (CFD model: notional is tied-up collateral)
        for symbol, short_pos in self.portfolio.get('short_positions', {}).items():
            if short_pos.get('shares', 0) > 0:
                current_price = self.portfolio['last_prices'].get(symbol, short_pos.get('avg_price', 0))
                if current_price <= 0:
                    # Fallback to avg_price if no current price available
                    current_price = short_pos.get('avg_price', 0)
                entry_price = short_pos.get('avg_price', current_price)
                
                # Short Notional: The collateral tied up in this position (entry price - what you originally locked up)
                short_notional = short_pos['shares'] * entry_price
                
                # Short P&L: profit when price goes DOWN (entry_price > current_price)
                # P&L = (Entry Price - Current Price) * Shares
                short_pnl = (entry_price - current_price) * short_pos['shares']
                
                # Add notional (tied-up collateral at entry) + P&L (unrealized gain/loss)
                total_value += short_notional + short_pnl
        
        return total_value

    def _get_short_spread_rate(self, symbol):
        """
        Calculate spread rate for short positions.
        Formula: 0.0006 + (1.0 / sqrt(market_cap_bil)) + 0.0010
        This matches the formula used in PortfolioManagerAgent waterfall allocation.
        """
        base_rate = 0.0006 + 0.0010  # Base spread components
        mc_bil = self.portfolio.get('market_caps', {}).get(symbol)
        if mc_bil and mc_bil > 0:
            return base_rate + (1.0 / math.sqrt(mc_bil))
        return base_rate

    def _execute_portfolio_trades(self, portfolio_decisions_list, current_date):
        """
        Executes the trades proposed by the Portfolio Manager after waterfall allocation.
        It must map the PM's simple decisions (BUY, SHORT, CLOSE) to the trading actions
        (BUY, SHORT, SELL, COVER) and apply real-time price updates.
        """
        trades_executed = 0
        
        # The Portfolio Manager returns a list of dictionaries with 'decision' and 'amount_usd'
        decisions = portfolio_decisions_list # This is now the list directly
        
        # We must re-prioritize CLOSES first for execution, then SHORTS, then BUYS
        # We map PM's decision ('CLOSE') to execution actions ('SELL'/'COVER')
        action_priority = {'CLOSE': 1, 'SHORT': 2, 'BUY': 3, 'MAINTAIN': 4, 'NEUTRAL': 5}
        sorted_decisions = sorted(decisions, key=lambda x: action_priority.get((x.get('action') or x.get('decision') or '').upper(), 99))
        
        available_cash = self.portfolio['cash']
        
        self.logger.info(f"🔧 Executing {len(sorted_decisions)} portfolio decisions...")
        for decision in sorted_decisions:
            symbol = decision.get('symbol')
            pm_decision = (decision.get('action') or decision.get('decision') or '').upper() # This is key
            amount_usd = decision.get('amount_usd', 0)
            reasoning = decision.get('reasoning', '')
            
            self.logger.debug(f"   Processing: {symbol} - {pm_decision} - ${amount_usd:,.2f}")
            
            # --- Trade Parameters ---
            current_price = self.portfolio['last_prices'].get(symbol, 0)
            if current_price <= 0:
                self.logger.warning(f"Skipping trade for {symbol}: price is ${current_price:,.2f}")
                continue
                
            shares_requested = int(amount_usd / current_price)
            cost_or_value = shares_requested * current_price # Actual transaction size (rounded)
            
            # --- 1. CLOSE/COVER/SELL (High Priority: Must resolve to SELL or COVER) ---
            # Note: CLOSE/COVER/SELL can have amount_usd = 0 (means close full position)
            if pm_decision in ('CLOSE', 'COVER', 'SELL'):
                # For CLOSE/COVER/SELL, amount_usd can be 0 (means close full position)
                # Check for Long Position to SELL
                if symbol in self.portfolio['positions'] and self.portfolio['positions'][symbol]['shares'] > 0:
                    shares_to_close = self.portfolio['positions'][symbol]['shares']
                    
                    self.portfolio['cash'] += shares_to_close * current_price
                    del self.portfolio['positions'][symbol]
                    
                    self.logger.info(f"✅ SELL/CLOSE LONG {symbol}: {shares_to_close} shares @ ${current_price:,.2f} (Value: ${shares_to_close*current_price:,.2f}) - {reasoning}")
                    trades_executed += 1
                    
                # Check for Short Position to COVER
                elif symbol in self.portfolio.get('short_positions', {}) and self.portfolio['short_positions'][symbol]['shares'] > 0:
                    short_pos = self.portfolio['short_positions'][symbol]
                    shares_to_cover = short_pos['shares']
                    entry_date = short_pos.get('entry_date', current_date)
                    
                    # Calculate days held for overnight fees
                    try:
                        entry_date_obj = datetime.strptime(entry_date, '%Y-%m-%d')
                        current_date_obj = datetime.strptime(current_date, '%Y-%m-%d')
                        days_held = (current_date_obj - entry_date_obj).days
                        if days_held < 0:
                            days_held = 0
                    except:
                        days_held = 0
                    
                    # CFD Model: Calculate fees and P&L
                    entry_notional = short_pos['shares'] * short_pos['avg_price']  # Original notional we deducted
                    
                    # Calculate exit spread fee
                    spread_rate = self._get_short_spread_rate(symbol)
                    exit_spread_fee = (shares_to_cover * current_price) * spread_rate
                    
                    # Note: Overnight fees are already charged daily via _update_short_positions()
                    # We do NOT charge them again on close to avoid double-counting
                    
                    # Profit/Loss from the short position
                    pnl = (short_pos['avg_price'] - current_price) * shares_to_cover
                    
                    # Cash update for CFD: Add back entry notional + P&L, subtract exit spread fee
                    # Overnight fees have already been deducted daily, so we don't subtract them here
                    # When we opened the short, we deducted entry_notional, so we add it back here
                    # P&L adjusts for price movement (loss reduces what we get back, gain increases it)
                    self.portfolio['cash'] += entry_notional + pnl - exit_spread_fee
                    del self.portfolio['short_positions'][symbol]

                    self.logger.info(f"✅ COVER/CLOSE SHORT {symbol}: {shares_to_cover} shares @ ${current_price:,.2f}. P/L: ${pnl:,.2f}, Exit Spread: ${exit_spread_fee:,.2f} (Overnight fees already charged daily) - {reasoning}")
                    trades_executed += 1
                    
                else:
                    self.logger.info(f"⏭️ NEUTRAL {symbol}: CLOSE proposed but no position found. - {reasoning}")
            
            # --- 2. SHORT (CFD Model: Deduct Notional Value + Spread Fee) ---
            elif pm_decision == 'SHORT' and amount_usd > 0 and shares_requested > 0:
                # Calculate entry spread fee
                spread_rate = self._get_short_spread_rate(symbol)
                entry_spread_fee = cost_or_value * spread_rate
                
                # For CFD shorts: Deduct the notional value (executed trade value) + spread fee from cash
                # Example: Short $30k → Cash decreases by $30k + spread fee
                self.portfolio['cash'] -= (cost_or_value + entry_spread_fee)

                # Update/Create Short Position
                current_short = self.portfolio['short_positions'].get(symbol, {'shares': 0, 'avg_price': 0})
                
                # Calculate new average price (shares are always positive in the position record)
                new_total_shares = current_short['shares'] + shares_requested
                new_total_value = (current_short['shares'] * current_short['avg_price']) + (shares_requested * current_price)
                new_avg_price = new_total_value / new_total_shares if new_total_shares > 0 else 0
                
                # Use existing entry_date if position already exists, otherwise use current date
                entry_date = current_short.get('entry_date', current_date)
                
                self.portfolio['short_positions'][symbol] = {
                    'shares': new_total_shares,
                    'avg_price': new_avg_price,
                    'entry_date': entry_date,  # Keep original entry date for overnight fee calculation
                    'short_date': current_date  # Track when this addition was made
                }
                
                self.logger.info(f"✅ SHORT {symbol}: {shares_requested} shares @ ${current_price:,.2f} (Notional: ${cost_or_value:,.2f}, Spread Fee: ${entry_spread_fee:,.2f}, Cash Deducted: ${cost_or_value + entry_spread_fee:,.2f}) - {reasoning}")
                trades_executed += 1
                    
            # --- 3. BUY (Uses Cash) ---
            elif pm_decision == 'BUY' and amount_usd > 0 and shares_requested > 0:
                # The PM's waterfall logic already constrained the allocation, so we assume
                # the cash needed for the 'amount_usd' is within the available cash.
                
                # Update cash
                self.portfolio['cash'] -= cost_or_value

                # Update/Create Long Position
                current_long = self.portfolio['positions'].get(symbol, {'shares': 0, 'avg_price': 0})
                
                # Calculate new average price
                new_total_shares = current_long['shares'] + shares_requested
                new_total_value = (current_long['shares'] * current_long['avg_price']) + (shares_requested * current_price)
                new_avg_price = new_total_value / new_total_shares if new_total_shares > 0 else 0

                self.portfolio['positions'][symbol] = {
                    'shares': new_total_shares,
                    'avg_price': new_avg_price,
                    'buy_date': current_date # Assume first buy date is current date for simplicity
                }
                
                self.logger.info(f"✅ BUY {symbol}: {shares_requested} shares @ ${current_price:,.2f} (Cost: ${cost_or_value:,.2f}) - {reasoning}")
                trades_executed += 1

            # --- 4. NEUTRAL / MAINTAIN ---
            elif pm_decision in ['NEUTRAL', 'MAINTAIN']:
                self.logger.info(f"⏭️ {pm_decision} {symbol} - {reasoning}")
            
            else:
                 # Catch-all for non-actionable or zero-amount entries
                pass
        
        return trades_executed
    
    def _update_short_positions(self, current_date):
        """
        Update short positions daily: charge overnight fees for open positions.
        CFD Model: Overnight fees accrue daily and reduce cash.
        """
        if not self.portfolio.get('short_positions'):
            return
        
        overnight_fee_rate = SHORT_SELLING_CONFIG.get('overnight_fee_rate', 0.02)  # 2% annual
        
        for symbol, short_pos in self.portfolio['short_positions'].items():
            if short_pos.get('shares', 0) <= 0:
                continue
            
            # Get entry date
            entry_date = short_pos.get('entry_date', current_date)
            
            try:
                entry_date_obj = datetime.strptime(entry_date, '%Y-%m-%d')
                current_date_obj = datetime.strptime(current_date, '%Y-%m-%d')
                
                # Only charge fee if position is held overnight (entry date < current date)
                # and we haven't charged for today yet
                if current_date_obj > entry_date_obj:
                    # Check if we've already charged for today
                    last_fee_date = short_pos.get('last_fee_date', '')
                    if last_fee_date != current_date:
                        # Calculate overnight fee for this day (1 day worth of 2% annual rate)
                        entry_value = short_pos['shares'] * short_pos.get('avg_price', 0)
                        daily_overnight_fee = entry_value * overnight_fee_rate / 365.0
                        
                        # Deduct daily overnight fee from cash
                        self.portfolio['cash'] -= daily_overnight_fee
                        
                        # Update last fee date to prevent double-charging on same day
                        short_pos['last_fee_date'] = current_date
                        
                        self.logger.debug(f"💰 Charged overnight fee for {symbol}: ${daily_overnight_fee:,.2f} (${entry_value:,.2f} notional)")
                        
            except (ValueError, TypeError) as e:
                # Skip if date parsing fails
                continue 
    
    def run_backtest(self, symbols):
        self.logger.info(f"\n🚀 Starting PARALLEL backtest")
        nyse = mcal.get_calendar('NYSE')
        trading_days = nyse.schedule(start_date=self.start_date, end_date=self.end_date)
        
        total_trades = 0
        
        for trading_date in trading_days.index:
            current_date = trading_date.strftime('%Y-%m-%d')
            self.logger.info(f"\n{'='*80}\n📅 TRADING DAY: {current_date}\n{'='*80}")
            
            # 1. ANALYZE STOCKS (Parallel)
            stock_decisions = []
            today_prices = {} # Temp store for audit
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_symbol = {}
                for idx, symbol in enumerate(symbols):
                    api_key = self.api_keys[idx % len(self.api_keys)]
                    # Small stagger to avoid simultaneous burst (0.1s per request)
                    # This helps prevent hitting global rate limits even with different API keys
                    import time
                    if idx > 0:
                        time.sleep(0.1 * idx)  # Stagger: 0s, 0.1s, 0.2s, 0.3s...
                    future = executor.submit(self._analyze_single_stock, symbol, current_date, api_key)
                    future_to_symbol[future] = symbol
                
                for future in as_completed(future_to_symbol):
                    res = future.result()
                    if res:
                        stock_decisions.append(res)
                        if 'current_price' in res:
                            today_prices[res['symbol']] = res['current_price']
            
            # 2. AUDIT: PRINT PRICES (Strict Requirement)
            self.logger.info("\n🔍 ==== DAILY PRICE AUDIT ====")
            for sym in sorted(today_prices.keys()):
                price = today_prices[sym]
                self.logger.info(f"   {sym:<6} : ${price:,.2f}")
                # UPDATE SOURCE OF TRUTH HERE
                self.portfolio['last_prices'][sym] = price
            
            # 2b. UPDATE PRICES FOR POSITIONS NOT IN DAILY ANALYSIS
            # This ensures short/long positions get price updates even if symbol isn't analyzed today
            all_position_symbols = set()
            all_position_symbols.update(self.portfolio.get('positions', {}).keys())
            all_position_symbols.update(self.portfolio.get('short_positions', {}).keys())
            
            missing_price_symbols = all_position_symbols - set(today_prices.keys())
            if missing_price_symbols:
                self.logger.info(f"📊 Fetching prices for {len(missing_price_symbols)} positions not in daily analysis...")
                for sym in missing_price_symbols:
                    price = self._get_price_for_symbol(sym, current_date)
                    if price:
                        self.portfolio['last_prices'][sym] = price
                        self.logger.info(f"   {sym:<6} : ${price:,.2f} (from cached analysis)")
                    else:
                        # Keep last known price if we can't find new one
                        existing_price = self.portfolio.get('last_prices', {}).get(sym)
                        if existing_price:
                            self.logger.debug(f"   {sym:<6} : ${existing_price:,.2f} (using last known price)")
                        else:
                            self.logger.warning(f"   {sym:<6} : No price found, using avg_price fallback")
            
            self.logger.info("==============================\n")

            # 3. UPDATE SHORT POSITIONS (Charge daily overnight fees)
            self._update_short_positions(current_date)
            
            # 4. PORTFOLIO ALLOCATION (Single Threaded Waterfall)
            self.logger.info(f"📊 Collected {len(stock_decisions)} stock decisions for portfolio allocation")
            if stock_decisions:
                self.logger.info(f"   Symbols: {[d.get('symbol') for d in stock_decisions]}")
                
                # Calculate portfolio value BEFORE trades (for PMA decision making)
                portfolio_value = self._calculate_portfolio_value()
                
                # Log portfolio value breakdown for debugging
                cash = self.portfolio['cash']
                long_value = sum(
                    pos['shares'] * self.portfolio['last_prices'].get(sym, pos.get('avg_price', 0))
                    for sym, pos in self.portfolio['positions'].items()
                    if pos.get('shares', 0) > 0
                )
                short_pnl = sum(
                    (short_pos.get('avg_price', 0) - self.portfolio['last_prices'].get(sym, short_pos.get('avg_price', 0))) * short_pos['shares']
                    for sym, short_pos in self.portfolio.get('short_positions', {}).items()
                    if short_pos.get('shares', 0) > 0
                )
                short_notional = sum(
                    short_pos['shares'] * short_pos.get('avg_price', 0)
                    for sym, short_pos in self.portfolio.get('short_positions', {}).items()
                    if short_pos.get('shares', 0) > 0
                )
                
                self.logger.info(f"💰 Portfolio Value Breakdown (before trades):")
                self.logger.info(f"   Cash: ${cash:,.2f}")
                self.logger.info(f"   Long Positions Value: ${long_value:,.2f}")
                self.logger.info(f"   Short Notional Locked: ${short_notional:,.2f}")
                self.logger.info(f"   Short P&L: ${short_pnl:,.2f}")
                self.logger.info(f"   Total Portfolio Value: ${portfolio_value:,.2f}")
                
                # --- Prepare PM Agent Arguments ---
                current_cash = self.portfolio['cash']
                
                # Build full portfolio_state dictionary with all required fields
                portfolio_state = {
                    'cash': current_cash,
                    'total_value': portfolio_value,
                    'initial_value': 100000,  # $100k starting capital
                    'positions': self.portfolio['positions'].copy(),
                    'short_positions': self.portfolio.get('short_positions', {}).copy(),
                    'last_prices': self.portfolio['last_prices'].copy(),
                    'market_caps': self.portfolio.get('market_caps', {}).copy(),  # Include market caps for spread calculation
                    'max_short_per_stock_pct': SHORT_SELLING_CONFIG.get('max_short_per_stock_pct', 25)
                }
                
                # CALL PM (Now returns a strictly calculated list)
                portfolio_decisions_list = self.portfolio_manager.get_portfolio_decisions(
                    stock_decisions,
                    portfolio_state=portfolio_state,
                    current_date=current_date,
                    previous_portfolio_decisions=self._load_previous_portfolio_decisions(current_date)
                )
                
                # 4. EXECUTE TRADES (Pass the list directly)
                portfolio_decisions = portfolio_decisions_list.get('portfolio_decisions', [])
                self.logger.info(f"📋 Received {len(portfolio_decisions)} portfolio decisions from PMA")
                if portfolio_decisions:
                    self.logger.info(f"   Decisions: {[(d.get('symbol'), d.get('action') or d.get('decision'), d.get('amount_usd', 0)) for d in portfolio_decisions[:10]]}")
                
                trades = self._execute_portfolio_trades(portfolio_decisions, current_date)
                total_trades += trades
                self.logger.info(f"✅ Executed {trades} trades this day")

                # 5. END OF DAY LOGGING
                final_val = self._calculate_portfolio_value()
                
                # Log detailed breakdown
                final_cash = self.portfolio['cash']
                final_long_value = sum(
                    pos['shares'] * self.portfolio['last_prices'].get(sym, pos.get('avg_price', 0))
                    for sym, pos in self.portfolio['positions'].items()
                    if pos.get('shares', 0) > 0
                )
                final_short_pnl = sum(
                    (short_pos.get('avg_price', 0) - self.portfolio['last_prices'].get(sym, short_pos.get('avg_price', 0))) * short_pos['shares']
                    for sym, short_pos in self.portfolio.get('short_positions', {}).items()
                    if short_pos.get('shares', 0) > 0
                )
                final_short_notional = sum(
                    short_pos['shares'] * short_pos.get('avg_price', 0)  # Use entry price (avg_price) for notional
                    for sym, short_pos in self.portfolio.get('short_positions', {}).items()
                    if short_pos.get('shares', 0) > 0
                )
                
                self.logger.info(f"\n🏁 EOD SUMMARY {current_date}")
                self.logger.info(f"   Cash: ${final_cash:,.2f}")
                self.logger.info(f"   Long Positions Value: ${final_long_value:,.2f}")
                self.logger.info(f"   Short Notional Exposure: ${final_short_notional:,.2f}")
                self.logger.info(f"   Short P&L: ${final_short_pnl:,.2f}")
                self.logger.info(f"   Total Value: ${final_val:,.2f}")
                
                # Validation: Total should equal cash + longs + short notional + short P&L (CFD model: notional is collateral)
                calculated_total = final_cash + final_long_value + final_short_notional + final_short_pnl
                if abs(final_val - calculated_total) > 0.01:
                    self.logger.warning(f"⚠️ Portfolio value mismatch! Calculated: ${calculated_total:,.2f}, Reported: ${final_val:,.2f}")
                
        return {'status': 'completed', 'total_trades': total_trades, 'start_date': self.start_date, 'end_date': self.end_date,
                'decisions_made': len(trading_days.index) * len(symbols), 'trades_executed': total_trades,
                'performance': {'initial_value': 100000, 'final_value': final_val, 'total_return': final_val - 100000,
                                'percent_return': (final_val / 100000.0 - 1) * 100}}


def main():
    parser = argparse.ArgumentParser(description='Run parallel backtest with portfolio management')
    parser.add_argument('--data-dir', default=os.path.dirname(os.path.abspath(__file__)),
                      help='Data directory (defaults to script directory)')
    parser.add_argument('--start-date', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--symbols', required=True,
                      help='Comma-separated list of symbols to test')
    parser.add_argument('--lookback', type=int, default=4, 
                      help='Number of previous decisions to include as context')
    parser.add_argument('--backtest-name', required=True,
                      help='Name for this backtest run (required)')
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
    
    # Add start/end dates for final logging (moved from run_backtest)
    results['start_date'] = args.start_date
    results['end_date'] = args.end_date
    
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
    print(f"  True Profit (after all fees): ${results['performance']['total_return']:,.2f} ")
    print(f"({results['performance']['percent_return']:.2f}%)")
    print(f"\n  Note: True profit includes all costs:")
    print(f"    - Entry spread fees (deducted on short open)")
    print(f"    - Exit spread fees (deducted on short close)")
    print(f"    - Overnight fees (2% annual, charged daily)")


if __name__ == "__main__":
    main()