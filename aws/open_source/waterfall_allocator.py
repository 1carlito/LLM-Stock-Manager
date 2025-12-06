"""
waterfall_allocator.py: Waterfall allocation algorithm for portfolio cash management.

This module provides sequential cash-constrained allocation that ensures:
- Trades are processed in priority order (CLOSE/SELL/COVER → SHORT → BUY)
- Cash is updated after each trade
- Each trade is capped at a percentage of remaining cash
- No overspending is possible
"""

import math
from typing import List, Dict, Any, Optional


class WaterfallAllocator:
    """
    Waterfall allocation: Process decisions sequentially, updating cash after each trade.
    Enforces strict per-trade caps and prevents overspending.
    """
    
    def __init__(self, 
                 per_trade_cap_pct: float = 0.25,
                 short_cap_pct: float = 0.25,
                 cash_threshold_pct: float = 0.25,
                 initial_value: float = 100000):
        """
        Initialize waterfall allocator.
        
        Args:
            per_trade_cap_pct: Maximum percentage of remaining cash per trade (default: 0.25 = 25%)
            short_cap_pct: Maximum percentage for short positions (default: 0.25 = 25%)
            cash_threshold_pct: Block new shorts when cash < this % of initial value (default: 0.25 = 25%)
            initial_value: Initial portfolio value for threshold calculations (default: $100k)
        """
        self.per_trade_cap_pct = per_trade_cap_pct
        self.short_cap_pct = short_cap_pct
        self.cash_threshold_pct = cash_threshold_pct
        self.initial_value = initial_value
    
    def allocate(self, 
                 decisions_list: List[Dict[str, Any]], 
                 portfolio_state: Dict[str, Any],
                 stock_decisions: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Apply waterfall allocation to a list of trading decisions.
        
        Args:
            decisions_list: List of decisions to allocate (each with 'action', 'symbol', 'amount_usd', etc.)
            portfolio_state: Current portfolio state with 'cash', 'last_prices', 'market_caps', etc.
            stock_decisions: Optional list of stock decisions for confidence mapping
        
        Returns:
            List of allocated decisions with updated 'amount_usd' values
        """
        available_cash = portfolio_state.get('cash', 0)
        last_prices = portfolio_state.get('last_prices', {}) or {}
        market_caps = portfolio_state.get('market_caps', {})
        max_short_per_stock_pct = portfolio_state.get('max_short_per_stock_pct', 25)
        
        # Calculate short cap (further limited by max_short_per_stock_pct)
        short_cap_pct = min(self.short_cap_pct, (max_short_per_stock_pct or 25) / 100.0)
        
        # Calculate cash threshold for blocking shorts
        cash_threshold = self.initial_value * self.cash_threshold_pct
        
        # Separate decisions by action type for priority processing
        # SELL = closing long positions, COVER = closing short positions, CLOSE = generic
        close_decisions = [
            d for d in decisions_list 
            if d.get('action', '').upper() in ('CLOSE', 'COVER', 'SELL')
        ]
        short_decisions = [
            d for d in decisions_list 
            if d.get('action', '').upper() == 'SHORT'
        ]
        buy_decisions = [
            d for d in decisions_list 
            if d.get('action', '').upper() == 'BUY'
        ]
        other_decisions = [
            d for d in decisions_list 
            if d.get('action', '').upper() not in ('CLOSE', 'COVER', 'SELL', 'SHORT', 'BUY')
        ]
        
        # Build confidence map from stock_decisions (if provided)
        confidence_map = {}
        short_confidence_map = {}
        if stock_decisions:
            confidence_map = {
                d.get('symbol'): d.get('confidence', 0.5) 
                for d in stock_decisions
            }
            short_confidence_map = {
                d.get('symbol'): d.get('short_confidence', d.get('confidence', 0.5)) 
                for d in stock_decisions
            }
        
        # Sort BUY and SHORT by confidence (higher first)
        buy_decisions.sort(
            key=lambda x: confidence_map.get(x.get('symbol'), 0.5), 
            reverse=True
        )
        short_decisions.sort(
            key=lambda x: short_confidence_map.get(x.get('symbol'), 0.5), 
            reverse=True
        )
        
        remaining_cash = available_cash
        final_decisions = []
        
        # Process CLOSE/SELL/COVER first (these generate cash, don't need allocation)
        # SELL = closing long positions, COVER = closing short positions
        for decision in close_decisions:
            # CLOSE/SELL/COVER actions don't need cash allocation
            # They generate cash when executed, so always include them
            final_decisions.append(decision)
        
        # Process SHORT decisions (for CFD: deduct notional + spread fees)
        # BLOCK new shorts if cash < threshold
        if available_cash < cash_threshold:
            # Skip all SHORT decisions when cash is below threshold
            for decision in short_decisions:
                decision['amount_usd'] = 0
                decision['reasoning'] = (
                    f"{decision.get('reasoning', '')} "
                    f"(blocked: cash ${available_cash:,.2f} < "
                    f"{self.cash_threshold_pct*100:.0f}% of initial ${cash_threshold:,.2f})"
                )
                decision['action'] = 'NEUTRAL'  # Convert to NEUTRAL instead of SHORT
            # Still add them but with amount_usd = 0
            final_decisions.extend(short_decisions)
        else:
            # Normal SHORT processing
            for decision in short_decisions:
                symbol = decision.get('symbol')
                requested_amount = abs(float(decision.get('amount_usd', 0) or 0))
                price = last_prices.get(symbol, 0)
                
                if price <= 0:
                    continue
                
                # Calculate cap: per_trade_cap_pct of remaining cash (further limited by short_cap_pct)
                cap = min(remaining_cash * self.per_trade_cap_pct, remaining_cash * short_cap_pct)
                capped_amount = min(requested_amount, cap)
                
                if capped_amount < price:
                    continue  # Skip if can't afford 1 share
                
                shares = int(capped_amount // price)
                if shares < 1:
                    continue
                
                final_amount = shares * price
                
                # Calculate spread fee for shorts
                spread_rate = self._calculate_spread_rate(symbol, market_caps)
                spread_fee = final_amount * spread_rate
                
                # If trade would cause overspend, reduce or skip
                if final_amount + spread_fee > remaining_cash:
                    shares = int(remaining_cash // (price * (1 + spread_rate)))
                    if shares < 1:
                        continue
                    final_amount = shares * price
                    spread_fee = final_amount * spread_rate
                
                # Update decision fields
                decision['amount_usd'] = final_amount
                decision['reasoning'] = (
                    f"{decision.get('reasoning', '')} "
                    f"(waterfall: ${final_amount:,.2f}, {shares} shares, "
                    f"spread_fee: ${spread_fee:,.2f})"
                )
                final_decisions.append(decision)
                
                # Deduct from remaining cash (notional + spread fee)
                remaining_cash -= (final_amount + spread_fee)
        
        # Process BUY decisions
        for decision in buy_decisions:
            symbol = decision.get('symbol')
            requested_amount = abs(float(decision.get('amount_usd', 0) or 0))
            price = last_prices.get(symbol, 0)
            
            if price <= 0:
                continue
            
            # Calculate cap: per_trade_cap_pct of remaining cash
            buy_cap = remaining_cash * self.per_trade_cap_pct
            
            # Cap the requested amount
            capped_amount = min(requested_amount, buy_cap)
            
            # Ensure at least 1 share
            if capped_amount < price:
                continue  # Skip if can't afford 1 share
            
            # Round down to whole shares
            shares = int(capped_amount // price)
            if shares < 1:
                continue
            
            final_amount = shares * price
            
            # Update remaining cash
            remaining_cash -= final_amount
            
            # Update decision fields
            decision['amount_usd'] = final_amount
            decision['reasoning'] = (
                f"{decision.get('reasoning', '')} "
                f"(waterfall: ${final_amount:,.2f}, {shares} shares)"
            )
            final_decisions.append(decision)
        
        # Add other decisions (NEUTRAL, MAINTAIN, etc.)
        final_decisions.extend(other_decisions)
        
        return final_decisions
    
    def _calculate_spread_rate(self, symbol: str, market_caps: Dict[str, float]) -> float:
        """
        Calculate spread rate for short positions.
        Formula: 0.0006 + 0.0010 + (1.0 / sqrt(market_cap_bil))
        
        Args:
            symbol: Stock symbol
            market_caps: Dictionary of market caps in billions
        
        Returns:
            Spread rate as a decimal (e.g., 0.0016 = 0.16%)
        """
        base_rate = 0.0006 + 0.0010  # Base spread components
        
        # Get market cap in billions
        market_cap_bil = 10  # fallback
        if symbol in market_caps:
            try:
                mcval = float(market_caps[symbol])
                if mcval > 0:
                    market_cap_bil = mcval
            except (ValueError, TypeError):
                pass
        
        # Calculate spread rate
        spread_rate = base_rate + (1.0 / math.sqrt(market_cap_bil))
        
        return spread_rate


def allocate_decisions(decisions_list: List[Dict[str, Any]], 
                       portfolio_state: Dict[str, Any],
                       stock_decisions: Optional[List[Dict[str, Any]]] = None,
                       per_trade_cap_pct: float = 0.25,
                       short_cap_pct: float = 0.25,
                       cash_threshold_pct: float = 0.25,
                       initial_value: float = 100000) -> List[Dict[str, Any]]:
    """
    Convenience function for waterfall allocation.
    
    Args:
        decisions_list: List of decisions to allocate
        portfolio_state: Current portfolio state
        stock_decisions: Optional list of stock decisions for confidence mapping
        per_trade_cap_pct: Maximum percentage of remaining cash per trade (default: 0.25)
        short_cap_pct: Maximum percentage for short positions (default: 0.25)
        cash_threshold_pct: Block new shorts when cash < this % of initial (default: 0.25)
        initial_value: Initial portfolio value (default: $100k)
    
    Returns:
        List of allocated decisions with updated 'amount_usd' values
    """
    allocator = WaterfallAllocator(
        per_trade_cap_pct=per_trade_cap_pct,
        short_cap_pct=short_cap_pct,
        cash_threshold_pct=cash_threshold_pct,
        initial_value=initial_value
    )
    return allocator.allocate(decisions_list, portfolio_state, stock_decisions)

