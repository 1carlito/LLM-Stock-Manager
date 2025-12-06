"""
OpenBB Data Provider

Data provider for OpenBB Platform.
Uses OpenBB as a data source while maintaining our own interface.

OpenBB provides unified access to 350+ data providers including:
- Yahoo Finance (free)
- Alpha Vantage
- Polygon.io
- Intrinio
- And many more...

Installation: pip install openbb-platform
Documentation: https://docs.openbb.co/
"""

import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

try:
    from openbb import obb
    OPENBB_AVAILABLE = True
except ImportError:
    OPENBB_AVAILABLE = False
    obb = None


class OpenBBProvider:
    """
    Data provider for OpenBB Platform.
    
    Uses OpenBB as a data source while maintaining our own interface.
    OpenBB is just the implementation detail - we control the interface.
    """
    
    def __init__(self, api_key: str = None, provider: str = None):
        """
        Initialize OpenBB provider.
        
        Args:
            api_key: OpenBB Personal Access Token (optional, for premium features)
            provider: Preferred data provider (e.g., 'yahoo', 'alpha_vantage', 'polygon')
                     If None, uses OpenBB's default provider
        """
        if not OPENBB_AVAILABLE:
            raise ImportError(
                "OpenBB Platform not installed. "
                "Install with: pip install openbb-platform"
            )
        
        self.provider = provider or 'yahoo'  # Default to Yahoo Finance (free)
        self.api_key = api_key or os.getenv('OPENBB_API_KEY')
        
        # Configure OpenBB if API key provided
        if self.api_key:
            try:
                obb.account.login(pat=self.api_key)
            except Exception as e:
                print(f"Warning: Could not login to OpenBB account: {e}")
                print("Continuing with free providers...")
        
        # Set up provider credentials if needed
        self._configure_provider_credentials()
    
    def _configure_provider_credentials(self):
        """Configure credentials for specific providers if available."""
        # Alpha Vantage
        av_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        if av_key:
            try:
                obb.user.credentials.set("alpha_vantage", api_key=av_key)
            except Exception:
                pass
        
        # Polygon.io
        polygon_key = os.getenv('POLYGON_API_KEY')
        if polygon_key:
            try:
                obb.user.credentials.set("polygon", api_key=polygon_key)
            except Exception:
                pass
    
    def get_daily_time_series(
        self, 
        symbol: str, 
        outputsize: str = 'full',
        adjusted: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get daily time series data.
        
        Args:
            symbol: Stock ticker symbol
            outputsize: 'compact' (last 100 data points) or 'full' (up to 20 years)
            adjusted: If True, returns adjusted prices (default: True)
        
        Returns:
            List of daily price data points, sorted by date (newest first)
        """
        try:
            # Use OpenBB to fetch historical prices
            result = obb.equity.price.historical(
                symbol=symbol,
                provider=self.provider
            )
            
            if result is None or result.empty:
                return []
            
            # Transform OpenBB format to our format
            historical_prices = []
            for date, row in result.iterrows():
                historical_prices.append({
                    'date': date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
                    'open': float(row.get('open', 0)),
                    'high': float(row.get('high', 0)),
                    'low': float(row.get('low', 0)),
                    'close': float(row.get('close', 0)),
                    'adjusted_close': float(row.get('close', row.get('close', 0))),  # OpenBB may not have adjusted
                    'volume': int(row.get('volume', 0)),
                    'dividend_amount': 0.0,  # OpenBB may not provide this
                    'split_coefficient': 1.0  # OpenBB may not provide this
                })
            
            # Sort by date (newest first)
            historical_prices.sort(key=lambda x: x['date'], reverse=True)
            
            # Limit to outputsize if needed
            if outputsize == 'compact' and len(historical_prices) > 100:
                historical_prices = historical_prices[:100]
            
            return historical_prices
            
        except Exception as e:
            print(f"Error fetching time series for {symbol}: {e}")
            return []
    
    def get_company_overview(self, symbol: str) -> Dict[str, Any]:
        """
        Get company overview and fundamental data.
        
        Args:
            symbol: Stock ticker symbol
        
        Returns:
            Dictionary with company fundamentals
        """
        try:
            # Get company profile
            profile = obb.equity.profile(symbol, provider=self.provider)
            
            if profile is None or profile.empty:
                return {}
            
            # Get overview data
            overview_data = obb.equity.fundamental.ratios(symbol, provider=self.provider)
            
            # Transform to our format
            overview = {}
            
            # From profile
            if not profile.empty:
                row = profile.iloc[0] if len(profile) > 0 else profile
                overview['Symbol'] = symbol
                overview['Name'] = row.get('name', '')
                overview['Sector'] = row.get('sector', '')
                overview['Industry'] = row.get('industry', '')
                overview['Description'] = row.get('description', '')
                overview['MarketCapitalization'] = row.get('market_cap', None)
            
            # From ratios
            if overview_data is not None and not overview_data.empty:
                row = overview_data.iloc[0] if len(overview_data) > 0 else overview_data
                overview['TrailingPE'] = row.get('pe_ratio', None)
                overview['ForwardPE'] = row.get('forward_pe', None)
                overview['PriceToBookRatio'] = row.get('pb_ratio', None)
                overview['PriceToSalesRatioTTM'] = row.get('ps_ratio', None)
                overview['Beta'] = row.get('beta', None)
            
            return overview
            
        except Exception as e:
            print(f"Error fetching company overview for {symbol}: {e}")
            return {}
    
    def get_income_statement(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Get annual income statements.
        
        Args:
            symbol: Stock ticker symbol
        
        Returns:
            List of annual income statements (most recent first)
        """
        try:
            income_data = obb.equity.fundamental.income(symbol, provider=self.provider)
            
            if income_data is None or income_data.empty:
                return []
            
            # Transform to our format
            statements = []
            for date, row in income_data.iterrows():
                statements.append({
                    'fiscalDateEnding': date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
                    'reportedCurrency': row.get('currency', 'USD'),
                    'totalRevenue': row.get('revenue', 0),
                    'netIncome': row.get('net_income', 0),
                    'grossProfit': row.get('gross_profit', None),
                    'operatingIncome': row.get('operating_income', None),
                    'eps': row.get('eps', None),
                    'epsDiluted': row.get('eps_diluted', None),
                })
            
            # Sort by date (most recent first)
            statements.sort(key=lambda x: x['fiscalDateEnding'], reverse=True)
            return statements
            
        except Exception as e:
            print(f"Error fetching income statement for {symbol}: {e}")
            return []
    
    def get_balance_sheet(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Get annual balance sheets.
        
        Args:
            symbol: Stock ticker symbol
        
        Returns:
            List of annual balance sheets (most recent first)
        """
        try:
            balance_data = obb.equity.fundamental.balance(symbol, provider=self.provider)
            
            if balance_data is None or balance_data.empty:
                return []
            
            # Transform to our format
            statements = []
            for date, row in balance_data.iterrows():
                statements.append({
                    'fiscalDateEnding': date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
                    'reportedCurrency': row.get('currency', 'USD'),
                    'totalAssets': row.get('total_assets', 0),
                    'totalLiabilities': row.get('total_liabilities', 0),
                    'totalShareholderEquity': row.get('total_equity', 0),
                    'commonStock': row.get('common_stock', None),
                    'retainedEarnings': row.get('retained_earnings', None),
                })
            
            # Sort by date (most recent first)
            statements.sort(key=lambda x: x['fiscalDateEnding'], reverse=True)
            return statements
            
        except Exception as e:
            print(f"Error fetching balance sheet for {symbol}: {e}")
            return []
    
    def get_cash_flow(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Get annual cash flow statements.
        
        Args:
            symbol: Stock ticker symbol
        
        Returns:
            List of annual cash flow statements (most recent first)
        """
        try:
            cashflow_data = obb.equity.fundamental.cash_flow(symbol, provider=self.provider)
            
            if cashflow_data is None or cashflow_data.empty:
                return []
            
            # Transform to our format
            statements = []
            for date, row in cashflow_data.iterrows():
                statements.append({
                    'fiscalDateEnding': date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
                    'reportedCurrency': row.get('currency', 'USD'),
                    'operatingCashflow': row.get('operating_cash_flow', 0),
                    'capitalExpenditures': row.get('capital_expenditure', None),
                    'freeCashFlow': row.get('free_cash_flow', None),
                    'cashflowFromInvestment': row.get('investing_cash_flow', None),
                    'cashflowFromFinancing': row.get('financing_cash_flow', None),
                })
            
            # Sort by date (most recent first)
            statements.sort(key=lambda x: x['fiscalDateEnding'], reverse=True)
            return statements
            
        except Exception as e:
            print(f"Error fetching cash flow for {symbol}: {e}")
            return []
    
    def get_global_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get real-time global quote.
        
        Args:
            symbol: Stock ticker symbol
        
        Returns:
            Dictionary with current quote data
        """
        try:
            quote_data = obb.equity.price.quote(symbol, provider=self.provider)
            
            if quote_data is None or quote_data.empty:
                return {}
            
            # Transform to our format
            row = quote_data.iloc[0] if len(quote_data) > 0 else quote_data
            quote = {
                'symbol': symbol,
                'price': float(row.get('price', 0)),
                'change': float(row.get('change', 0)) if row.get('change') is not None else 0,
                'change percent': float(row.get('change_percent', 0)) if row.get('change_percent') is not None else 0,
                'volume': int(row.get('volume', 0)) if row.get('volume') is not None else 0,
                'previous close': float(row.get('previous_close', 0)) if row.get('previous_close') is not None else None,
                'open': float(row.get('open', 0)) if row.get('open') is not None else None,
                'high': float(row.get('high', 0)) if row.get('high') is not None else None,
                'low': float(row.get('low', 0)) if row.get('low') is not None else None,
            }
            
            return quote
            
        except Exception as e:
            print(f"Error fetching quote for {symbol}: {e}")
            return {}
    
    def get_technical_indicators(self, symbol: str) -> Dict[str, Any]:
        """
        Get technical indicators.
        
        Args:
            symbol: Stock ticker symbol
        
        Returns:
            Dictionary with technical indicators
        """
        try:
            indicators = {}
            
            # RSI
            try:
                rsi_data = obb.technical.rsi(symbol, period=14, provider=self.provider)
                if rsi_data is not None and not rsi_data.empty:
                    indicators['rsi'] = float(rsi_data.iloc[-1]) if len(rsi_data) > 0 else None
            except Exception:
                indicators['rsi'] = None
            
            # MACD
            try:
                macd_data = obb.technical.macd(symbol, provider=self.provider)
                if macd_data is not None and not macd_data.empty:
                    row = macd_data.iloc[-1] if len(macd_data) > 0 else macd_data
                    indicators['macd'] = {
                        'macd_line': float(row.get('macd', 0)),
                        'signal_line': float(row.get('signal', 0)),
                        'histogram': float(row.get('histogram', 0))
                    }
            except Exception:
                indicators['macd'] = None
            
            # Moving Averages
            for period in [20, 50, 200]:
                try:
                    sma_data = obb.technical.sma(symbol, period=period, provider=self.provider)
                    if sma_data is not None and not sma_data.empty:
                        indicators[f'sma_{period}'] = float(sma_data.iloc[-1]) if len(sma_data) > 0 else None
                except Exception:
                    indicators[f'sma_{period}'] = None
            
            return indicators
            
        except Exception as e:
            print(f"Error fetching technical indicators for {symbol}: {e}")
            return {}
    
    def get_data(
        self, 
        symbol: str, 
        current_date: str = None,
        include_fundamentals: bool = True,
        include_financials: bool = True
    ) -> Dict[str, Any]:
        """
        Get comprehensive stock data for a symbol.
        
        This is the main method that strategies should use to get all available data.
        
        Args:
            symbol: Stock ticker symbol
            current_date: Current trading date (YYYY-MM-DD). If provided, filters historical data.
            include_fundamentals: If True, fetches company overview
            include_financials: If True, fetches financial statements
        
        Returns:
            Dictionary with all available stock data:
            - historical_prices: List of daily price data
            - current_price: Current stock price
            - company_overview: Fundamental data
            - income_statement: Annual income statements
            - balance_sheet: Annual balance sheets
            - cash_flow: Annual cash flow statements
            - quote: Real-time quote data
            - technical_indicators: Technical indicators (RSI, MACD, etc.)
        """
        result = {
            'symbol': symbol,
            'historical_prices': [],
            'current_price': None,
            'company_overview': {},
            'income_statement': [],
            'balance_sheet': [],
            'cash_flow': [],
            'quote': {},
            'technical_indicators': {}
        }
        
        try:
            # Get daily time series
            historical_prices = self.get_daily_time_series(symbol, outputsize='full', adjusted=True)
            
            # Filter by date if provided
            if current_date:
                filtered_prices = [
                    p for p in historical_prices 
                    if p['date'] <= current_date
                ]
                historical_prices = filtered_prices
            
            result['historical_prices'] = historical_prices
            
            # Get current price from most recent historical data or quote
            if historical_prices:
                result['current_price'] = historical_prices[0].get('adjusted_close') or historical_prices[0].get('close')
            else:
                # Fallback to quote
                quote = self.get_global_quote(symbol)
                result['quote'] = quote
                result['current_price'] = quote.get('price')
            
            # Get fundamentals if requested
            if include_fundamentals:
                try:
                    result['company_overview'] = self.get_company_overview(symbol)
                except Exception as e:
                    print(f"Warning: Could not fetch company overview for {symbol}: {e}")
            
            # Get financial statements if requested
            if include_financials:
                try:
                    result['income_statement'] = self.get_income_statement(symbol)
                    result['balance_sheet'] = self.get_balance_sheet(symbol)
                    result['cash_flow'] = self.get_cash_flow(symbol)
                except Exception as e:
                    print(f"Warning: Could not fetch financial statements for {symbol}: {e}")
            
            # Get technical indicators
            try:
                result['technical_indicators'] = self.get_technical_indicators(symbol)
            except Exception as e:
                print(f"Warning: Could not fetch technical indicators for {symbol}: {e}")
            
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            raise
        
        return result
    
    def get_price_for_date(self, symbol: str, target_date: str) -> Optional[float]:
        """
        Get the closing price for a specific date.
        
        Args:
            symbol: Stock ticker symbol
            target_date: Target date in YYYY-MM-DD format
        
        Returns:
            Closing price for the date, or None if not found
        """
        historical_prices = self.get_daily_time_series(symbol, outputsize='full', adjusted=True)
        
        # Find exact date or latest date on/before target_date
        target_dt = datetime.strptime(target_date, '%Y-%m-%d')
        latest_price = None
        latest_date = None
        
        for price_data in historical_prices:
            price_date = datetime.strptime(price_data['date'], '%Y-%m-%d')
            if price_date <= target_dt:
                if latest_date is None or price_date > latest_date:
                    latest_date = price_date
                    latest_price = price_data.get('adjusted_close') or price_data.get('close')
        
        return latest_price


