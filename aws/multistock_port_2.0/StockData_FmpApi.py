"""
Stock Data API Client for Financial Modeling Prep
================================================

This module provides a client for fetching stock data from Financial Modeling Prep API
with flexible date filtering for both historical backtesting and current predictions.
"""

import os
import json
import requests
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import time
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables at module level from .env in the same directory as this script
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(dotenv_path=env_path)

@dataclass
class StockData:
    """Structured stock data for analysis and prediction"""
    symbol: str
    company_name: str
    sector: str
    current_price: float
    historical_prices: List[Dict]
    price_change_1d: float
    price_change_5d: float
    price_change_1m: float
    volume: int
    avg_volume: int
    market_cap: float
    pe_ratio: float
    eps: float
    beta: float
    dividend_yield: float
    # New fields for financial statements
    income_statement: Optional[List[Dict]] = None
    balance_sheet: Optional[List[Dict]] = None
    cash_flow: Optional[List[Dict]] = None
    # Removed market_indexes field
    sector_performance: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'symbol': self.symbol,
            'company_name': self.company_name,
            'sector': self.sector,
            'current_price': self.current_price,
            'historical_prices': self.historical_prices,
            'price_change_1d': self.price_change_1d,
            'price_change_5d': self.price_change_5d,
            'price_change_1m': self.price_change_1m,
            'volume': self.volume,
            'avg_volume': self.avg_volume,
            'market_cap': self.market_cap,
            'pe_ratio': self.pe_ratio,
            'eps': self.eps,
            'beta': self.beta,
            'dividend_yield': self.dividend_yield,
            'income_statement': self.income_statement,
            'balance_sheet': self.balance_sheet,
            'cash_flow': self.cash_flow,
            'sector_performance': self.sector_performance
        }
    
    def to_prompt_format(self) -> str:
        """Convert stock data to a formatted string for LLM prompts"""
        prompt = f"""
COMPANY: {self.company_name} ({self.symbol})
SECTOR: {self.sector}
CURRENT PRICE: ${self.current_price:.2f}

PRICE MOVEMENT:
- 1 Day: {self.price_change_1d:+.2f}%
- 5 Days: {self.price_change_5d:+.2f}%
- 1 Month: {self.price_change_1m:+.2f}%

TRADING METRICS:
- Volume: {self.volume:,}
- Average Volume: {self.avg_volume:,}
- Market Cap: ${self.market_cap / 1e9:.2f}B

FUNDAMENTALS:
- P/E Ratio: {self.pe_ratio:.2f}
- EPS: ${self.eps:.2f}
- Beta: {self.beta:.2f}
- Dividend Yield: {self.dividend_yield:.2f}%

RECENT PRICE HISTORY:
"""
        # Add recent price history
        recent_prices = sorted(self.historical_prices, key=lambda x: x.get('date', ''), reverse=True)[:5]
        for price_data in recent_prices:
            date = price_data.get('date', 'Unknown')
            close = price_data.get('close', 0)
            change = price_data.get('changePercent', 0)
            prompt += f"- {date}: ${close:.2f} ({change:+.2f}%)\n"

        # Add financial statement summary if available
        if self.income_statement and len(self.income_statement) > 0:
            latest = self.income_statement[0]
            prompt += f"\nFINANCIAL HIGHLIGHTS (Latest Quarter):\n"
            prompt += f"- Revenue: ${latest.get('revenue', 0) / 1e6:.2f}M\n"
            prompt += f"- Net Income: ${latest.get('netIncome', 0) / 1e6:.2f}M\n"
            prompt += f"- Operating Income: ${latest.get('operatingIncome', 0) / 1e6:.2f}M\n"

        return prompt

