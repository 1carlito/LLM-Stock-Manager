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

# Default sector priority map (can be overridden by portfolio_state['sector_priority'])
DEFAULT_SECTOR_PRIORITY = {
    "Technology": 3.0,
    "Healthcare": 3.0,
    "Financial Services": 2.0,
    "Consumer Defensive": 2.0,
    "Consumer Cyclical": 2.0,
    "Industrials": 2.0,
    "Energy": 1.0,
    "Materials": 1.0,
    "Real Estate": 1.0,
    "Utilities": 1.0,
    "Communication Services": 1.0,
    "Unknown": 0.0,
}

# Default industry (subsector) priority map (can be overridden by portfolio_state['industry_priority'])
# These scores are ADDED to sector scores for combined prioritization
DEFAULT_INDUSTRY_PRIORITY = {
    # Technology subsectors
    "Consumer Electronics": 2.0,
    "Software": 1.5,
    "Semiconductors": 2.5,
    "Internet Content & Information": 1.0,
    "Computer Hardware": 1.0,
    "Telecom Services": 0.5,
    
    # Healthcare subsectors
    "Biotechnology": 2.5,
    "Pharmaceuticals": 2.0,
    "Medical Devices": 1.5,
    "Healthcare Plans": 1.0,
    
    # Financial Services subsectors
    "Banks - Diversified": 1.5,
    "Capital Markets": 1.0,
    "Insurance": 0.5,
    "Credit Services": 0.5,
    
    # Consumer subsectors
    "Auto Manufacturers": 1.5,
    "Retail - Cyclical": 1.0,
    "Packaged Foods": 0.5,
    
    # Default
    "Unknown": 0.0,
}


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
        
        # Build combined sector + industry priority map
        # Priority: portfolio_state configs > DEFAULT configs
        sector_priority_config = portfolio_state.get('sector_priority', DEFAULT_SECTOR_PRIORITY)
        industry_priority_config = portfolio_state.get('industry_priority', DEFAULT_INDUSTRY_PRIORITY)
        combined_priority_map = {}
        
        # Build per-symbol combined priority (sector_score + industry_score)
        if stock_decisions:
            for d in stock_decisions:
                symbol = d.get('symbol')
                sector = d.get('sector') or d.get('Sector') or 'Unknown'
                industry = d.get('industry') or d.get('Industry') or 'Unknown'
                
                # Get sector score
                sector_score = sector_priority_config.get(sector, sector_priority_config.get('Unknown', 0.0))
                
                # Get industry (subsector) score
                industry_score = industry_priority_config.get(industry, industry_priority_config.get('Unknown', 0.0))
                
                # Combined score: sector + industry (additive)
                combined_priority_map[symbol] = sector_score + industry_score
        
        # Sort BUY decisions by (confidence, combined_priority, symbol)
        # Primary: confidence (higher first) - use negative for reverse sort
        # Secondary: combined_priority (sector + industry, higher first) - use negative for reverse sort
        # Tertiary: symbol (alphabetical, A-Z first) - normal sort (no negative)
        def _buy_sort_key(d):
            symbol = d.get('symbol', '')
            conf = confidence_map.get(symbol, 0.5)
            combined_pri = combined_priority_map.get(symbol, 0.0)
            # Negate conf and combined_pri so higher values sort first
            # symbol stays positive so A-Z sorts first
            return (-conf, -combined_pri, symbol)
        
        def _short_sort_key(d):
            symbol = d.get('symbol', '')
            conf = short_confidence_map.get(symbol, confidence_map.get(symbol, 0.5))
            combined_pri = combined_priority_map.get(symbol, 0.0)
            # Negate conf and combined_pri so higher values sort first
            # symbol stays positive so A-Z sorts first
            return (-conf, -combined_pri, symbol)
        
        buy_decisions.sort(key=_buy_sort_key)
        short_decisions.sort(key=_short_sort_key)
        
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
            # Get portfolio value for max allocation calculation
            portfolio_value = portfolio_state.get('total_value', available_cash)
            max_allocation_pct = portfolio_state.get('max_allocation_pct', 0.30)  # Default 30% max per position
            
            for decision in short_decisions:
                symbol = decision.get('symbol')
                price = last_prices.get(symbol, 0)
                
                if price <= 0:
                    continue
                
                # Get short_confidence from stock_decisions (if available)
                short_confidence = short_confidence_map.get(symbol, confidence_map.get(symbol, 0.5))
                
                # Calculate allocation: short_confidence * max_allocation
                # max_allocation = min(portfolio_value * max_allocation_pct, remaining_cash * short_cap_pct)
                max_allocation_absolute = portfolio_value * max_allocation_pct
                short_cap_absolute = remaining_cash * short_cap_pct
                max_allocation = min(max_allocation_absolute, short_cap_absolute)
                
                # Calculate amount based on short_confidence
                requested_amount = max_allocation * short_confidence
                capped_amount = requested_amount
                
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
                    f"spread_fee: ${spread_fee:,.2f}, short_conf: {short_confidence:.2f}, "
                    f"max_alloc: ${max_allocation:,.2f})"
                )
                final_decisions.append(decision)
                
                # Deduct from remaining cash (notional + spread fee)
                remaining_cash -= (final_amount + spread_fee)
        
        # Process BUY decisions
        # Get portfolio value for max allocation calculation
        portfolio_value = portfolio_state.get('total_value', available_cash)
        max_allocation_pct = portfolio_state.get('max_allocation_pct', 0.30)  # Default 30% max per position
        
        for decision in buy_decisions:
            symbol = decision.get('symbol')
            price = last_prices.get(symbol, 0)
            
            if price <= 0:
                continue
            
            # Get confidence from stock_decisions (if available)
            confidence = confidence_map.get(symbol, 0.5)
            
            # Calculate allocation: confidence * max_allocation
            # max_allocation = min(portfolio_value * max_allocation_pct, remaining_cash * per_trade_cap_pct)
            max_allocation_absolute = portfolio_value * max_allocation_pct
            per_trade_cap_absolute = remaining_cash * self.per_trade_cap_pct
            max_allocation = min(max_allocation_absolute, per_trade_cap_absolute)
            
            # Calculate amount based on confidence
            requested_amount = max_allocation * confidence
            
            # Ensure at least 1 share
            if requested_amount < price:
                continue  # Skip if can't afford 1 share
            
            # Round down to whole shares
            shares = int(requested_amount // price)
            if shares < 1:
                continue
            
            final_amount = shares * price
            
            # Update remaining cash
            remaining_cash -= final_amount
            
            # Update decision fields
            decision['amount_usd'] = final_amount
            decision['reasoning'] = (
                f"{decision.get('reasoning', '')} "
                f"(waterfall: ${final_amount:,.2f}, {shares} shares, confidence: {confidence:.2f}, "
                f"max_alloc: ${max_allocation:,.2f})"
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

