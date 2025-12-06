"""
trade_executor.py: Trade execution logic for BUY, SELL, SHORT, and COVER operations.

This module handles the actual execution of trades, updating portfolio state,
calculating fees, P&L, and managing positions.
"""

import math
from datetime import datetime
from typing import Dict, Any, Optional, Tuple


class TradeExecutor:
    """
    Executes trades and updates portfolio state.
    Handles BUY, SELL, SHORT, and COVER operations.
    """
    
    def __init__(self, portfolio: Dict[str, Any], logger=None):
        """
        Initialize trade executor.
        
        Args:
            portfolio: Portfolio state dictionary (modified in place)
            logger: Optional logger for trade execution messages
        """
        self.portfolio = portfolio
        self.logger = logger
    
    def execute_buy(self, symbol: str, amount_usd: float, current_price: float, 
                   current_date: str, reasoning: str = "") -> Tuple[bool, Dict[str, Any]]:
        """
        Execute a BUY order (open or add to long position).
        
        Args:
            symbol: Stock symbol
            amount_usd: Dollar amount to allocate (already waterfall-allocated)
            current_price: Current stock price
            current_date: Trading date
            reasoning: Optional reasoning for the trade
        
        Returns:
            Tuple of (success: bool, trade_info: dict)
        """
        if amount_usd <= 0 or current_price <= 0:
            return False, {}
        
        # Calculate shares to buy
        shares = int(amount_usd / current_price)
        if shares < 1:
            return False, {}
        
        cost = shares * current_price
        
        # Check if we have enough cash
        if cost > self.portfolio.get('cash', 0):
            if self.logger:
                self.logger.warning(f"❌ BUY {symbol}: Insufficient cash (need ${cost:,.2f}, have ${self.portfolio.get('cash', 0):,.2f})")
            return False, {}
        
        # Deduct cash
        self.portfolio['cash'] -= cost
        
        # Update or create long position
        current_long = self.portfolio.get('positions', {}).get(symbol, {'shares': 0, 'avg_price': 0})
        
        # Calculate new average price
        new_total_shares = current_long['shares'] + shares
        new_total_value = (current_long['shares'] * current_long.get('avg_price', 0)) + (shares * current_price)
        new_avg_price = new_total_value / new_total_shares if new_total_shares > 0 else 0
        
        # Update position
        if 'positions' not in self.portfolio:
            self.portfolio['positions'] = {}
        
        self.portfolio['positions'][symbol] = {
            'shares': new_total_shares,
            'avg_price': new_avg_price,
            'buy_date': current_date
        }
        
        trade_info = {
            'symbol': symbol,
            'action': 'BUY',
            'shares': shares,
            'price': current_price,
            'cost': cost,
            'reasoning': reasoning
        }
        
        if self.logger:
            self.logger.info(f"✅ BUY {symbol}: {shares} shares @ ${current_price:,.2f} (Cost: ${cost:,.2f}) - {reasoning}")
        
        return True, trade_info
    
    def execute_sell(self, symbol: str, current_price: float, current_date: str, 
                    reasoning: str = "", shares_to_sell: Optional[int] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Execute a SELL order (close long position).
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
            current_date: Trading date
            reasoning: Optional reasoning for the trade
            shares_to_sell: Number of shares to sell (None = sell all)
        
        Returns:
            Tuple of (success: bool, trade_info: dict)
        """
        positions = self.portfolio.get('positions', {})
        
        if symbol not in positions or positions[symbol].get('shares', 0) <= 0:
            if self.logger:
                self.logger.info(f"⏭️ SELL {symbol}: No long position to sell - {reasoning}")
            return False, {}
        
        # Determine shares to sell
        if shares_to_sell is None:
            shares_to_sell = positions[symbol]['shares']
        else:
            shares_to_sell = min(shares_to_sell, positions[symbol]['shares'])
        
        if shares_to_sell <= 0:
            return False, {}
        
        # Calculate proceeds
        proceeds = shares_to_sell * current_price
        
        # Add cash
        self.portfolio['cash'] += proceeds
        
        # Update or remove position
        remaining_shares = positions[symbol]['shares'] - shares_to_sell
        if remaining_shares > 0:
            # Partial close - keep position with remaining shares
            positions[symbol]['shares'] = remaining_shares
            # Keep same avg_price for remaining shares
        else:
            # Full close - remove position
            del positions[symbol]
        
        trade_info = {
            'symbol': symbol,
            'action': 'SELL',
            'shares': shares_to_sell,
            'price': current_price,
            'proceeds': proceeds,
            'reasoning': reasoning
        }
        
        if self.logger:
            self.logger.info(f"✅ SELL {symbol}: {shares_to_sell} shares @ ${current_price:,.2f} (Value: ${proceeds:,.2f}) - {reasoning}")
        
        return True, trade_info
    
    def execute_short(self, symbol: str, amount_usd: float, current_price: float,
                     current_date: str, reasoning: str = "") -> Tuple[bool, Dict[str, Any]]:
        """
        Execute a SHORT order (open or add to short position).
        Uses CFD model: deducts notional value + spread fee from cash.
        
        Args:
            symbol: Stock symbol
            amount_usd: Dollar amount to allocate (already waterfall-allocated)
            current_price: Current stock price
            current_date: Trading date
            reasoning: Optional reasoning for the trade
        
        Returns:
            Tuple of (success: bool, trade_info: dict)
        """
        if amount_usd <= 0 or current_price <= 0:
            return False, {}
        
        # Calculate shares to short
        shares = int(amount_usd / current_price)
        if shares < 1:
            return False, {}
        
        cost_or_value = shares * current_price  # Notional value
        
        # Calculate entry spread fee
        spread_rate = self._get_short_spread_rate(symbol)
        entry_spread_fee = cost_or_value * spread_rate
        
        total_cost = cost_or_value + entry_spread_fee
        
        # Check if we have enough cash
        if total_cost > self.portfolio.get('cash', 0):
            if self.logger:
                self.logger.warning(f"❌ SHORT {symbol}: Insufficient cash (need ${total_cost:,.2f}, have ${self.portfolio.get('cash', 0):,.2f})")
            return False, {}
        
        # Deduct cash (notional + spread fee)
        self.portfolio['cash'] -= total_cost
        
        # Update or create short position
        if 'short_positions' not in self.portfolio:
            self.portfolio['short_positions'] = {}
        
        current_short = self.portfolio['short_positions'].get(symbol, {'shares': 0, 'avg_price': 0})
        
        # Calculate new average price
        new_total_shares = current_short['shares'] + shares
        new_total_value = (current_short['shares'] * current_short.get('avg_price', 0)) + (shares * current_price)
        new_avg_price = new_total_value / new_total_shares if new_total_shares > 0 else 0
        
        # Use existing entry_date if position already exists, otherwise use current date
        entry_date = current_short.get('entry_date', current_date)
        
        # Update short position
        self.portfolio['short_positions'][symbol] = {
            'shares': new_total_shares,
            'avg_price': new_avg_price,
            'entry_date': entry_date,  # Keep original entry date for overnight fee calculation
            'short_date': current_date  # Track when this addition was made
        }
        
        trade_info = {
            'symbol': symbol,
            'action': 'SHORT',
            'shares': shares,
            'price': current_price,
            'notional': cost_or_value,
            'spread_fee': entry_spread_fee,
            'total_cost': total_cost,
            'reasoning': reasoning
        }
        
        if self.logger:
            self.logger.info(
                f"✅ SHORT {symbol}: {shares} shares @ ${current_price:,.2f} "
                f"(Notional: ${cost_or_value:,.2f}, Spread Fee: ${entry_spread_fee:,.2f}, "
                f"Cash Deducted: ${total_cost:,.2f}) - {reasoning}"
            )
        
        return True, trade_info
    
    def execute_cover(self, symbol: str, current_price: float, current_date: str,
                     reasoning: str = "", shares_to_cover: Optional[int] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Execute a COVER order (close short position).
        Uses CFD model: adds back entry notional + P&L, subtracts exit spread fee.
        Note: Overnight fees are charged daily, not on close.
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
            current_date: Trading date
            reasoning: Optional reasoning for the trade
            shares_to_cover: Number of shares to cover (None = cover all)
        
        Returns:
            Tuple of (success: bool, trade_info: dict)
        """
        short_positions = self.portfolio.get('short_positions', {})
        
        if symbol not in short_positions or short_positions[symbol].get('shares', 0) <= 0:
            if self.logger:
                self.logger.info(f"⏭️ COVER {symbol}: No short position to cover - {reasoning}")
            return False, {}
        
        short_pos = short_positions[symbol]
        entry_date = short_pos.get('entry_date', current_date)
        
        # Determine shares to cover
        if shares_to_cover is None:
            shares_to_cover = short_pos['shares']
        else:
            shares_to_cover = min(shares_to_cover, short_pos['shares'])
        
        if shares_to_cover <= 0:
            return False, {}
        
        # Calculate days held (for reference, not used in fee calculation)
        try:
            entry_date_obj = datetime.strptime(entry_date, '%Y-%m-%d')
            current_date_obj = datetime.strptime(current_date, '%Y-%m-%d')
            days_held = max(0, (current_date_obj - entry_date_obj).days)
        except (ValueError, TypeError):
            days_held = 0
        
        # CFD Model: Calculate fees and P&L
        entry_notional = shares_to_cover * short_pos.get('avg_price', 0)  # Original notional deducted
        
        # Calculate exit spread fee
        spread_rate = self._get_short_spread_rate(symbol)
        exit_spread_fee = (shares_to_cover * current_price) * spread_rate
        
        # Note: Overnight fees are already charged daily via _update_short_positions()
        # We do NOT charge them again on close to avoid double-counting
        
        # Profit/Loss from the short position
        # P&L = (entry_price - exit_price) * shares
        # If price went down, we profit (entry > exit)
        # If price went up, we lose (entry < exit)
        pnl = (short_pos.get('avg_price', 0) - current_price) * shares_to_cover
        
        # Cash update for CFD:
        # Add back entry notional + P&L, subtract exit spread fee
        # Overnight fees have already been deducted daily, so we don't subtract them here
        cash_change = entry_notional + pnl - exit_spread_fee
        self.portfolio['cash'] += cash_change
        
        # Update or remove short position
        remaining_shares = short_pos['shares'] - shares_to_cover
        if remaining_shares > 0:
            # Partial cover - keep position with remaining shares
            # Recalculate avg_price for remaining shares (keep same avg_price)
            short_positions[symbol]['shares'] = remaining_shares
            # Keep same avg_price and entry_date for remaining shares
        else:
            # Full cover - remove position
            del short_positions[symbol]
        
        trade_info = {
            'symbol': symbol,
            'action': 'COVER',
            'shares': shares_to_cover,
            'price': current_price,
            'entry_price': short_pos.get('avg_price', 0),
            'entry_notional': entry_notional,
            'pnl': pnl,
            'exit_spread_fee': exit_spread_fee,
            'cash_change': cash_change,
            'days_held': days_held,
            'reasoning': reasoning
        }
        
        if self.logger:
            self.logger.info(
                f"✅ COVER {symbol}: {shares_to_cover} shares @ ${current_price:,.2f}. "
                f"P/L: ${pnl:,.2f}, Exit Spread: ${exit_spread_fee:,.2f} "
                f"(Overnight fees already charged daily) - {reasoning}"
            )
        
        return True, trade_info
    
    def execute_close(self, symbol: str, current_price: float, current_date: str,
                     reasoning: str = "") -> Tuple[bool, Dict[str, Any]]:
        """
        Execute a CLOSE order (generic - closes either long or short position).
        Tries to SELL long position first, then COVER short position.
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
            current_date: Trading date
            reasoning: Optional reasoning for the trade
        
        Returns:
            Tuple of (success: bool, trade_info: dict)
        """
        # Try to SELL long position first
        success, trade_info = self.execute_sell(symbol, current_price, current_date, reasoning)
        if success:
            return True, trade_info
        
        # If no long position, try to COVER short position
        success, trade_info = self.execute_cover(symbol, current_price, current_date, reasoning)
        if success:
            return True, trade_info
        
        # No position found
        if self.logger:
            self.logger.info(f"⏭️ CLOSE {symbol}: No position found (neither long nor short) - {reasoning}")
        
        return False, {}
    
    def _get_short_spread_rate(self, symbol: str) -> float:
        """
        Calculate spread rate for short positions.
        Formula: 0.0006 + 0.0010 + (1.0 / sqrt(market_cap_bil))
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Spread rate as a decimal (e.g., 0.0016 = 0.16%)
        """
        base_rate = 0.0006 + 0.0010  # Base spread components
        
        market_caps = self.portfolio.get('market_caps', {})
        market_cap_bil = 10  # fallback
        
        if symbol in market_caps:
            try:
                mcval = float(market_caps[symbol])
                if mcval > 0:
                    market_cap_bil = mcval
            except (ValueError, TypeError):
                pass
        
        spread_rate = base_rate + (1.0 / math.sqrt(market_cap_bil))
        
        return spread_rate


def execute_trade(portfolio: Dict[str, Any], decision: Dict[str, Any], 
                 current_date: str, logger=None) -> Tuple[bool, Dict[str, Any]]:
    """
    Convenience function to execute a single trade decision.
    
    Args:
        portfolio: Portfolio state dictionary (modified in place)
        decision: Decision dict with 'action', 'symbol', 'amount_usd', 'current_price', etc.
        current_date: Trading date
        logger: Optional logger
    
    Returns:
        Tuple of (success: bool, trade_info: dict)
    """
    executor = TradeExecutor(portfolio, logger)
    
    action = (decision.get('action') or decision.get('decision') or '').upper()
    symbol = decision.get('symbol')
    current_price = decision.get('current_price', portfolio.get('last_prices', {}).get(symbol, 0))
    amount_usd = decision.get('amount_usd', 0)
    reasoning = decision.get('reasoning', '')
    
    if action == 'BUY':
        return executor.execute_buy(symbol, amount_usd, current_price, current_date, reasoning)
    elif action == 'SELL':
        return executor.execute_sell(symbol, current_price, current_date, reasoning)
    elif action == 'SHORT':
        return executor.execute_short(symbol, amount_usd, current_price, current_date, reasoning)
    elif action == 'COVER':
        return executor.execute_cover(symbol, current_price, current_date, reasoning)
    elif action == 'CLOSE':
        return executor.execute_close(symbol, current_price, current_date, reasoning)
    else:
        if logger:
            logger.info(f"⏭️ {action} {symbol} - {reasoning}")
        return False, {}