class StockDataFmpApi:
    """Client for fetching stock data from Financial Modeling Prep API"""
    
    def __init__(self, api_key: str = None):
        """
        Initialize the API client with your FMP API key
        
        Args:
            api_key: FMP API key, if None will try to load from environment variable FMP_API_KEY
        """
        if api_key is None:
            api_key = os.getenv('FMP_API_KEY')
            if not api_key:
                raise ValueError("No API key provided and FMP_API_KEY environment variable not set")
                
        self.api_key = api_key
        self.base_url = "https://financialmodelingprep.com/api/v3"
        
    def _make_request(self, endpoint: str, params: Dict = None) -> Any:
        """Make API request to FMP"""
        url = f"{self.base_url}/{endpoint}"
        
        # Add API key to parameters
        if params is None:
            params = {}
        params['apikey'] = self.api_key
        
        try:
            print(f"Fetching: {url}")
            response = requests.get(url, params=params, timeout=30)
            
            # Handle payment required errors gracefully
            if response.status_code == 402:
                print(f"⚠️  Endpoint requires paid subscription: {endpoint}")
                return []
            
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, list) or isinstance(data, dict):
                return data
            else:
                print(f"Unexpected response format: {type(data)}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return []
    
    def get_company_profile(self, symbol: str) -> Dict:
        """Get company profile data"""
        endpoint = f"profile/{symbol}"  # Updated endpoint format
        data = self._make_request(endpoint)
        return data[0] if data and isinstance(data, list) and len(data) > 0 else {}
    
    def get_quote(self, symbol: str) -> Dict:
        """Get current stock quote"""
        endpoint = f"quote/{symbol}"  # Updated to include symbol in endpoint
        data = self._make_request(endpoint)
        return data[0] if data and isinstance(data, list) and len(data) > 0 else {}
    
    def get_historical_price(
        self, 
        symbol: str, 
        from_date: str = None, 
        to_date: str = None, 
        timeseries: int = None
    ) -> List[Dict]:
        """
        Get historical stock prices (limited to 8 months)
        
        Args:
            symbol: Stock ticker symbol
            from_date: Start date in YYYY-MM-DD format
            to_date: End date in YYYY-MM-DD format
            timeseries: Number of data points (alternative to date range)
            
        Returns:
            List of historical price data points
        """
        endpoint = f"historical-price-full/{symbol}"
        params = {}
        
        # Limit historical data to 8 months (approximately 240 days)
        if timeseries and timeseries > 240:
            timeseries = 240
        
        # Use either date range or timeseries
        if from_date and to_date:
            params['from'] = from_date
            params['to'] = to_date
        elif timeseries:
            params['timeseries'] = timeseries
        else:
            # Default to 8 months if no parameters provided
            params['timeseries'] = 240
        
        data = self._make_request(endpoint, params)
        
        # Extract historical data from response
        if isinstance(data, dict) and 'historical' in data:
            return data['historical']
        return []
    
    def get_key_metrics(self, symbol: str, period: str = 'annual', limit: int = 1) -> List[Dict]:
        """
        Get key financial metrics
        
        Args:
            symbol: Stock ticker symbol
            period: 'annual' or 'quarter'
            limit: Number of periods to return
            
        Returns:
            List of financial metrics by period
        """
        endpoint = "key-metrics"
        params = {
            'symbol': symbol,
            'period': period,
            'limit': limit
        }
        return self._make_request(endpoint, params)
    
    def get_ratios(self, symbol: str, period: str = 'annual', limit: int = 1) -> List[Dict]:
        """
        Get financial ratios
        
        Args:
            symbol: Stock ticker symbol
            period: 'annual' or 'quarter'
            limit: Number of periods to return
            
        Returns:
            List of financial ratios by period
        """
        endpoint = "ratios"
        params = {
            'symbol': symbol,
            'period': period,
            'limit': limit
        }
        return self._make_request(endpoint, params)
    
    def get_news(self, symbol: str = None, limit: int = 10) -> List[Dict]:
        """
        Get news articles for a specific stock or general market news
        
        Args:
            symbol: Stock ticker symbol (optional, if None returns general market news)
            limit: Number of news items to return
            
        Returns:
            List of news articles
        """
        if symbol:
            endpoint = f"stock_news"
            params = {'symbol': symbol, 'limit': limit}
        else:
            endpoint = f"stock_news"
            params = {'limit': limit}
        
        return self._make_request(endpoint, params)
    
    def get_earnings_calendar(
        self, 
        from_date: str = None, 
        to_date: str = None
    ) -> List[Dict]:
        """
        Get earnings calendar for specified date range
        
        Args:
            from_date: Start date in YYYY-MM-DD format
            to_date: End date in YYYY-MM-DD format
            
        Returns:
            List of upcoming earnings releases
        """
        endpoint = "earning-calendar"
        params = {}
        
        if from_date:
            params['from'] = from_date
        if to_date:
            params['to'] = to_date
            
        return self._make_request(endpoint, params)
    
    def get_sector_performance(self) -> List[Dict]:
        """Get performance data for market sectors"""
        endpoint = "sector-performance"
        return self._make_request(endpoint)
    
    def get_income_statement(self, symbol: str, period: str = 'quarter', limit: int = 4) -> List[Dict]:
        """
        Get income statement data
        
        Args:
            symbol: Stock ticker symbol
            period: 'quarter' or 'annual'
            limit: Number of periods to return
            
        Returns:
            List of income statements
        """
        endpoint = f"income-statement/{symbol}"
        params = {
            'period': period,
            'limit': limit
        }
        return self._make_request(endpoint, params)
    
    def get_balance_sheet(self, symbol: str, period: str = 'quarter', limit: int = 4) -> List[Dict]:
        """
        Get balance sheet data
        
        Args:
            symbol: Stock ticker symbol
            period: 'quarter' or 'annual'
            limit: Number of periods to return
            
        Returns:
            List of balance sheets
        """
        endpoint = f"balance-sheet-statement/{symbol}"
        params = {
            'period': period,
            'limit': limit
        }
        return self._make_request(endpoint, params)
    
    def get_cash_flow(self, symbol: str, period: str = 'quarter', limit: int = 4) -> List[Dict]:
        """
        Get cash flow statement data
        
        Args:
            symbol: Stock ticker symbol
            period: 'quarter' or 'annual'
            limit: Number of periods to return
            
        Returns:
            List of cash flow statements
        """
        endpoint = f"cash-flow-statement/{symbol}"
        params = {
            'period': period,
            'limit': limit
        }
        return self._make_request(endpoint, params)

    def fetch_financial_statements(self, symbol: str, period: str = 'quarter', limit: int = 4) -> Dict[str, List[Dict]]:
        """
        Fetch all financial statements (income, balance sheet, cash flow)
        
        Args:
            symbol: Stock ticker symbol
            period: 'quarter' or 'annual'
            limit: Number of periods to return
            
        Returns:
            Dictionary containing all financial statements
        """
        return {
            'income_statement': self.get_income_statement(symbol, period, limit),
            'balance_sheet': self.get_balance_sheet(symbol, period, limit),
            'cash_flow': self.get_cash_flow(symbol, period, limit)
        }

    def fetch_stock_data(
        self, 
        symbol: str,
        historical_days: int = 240,  # Changed default to 8 months
        from_date: str = None,
        to_date: str = None,
        include_financials: bool = True
    ) -> Optional[StockData]:
        """
        Fetch complete stock data for a single stock
        
        Args:
            symbol: Stock ticker symbol
            historical_days: Number of days of historical data to fetch (max 240)
            from_date: Start date for historical data in YYYY-MM-DD format
            to_date: End date for historical data in YYYY-MM-DD format
            include_financials: Whether to include financial statements
            
        Returns:
            StockData object or None if data couldn't be fetched
        """
        try:
            # Limit historical days to 8 months
            if historical_days > 240:
                historical_days = 240

            # Get company profile
            profile = self.get_company_profile(symbol)
            if not profile:
                print(f"❌ Could not fetch company profile for {symbol}")
                return None
            
            # Get current quote
            quote = self.get_quote(symbol)
            if not quote:
                print(f"❌ Could not fetch current quote for {symbol}")
                return None
            
            # Get historical price data with date filtering
            historical_prices = []
            if from_date and to_date:
                historical_prices = self.get_historical_price(symbol, from_date, to_date)
            else:
                historical_prices = self.get_historical_price(symbol, timeseries=historical_days)
            
            if not historical_prices:
                print(f"❌ Could not fetch historical prices for {symbol}")
                return None
            
            # Sort historical prices by date (newest first)
            historical_prices = sorted(historical_prices, key=lambda x: x.get('date', ''), reverse=True)
            
            # Calculate price changes
            current_price = quote.get('price', 0)
            
            # Calculate price changes if we have enough historical data
            price_change_1d = quote.get('changesPercentage', 0)
            price_change_5d = 0
            price_change_1m = 0
            
            if len(historical_prices) >= 5:
                price_5d_ago = historical_prices[4].get('close', current_price)
                if price_5d_ago > 0:
                    price_change_5d = ((current_price - price_5d_ago) / price_5d_ago) * 100
            
            if len(historical_prices) >= 20:
                price_1m_ago = historical_prices[19].get('close', current_price)
                if price_1m_ago > 0:
                    price_change_1m = ((current_price - price_1m_ago) / price_1m_ago) * 100
            
            # Get key metrics
            metrics = self.get_key_metrics(symbol, 'quarter', 1)
            metrics_data = metrics[0] if metrics and len(metrics) > 0 else {}
            
            # Get financial ratios
            ratios = self.get_ratios(symbol, 'quarter', 1)
            ratios_data = ratios[0] if ratios and len(ratios) > 0 else {}
            
            # Extract and calculate additional metrics
            market_cap = quote.get('marketCap', 0)
            volume = quote.get('volume', 0)
            avg_volume = quote.get('avgVolume', 0)
            pe_ratio = quote.get('pe', 0)
            eps = quote.get('eps', 0)
            
            # Try to get beta and dividend yield from different sources
            beta = profile.get('beta', 0)
            if beta == 0:
                beta = ratios_data.get('beta', 0)
            
            dividend_yield = quote.get('dividendYield', 0) * 100  # Convert to percentage
            if dividend_yield == 0:
                dividend_yield = ratios_data.get('dividendYield', 0) * 100

            # Get financial statements if requested
            income_statement = None
            balance_sheet = None
            cash_flow = None
            if include_financials:
                financials = self.fetch_financial_statements(symbol)
                income_statement = financials['income_statement']
                balance_sheet = financials['balance_sheet']
                cash_flow = financials['cash_flow']

            # Get sector performance
            sector_performance = self.get_sector_performance()
            
            # Create StockData object
            return StockData(
                symbol=symbol,
                company_name=profile.get('companyName', symbol),
                sector=profile.get('sector', 'Unknown'),
                current_price=current_price,
                historical_prices=historical_prices,
                price_change_1d=price_change_1d,
                price_change_5d=price_change_5d,
                price_change_1m=price_change_1m,
                volume=volume,
                avg_volume=avg_volume,
                market_cap=market_cap,
                pe_ratio=pe_ratio,
                eps=eps,
                beta=beta,
                dividend_yield=dividend_yield,
                income_statement=income_statement,
                balance_sheet=balance_sheet,
                cash_flow=cash_flow,
                sector_performance=sector_performance
            )
            
        except Exception as e:
            print(f"❌ Error fetching stock data for {symbol}: {e}")
            return None
    
    def fetch_batch_stock_data(
        self, 
        symbols: List[str], 
        historical_days: int = 240,
        from_date: str = None,
        to_date: str = None,
        delay: float = 0.5
    ) -> Dict[str, StockData]:
        """
        Fetch stock data for multiple stocks
        
        Args:
            symbols: List of stock ticker symbols
            historical_days: Number of days of historical data to fetch (max 240)
            from_date: Start date for historical data in YYYY-MM-DD format
            to_date: End date for historical data in YYYY-MM-DD format
            delay: Delay between API calls in seconds
            
        Returns:
            Dictionary of StockData objects keyed by symbol
        """
        results = {}
        
        for symbol in symbols:
            print(f"Fetching stock data for {symbol}...")
            data = self.fetch_stock_data(symbol, historical_days, from_date, to_date)
            if data:
                results[symbol] = data
                print(f"✅ Successfully fetched stock data for {symbol}")
            else:
                print(f"❌ Failed to fetch stock data for {symbol}")
            
            time.sleep(delay)  # Rate limiting
        
        return results

def save_stock_data(data: Dict[str, StockData], output_file: str = "stock_data.json"):
    """
    Save stock data to a JSON file
    
    Args:
        data: Dictionary of StockData objects
        output_file: Path to output file
    """
    output = {}
    
    for symbol, stock_data in data.items():
        output[symbol] = stock_data.to_dict()
    
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"💾 Stock data saved to {output_file}")

