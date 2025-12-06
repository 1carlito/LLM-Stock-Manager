"""
base_executor.py: Core trade execution logic.

This is the base execution engine that handles the actual portfolio updates,
position management, and trade execution. Simulators wrap this to add costs.
"""

import math
from datetime import datetime
from typing import Dict, Any, Optional, Tuple


class BaseExecutor:
    """
    Core trade execution engine.
    
    Handles the actual execution of trades:
    - Updates portfolio state (cash, positions)
    - Manages long and short positions
    - Calculates average prices
    - Tracks entry dates
    
    Simulators wrap this to add execution costs (slippage, fees, etc.)
    """
    
    def __init__(self, portfolio: Dict[str, Any], logger=None):
        """
        Initialize base executor.
        
        Args:
            portfolio: Portfolio state dictionary (modified in place)
            logger: Optional logger for execution messages
        """
        self.portfolio = portfolio
        self.logger = logger
    
    def execute_buy(self, symbol: str, amount_usd: float, execution_price: float,
                   current_date: str, reasoning: str = "") -> Tuple[bool, Dict[str, Any]]:
        """
        Execute a BUY order (open or add to long position).
        
        Args:
            symbol: Stock symbol
            amount_usd: Dollar amount to allocate
            execution_price: Execution price (may include slippage/fees from simulator)
            current_date: Trading date
            reasoning: Optional reasoning for the trade
        
        Returns:
            Tuple of (success: bool, trade_info: dict)
        """
        if amount_usd <= 0 or execution_price <= 0:
            return False, {}
        
        # Calculate shares to buy
        shares = int(amount_usd / execution_price)
        if shares < 1:
            return False, {}
        
        cost = shares * execution_price
        
        # Check if we have enough cash
        if cost > self.portfolio.get('cash', 0):
            if self.logger:
                self.logger.warning(f"❌ BUY {symbol}: Insufficient cash (need ${cost:,.2f}, have ${self.portfolio.get('cash', 0):,.2f})")
            return False, {}
        
        # Deduct cash
        self.portfolio['cash'] -= cost
        
        # Update or create long position
        if 'positions' not in self.portfolio:
            self.portfolio['positions'] = {}
        
        current_long = self.portfolio['positions'].get(symbol, {'shares': 0, 'avg_price': 0})
        
        # Calculate new average price
        new_total_shares = current_long['shares'] + shares
        new_total_value = (current_long['shares'] * current_long.get('avg_price', 0)) + (shares * execution_price)
        new_avg_price = new_total_value / new_total_shares if new_total_shares > 0 else 0
        
        # Update position
        self.portfolio['positions'][symbol] = {
            'shares': new_total_shares,
            'avg_price': new_avg_price,
            'buy_date': current_date
        }
        
        trade_info = {
            'symbol': symbol,
            'action': 'BUY',
            'shares': shares,
            'price': execution_price,
            'cost': cost,
            'reasoning': reasoning
        }
        
        if self.logger:
            self.logger.info(f"✅ BUY {symbol}: {shares} shares @ ${execution_price:,.2f} (Cost: ${cost:,.2f}) - {reasoning}")
        
        return True, trade_info
    
    def execute_sell(self, symbol: str, execution_price: float, current_date: str,
                    reasoning: str = "", shares_to_sell: Optional[int] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Execute a SELL order (close long position).
        
        Args:
            symbol: Stock symbol
            execution_price: Execution price (may include slippage from simulator)
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
        proceeds = shares_to_sell * execution_price
        
        # Add cash
        self.portfolio['cash'] += proceeds
        
        # Update or remove position
        remaining_shares = positions[symbol]['shares'] - shares_to_sell
        if remaining_shares > 0:
            # Partial close - keep position with remaining shares
            positions[symbol]['shares'] = remaining_shares
        else:
            # Full close - remove position
            del positions[symbol]
        
        trade_info = {
            'symbol': symbol,
            'action': 'SELL',
            'shares': shares_to_sell,
            'price': execution_price,
            'proceeds': proceeds,
            'reasoning': reasoning
        }
        
        if self.logger:
            self.logger.info(f"✅ SELL {symbol}: {shares_to_sell} shares @ ${execution_price:,.2f} (Value: ${proceeds:,.2f}) - {reasoning}")
        
        return True, trade_info
    
    def execute_short(self, symbol: str, amount_usd: float, execution_price: float,
                     current_date: str, reasoning: str = "", spread_fee: float = 0.0) -> Tuple[bool, Dict[str, Any]]:
        """
        Execute a SHORT order (open or add to short position).
        Uses CFD model: deducts notional value + spread fee from cash.
        
        Args:
            symbol: Stock symbol
            amount_usd: Dollar amount to allocate
            execution_price: Execution price (may include slippage from simulator)
            current_date: Trading date
            reasoning: Optional reasoning for the trade
            spread_fee: Spread fee to deduct (calculated by simulator)
        
        Returns:
            Tuple of (success: bool, trade_info: dict)
        """
        if amount_usd <= 0 or execution_price <= 0:
            return False, {}
        
        # Calculate shares to short
        shares = int(amount_usd / execution_price)
        if shares < 1:
            return False, {}
        
        cost_or_value = shares * execution_price  # Notional value
        total_cost = cost_or_value + spread_fee
        
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
        new_total_value = (current_short['shares'] * current_short.get('avg_price', 0)) + (shares * execution_price)
        new_avg_price = new_total_value / new_total_shares if new_total_shares > 0 else 0
        
        # Use existing entry_date if position already exists, otherwise use current date
        entry_date = current_short.get('entry_date', current_date)
        
        # Update short position
        self.portfolio['short_positions'][symbol] = {
            'shares': new_total_shares,
            'avg_price': new_avg_price,
            'entry_date': entry_date,
            'short_date': current_date
        }
        
        trade_info = {
            'symbol': symbol,
            'action': 'SHORT',
            'shares': shares,
            'price': execution_price,
            'notional': cost_or_value,
            'spread_fee': spread_fee,
            'total_cost': total_cost,
            'reasoning': reasoning
        }
        
        if self.logger:
            self.logger.info(
                f"✅ SHORT {symbol}: {shares} shares @ ${execution_price:,.2f} "
                f"(Notional: ${cost_or_value:,.2f}, Spread Fee: ${spread_fee:,.2f}, "
                f"Cash Deducted: ${total_cost:,.2f}) - {reasoning}"
            )
        
        return True, trade_info
    
    def execute_cover(self, symbol: str, execution_price: float, current_date: str,
                     reasoning: str = "", shares_to_cover: Optional[int] = None,
                     exit_spread_fee: float = 0.0) -> Tuple[bool, Dict[str, Any]]:
        """
        Execute a COVER order (close short position).
        Uses CFD model: adds back entry notional + P&L, subtracts exit spread fee.
        
        Args:
            symbol: Stock symbol
            execution_price: Execution price (may include slippage from simulator)
            current_date: Trading date
            reasoning: Optional reasoning for the trade
            shares_to_cover: Number of shares to cover (None = cover all)
            exit_spread_fee: Exit spread fee (calculated by simulator)
        
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
        
        # CFD Model: Calculate fees and P&L
        entry_notional = shares_to_cover * short_pos.get('avg_price', 0)
        
        # Profit/Loss from the short position
        pnl = (short_pos.get('avg_price', 0) - execution_price) * shares_to_cover
        
        # Cash update: Add back entry notional + P&L, subtract exit spread fee
        cash_change = entry_notional + pnl - exit_spread_fee
        self.portfolio['cash'] += cash_change
        
        # Update or remove short position
        remaining_shares = short_pos['shares'] - shares_to_cover
        if remaining_shares > 0:
            # Partial cover - keep position
            short_positions[symbol]['shares'] = remaining_shares
        else:
            # Full cover - remove position
            del short_positions[symbol]
        
        trade_info = {
            'symbol': symbol,
            'action': 'COVER',
            'shares': shares_to_cover,
            'price': execution_price,
            'entry_price': short_pos.get('avg_price', 0),
            'entry_notional': entry_notional,
            'pnl': pnl,
            'exit_spread_fee': exit_spread_fee,
            'cash_change': cash_change,
            'reasoning': reasoning
        }
        
        if self.logger:
            self.logger.info(
                f"✅ COVER {symbol}: {shares_to_cover} shares @ ${execution_price:,.2f}. "
                f"P/L: ${pnl:,.2f}, Exit Spread: ${exit_spread_fee:,.2f} - {reasoning}"
            )
        
        return True, trade_info
    
    def execute_close(self, symbol: str, execution_price: float, current_date: str,
                     reasoning: str = "") -> Tuple[bool, Dict[str, Any]]:
        """
        Execute a CLOSE order (generic - tries SELL first, then COVER).
        
        Args:
            symbol: Stock symbol
            execution_price: Execution price
            current_date: Trading date
            reasoning: Optional reasoning for the trade
        
        Returns:
            Tuple of (success: bool, trade_info: dict)
        """
        # Try to SELL long position first
        success, trade_info = self.execute_sell(symbol, execution_price, current_date, reasoning)
        if success:
            return True, trade_info
        
        # If no long position, try to COVER short position
        success, trade_info = self.execute_cover(symbol, execution_price, current_date, reasoning)
        if success:
            return True, trade_info
        
        # No position found
        if self.logger:
            self.logger.info(f"⏭️ CLOSE {symbol}: No position found - {reasoning}")
        
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
        base_rate = 0.0006 + 0.0010
        
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

