"""
Alpha Vantage Data Provider

Default data provider for fetching stock data from Alpha Vantage API.
Provides historical prices, fundamentals, financial statements, and real-time quotes.

API Documentation: https://www.alphavantage.co/documentation/
"""

import os
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import time
from dotenv import load_dotenv

load_dotenv()


class AlphaVantageProvider:
    """
    Data provider for Alpha Vantage API.
    
    This is the default data provider for the backtesting infrastructure.
    It fetches stock data including prices, fundamentals, and financial statements.
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize Alpha Vantage provider.
        
        Args:
            api_key: Alpha Vantage API key. If None, loads from ALPHA_VANTAGE_API_KEY env var.
        """
        if api_key is None:
            api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
            if not api_key:
                raise ValueError(
                    "No API key provided and ALPHA_VANTAGE_API_KEY environment variable not set. "
                    "Get a free API key at https://www.alphavantage.co/support/#api-key"
                )
        
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        self.rate_limit_delay = 12.0  # Alpha Vantage free tier: 5 calls/min, 500/day
        
    def _make_request(self, function: str, symbol: str, **params) -> Dict[str, Any]:
        """
        Make API request to Alpha Vantage.
        
        Args:
            function: API function name (e.g., 'TIME_SERIES_DAILY')
            symbol: Stock ticker symbol
            **params: Additional API parameters
        
        Returns:
            API response as dictionary
        """
        url = self.base_url
        request_params = {
            'function': function,
            'symbol': symbol,
            'apikey': self.api_key,
            **params
        }
        
        try:
            response = requests.get(url, params=request_params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Check for API errors
            if 'Error Message' in data:
                raise ValueError(f"Alpha Vantage API Error: {data['Error Message']}")
            if 'Note' in data:
                # Rate limit message
                raise ValueError(f"Alpha Vantage Rate Limit: {data['Note']}")
            
            return data
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Alpha Vantage API request failed: {e}")
    
    def _rate_limit(self):
        """Apply rate limiting for free tier (5 calls per minute)"""
        time.sleep(self.rate_limit_delay)
    
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
        function = 'TIME_SERIES_DAILY_ADJUSTED' if adjusted else 'TIME_SERIES_DAILY'
        
        data = self._make_request(function, symbol, outputsize=outputsize)
        self._rate_limit()  # Rate limit after each call
        
        # Extract time series data
        time_series_key = 'Time Series (Daily)' if not adjusted else 'Time Series (Daily Adjusted)'
        
        if time_series_key not in data:
            return []
        
        time_series = data[time_series_key]
        historical_prices = []
        
        for date_str, price_data in time_series.items():
            historical_prices.append({
                'date': date_str,
                'open': float(price_data.get('1. open', 0)),
                'high': float(price_data.get('2. high', 0)),
                'low': float(price_data.get('3. low', 0)),
                'close': float(price_data.get('4. close', 0)),
                'adjusted_close': float(price_data.get('5. adjusted close', price_data.get('4. close', 0))),
                'volume': int(price_data.get('6. volume', 0)),
                'dividend_amount': float(price_data.get('7. dividend amount', 0)),
                'split_coefficient': float(price_data.get('8. split coefficient', 1.0))
            })
        
        # Sort by date (newest first)
        historical_prices.sort(key=lambda x: x['date'], reverse=True)
        return historical_prices
    
    def get_company_overview(self, symbol: str) -> Dict[str, Any]:
        """
        Get company overview and fundamental data.
        
        Args:
            symbol: Stock ticker symbol
        
        Returns:
            Dictionary with company fundamentals
        """
        data = self._make_request('OVERVIEW', symbol)
        self._rate_limit()
        
        # Convert string values to appropriate types
        overview = {}
        for key, value in data.items():
            if value == 'None' or value == 'None.' or value == '':
                overview[key] = None
            elif key in ['MarketCapitalization', 'EBITDA', 'RevenueTTM', 'GrossProfitTTM',
                        'DilutedEPSTTM', 'QuarterlyEarningsGrowthYOY', 'QuarterlyRevenueGrowthYOY',
                        'TrailingPE', 'ForwardPE', 'PriceToSalesRatioTTM', 'PriceToBookRatio',
                        'EVToRevenue', 'EVToEBITDA', 'Beta', '52WeekHigh', '52WeekLow',
                        '50DayMovingAverage', '200DayMovingAverage', 'SharesOutstanding']:
                try:
                    overview[key] = float(value) if value else None
                except (ValueError, TypeError):
                    overview[key] = None
            elif key in ['DividendDate', 'ExDividendDate', 'LatestQuarter']:
                overview[key] = value if value else None
            else:
                overview[key] = value
        
        return overview
    
    def get_income_statement(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Get annual income statements.
        
        Args:
            symbol: Stock ticker symbol
        
        Returns:
            List of annual income statements (most recent first)
        """
        data = self._make_request('INCOME_STATEMENT', symbol)
        self._rate_limit()
        
        if 'annualReports' not in data:
            return []
        
        return data['annualReports']
    
    def get_balance_sheet(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Get annual balance sheets.
        
        Args:
            symbol: Stock ticker symbol
        
        Returns:
            List of annual balance sheets (most recent first)
        """
        data = self._make_request('BALANCE_SHEET', symbol)
        self._rate_limit()
        
        if 'annualReports' not in data:
            return []
        
        return data['annualReports']
    
    def get_cash_flow(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Get annual cash flow statements.
        
        Args:
            symbol: Stock ticker symbol
        
        Returns:
            List of annual cash flow statements (most recent first)
        """
        data = self._make_request('CASH_FLOW', symbol)
        self._rate_limit()
        
        if 'annualReports' not in data:
            return []
        
        return data['annualReports']
    
    def get_global_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get real-time global quote.
        
        Args:
            symbol: Stock ticker symbol
        
        Returns:
            Dictionary with current quote data
        """
        data = self._make_request('GLOBAL_QUOTE', symbol)
        self._rate_limit()
        
        if 'Global Quote' not in data:
            return {}
        
        quote = data['Global Quote']
        
        # Parse quote data
        parsed_quote = {}
        for key, value in quote.items():
            # Remove prefix "01. " or "02. " etc.
            clean_key = key.split('. ', 1)[-1] if '. ' in key else key
            
            # Convert numeric values
            if clean_key in ['price', 'change', 'change percent', 'volume', 'previous close',
                           'open', 'high', 'low']:
                try:
                    # Remove % sign and convert
                    clean_value = value.replace('%', '') if isinstance(value, str) else value
                    parsed_quote[clean_key] = float(clean_value) if clean_value else None
                except (ValueError, TypeError):
                    parsed_quote[clean_key] = None
            else:
                parsed_quote[clean_key] = value
        
        return parsed_quote
    
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
        """
        result = {
            'symbol': symbol,
            'historical_prices': [],
            'current_price': None,
            'company_overview': {},
            'income_statement': [],
            'balance_sheet': [],
            'cash_flow': [],
            'quote': {}
        }
        
        try:
            # Get daily time series (most important)
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