def load_stock_data(input_file: str = "stock_data.json") -> Dict[str, StockData]:
    """Load stock data from a JSON file"""
    if not os.path.exists(input_file):
        print(f"❌ Stock data file {input_file} not found")
        return {}
    
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    results = {}
    for symbol, stock_dict in data.items():
        results[symbol] = StockData(**stock_dict)
    
    print(f"📊 Loaded stock data for {len(results)} symbols from {input_file}")
    return results

def get_api_key(key_name: str) -> str:
    """
    Get API key from environment variables
    
    Args:
        key_name: Name of the API key (FMP_API_KEY, OPENAI_API_KEY, etc.)
        
    Returns:
        API key string or None if not found
    """
    return os.environ.get(key_name)

def main():
    """Main function to fetch stock data with command-line arguments"""
    import argparse
    
    # Load environment variables
    # .env already loaded at module level
    
    # Debug: Print API key (first few characters)
    api_key = os.getenv('FMP_API_KEY')
    if api_key:
        print(f"API Key loaded (first 5 chars): {api_key[:5]}...")
    else:
        print("❌ No API key found in environment")
    
    parser = argparse.ArgumentParser(description="Fetch stock data from Financial Modeling Prep API")
    parser.add_argument("--symbols", nargs="+", help="Stock symbols to fetch")
    parser.add_argument("--days", type=int, default=30, help="Number of days of historical data (default: 30)")
    parser.add_argument("--from-date", help="Start date in YYYY-MM-DD format")
    parser.add_argument("--to-date", help="End date in YYYY-MM-DD format")
    parser.add_argument("--output", default="stock_data.json", help="Output file (default: stock_data.json)")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between API calls in seconds (default: 0.5)")
    # New arguments for financial and market data
    parser.add_argument("--no-financials", action="store_true", help="Skip collecting financial statement data")
    parser.add_argument("--no-market-data", action="store_true", help="Skip collecting market and sector data")
    
    args = parser.parse_args()
    
    # Get API key from environment
    api_key = os.getenv('FMP_API_KEY')
    if not api_key:
        print("❌ FMP_API_KEY environment variable not set")
        print("Please set your API key: export FMP_API_KEY='your_api_key'")
        return
    
    # Initialize API client
    client = StockDataFmpApi(api_key)
    
    # Check if symbols are provided
    if not args.symbols:
        print("❌ No stock symbols provided")
        print("Usage: python StockData_FmpApi.py --symbols AAPL MSFT GOOGL")
        return
    
    # Fetch stock data
    print(f"🔍 Fetching stock data for {len(args.symbols)} symbols...")
    
    # Use date range or days
    from_date = args.from_date
    to_date = args.to_date
    historical_days = args.days if not (from_date and to_date) else None
    
    if from_date and to_date:
        print(f"📅 Date range: {from_date} to {to_date}")
    else:
        print(f"📅 Historical days: {historical_days}")
    
    data = client.fetch_batch_stock_data(
        args.symbols,
        historical_days=historical_days,
        from_date=from_date,
        to_date=to_date,
        delay=args.delay
    )
    
    # Save to file
    save_stock_data(data, args.output)
    
    # Print summary
    print("\n📊 Stock Data Summary:")
    print("=" * 50)
    
    for symbol, stock_data in data.items():
        print(f"\n{stock_data.company_name} ({symbol}) - ${stock_data.current_price:.2f}")
        print(f"Sector: {stock_data.sector}")
        print(f"Price Change (1D): {stock_data.price_change_1d:+.2f}%")
        print(f"Price Change (5D): {stock_data.price_change_5d:+.2f}%")
        print(f"Price Change (1M): {stock_data.price_change_1m:+.2f}%")
        print(f"Market Cap: ${stock_data.market_cap / 1e9:.2f}B")
        print(f"P/E Ratio: {stock_data.pe_ratio:.2f}")
        
        # Print financial highlights if available
        if stock_data.income_statement and len(stock_data.income_statement) > 0:
            latest = stock_data.income_statement[0]
            print(f"Latest Quarter Revenue: ${latest.get('revenue', 0) / 1e6:.2f}M")
            print(f"Latest Quarter Net Income: ${latest.get('netIncome', 0) / 1e6:.2f}M")
        
        print("-" * 50)

if __name__ == "__main__":
    main()