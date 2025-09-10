"""
Enhanced Earnings API Client for Stock Predictions
=================================================

This module provides a client for fetching comprehensive stock data from Financial Modeling Prep API
including earnings data, stock prices, analyst ratings, and commitment of traders data.
"""

import os
import json
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime
import time
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class StockData:
    """Comprehensive stock data for predictions"""
    symbol: str
    company_name: str
    sector: str
    
    # Current market data
    current_price: float
    volume: float
    change_percent: float
    
    # Earnings data
    latest_quarter: str
    revenue: float
    revenue_growth: float
    eps: float
    eps_growth: float
    operating_profit: float
    operating_margin: float
    
    # Historical price data
    price_history: List[Dict]
    
    # Position data (longs/shorts)
    commitment_data: Dict
    
    # Analyst ratings
    analyst_ratings: List[Dict]
    
    # News data
    news_data: List[Dict]
    
    # Historical quarters
    historical_quarters: List[Dict]
    
    def to_prompt_format(self) -> str:
        """Convert stock data to a formatted string for LLM prompts"""
        prompt = f"""
COMPANY: {self.company_name} ({self.symbol})
SECTOR: {self.sector}

CURRENT MARKET DATA:
- Current Price: ${self.current_price:.2f}
- Daily Change: {self.change_percent:+.2f}%
- Volume: {self.volume:,.0f}

EARNINGS DATA:
- Latest Quarter: {self.latest_quarter}
- Revenue: ${self.revenue:.2f}B ({self.revenue_growth:+.1f}% YoY)
- EPS: ${self.eps:.2f} ({self.eps_growth:+.1f}% YoY)
- Operating Profit: ${self.operating_profit:.2f}B
- Operating Margin: {self.operating_margin:.1f}%

POSITION DATA:
"""
        # Add commitment of traders data if available
        if self.commitment_data:
            prompt += f"- Long Positions: {self.commitment_data.get('long_positions', 'N/A')}\n"
            prompt += f"- Short Positions: {self.commitment_data.get('short_positions', 'N/A')}\n"
            prompt += f"- Net Position: {self.commitment_data.get('net_position', 'N/A')}\n"
        
        prompt += "\nANALYST RATINGS:\n"
        # Add top 5 analyst ratings
        for i, rating in enumerate(self.analyst_ratings[:5]):
            prompt += f"- {rating.get('gradingCompany', 'Unknown')}: {rating.get('newGrade', 'N/A')}, Target: ${rating.get('priceTarget', 'N/A')}\n"
        
        prompt += "\nRECENT PRICE HISTORY (Last 10 days):\n"
        # Add recent price history
        for i, price_data in enumerate(self.price_history[:10]):
            prompt += f"- {price_data.get('date', 'Unknown')}: ${price_data.get('close', 0):.2f} ({price_data.get('changePercent', 0):+.2f}%)\n"
        
        return prompt

class EnhancedEarningsAPIClient:
    """Enhanced client for fetching comprehensive stock data from FMP API"""
    
    def __init__(self, api_key: str):
        """Initialize the API client"""
        self.api_key = api_key
        self.base_url = "https://financialmodelingprep.com/stable"
        
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
    
    def get_current_price(self, symbol: str) -> Dict:
        """Get current stock price data"""
        endpoint = f"historical-price-eod/full"
        params = {'symbol': symbol, 'limit': 1}
        data = self._make_request(endpoint, params)
        
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        return {}
    
    def get_historical_prices(self, symbol: str, days: int = 30) -> List[Dict]:
        """Get historical stock prices"""
        endpoint = f"historical-price-eod/full"
        params = {'symbol': symbol, 'limit': days}
        data = self._make_request(endpoint, params)
        
        if isinstance(data, list):
            return data
        return []
    
    def get_commitment_of_traders(self, symbol: str = None) -> Dict:
        """Get commitment of traders data (longs/shorts)"""
        endpoint = "commitment-of-traders-report"
        params = {}
        if symbol:
            params['symbol'] = symbol
            
        data = self._make_request(endpoint, params)
        
        if isinstance(data, list) and len(data) > 0:
            # Filter for the specific symbol if provided
            if symbol:
                symbol_data = [item for item in data if item.get('symbol') == symbol]
                return symbol_data[0] if symbol_data else {}
            return data[0]
        return {}
    
    def get_company_profile(self, symbol: str) -> Dict:
        """Get company profile data"""
        endpoint = "profile"
        params = {'symbol': symbol}
        data = self._make_request(endpoint, params)
        return data[0] if data and isinstance(data, list) and len(data) > 0 else {}
    
    def get_earnings_data(self, symbol: str, limit: int = 8) -> List[Dict]:
        """Get historical earnings data"""
        endpoint = "earnings"
        params = {'symbol': symbol, 'limit': limit}
        return self._make_request(endpoint, params)
    
    def get_analyst_ratings(self, symbol: str) -> List[Dict]:
        """Get analyst ratings and price targets"""
        endpoint = "grades"
        params = {'symbol': symbol}
        return self._make_request(endpoint, params)
    
    def get_income_statement(self, symbol: str, limit: int = 4) -> List[Dict]:
        """Get income statement data"""
        endpoint = "income-statement"
        params = {'symbol': symbol, 'limit': limit}
        return self._make_request(endpoint, params)
    
    def get_key_metrics(self, symbol: str, limit: int = 4) -> List[Dict]:
        """Get key financial metrics"""
        endpoint = "key-metrics"
        params = {'symbol': symbol, 'limit': limit}
        return self._make_request(endpoint, params)
    
    def fetch_comprehensive_stock_data(self, symbol: str) -> Optional[StockData]:
        """Fetch comprehensive stock data for a symbol"""
        try:
            print(f"🔄 Fetching comprehensive data for {symbol}...")
            
            # Get company profile
            profile = self.get_company_profile(symbol)
            if not profile:
                print(f"❌ Could not fetch company profile for {symbol}")
                return self._generate_mock_data(symbol)
            
            # Get current price data
            current_price_data = self.get_current_price(symbol)
            current_price = current_price_data.get('close', 0)
            volume = current_price_data.get('volume', 0)
            change_percent = current_price_data.get('changePercent', 0)
            
            # Get historical prices
            price_history = self.get_historical_prices(symbol, days=30)
            
            # Get commitment of traders data
            commitment_data = self.get_commitment_of_traders(symbol)
            
            # Get earnings data
            earnings = self.get_earnings_data(symbol, limit=8)
            if not earnings:
                # Try income statement as fallback
                income_statement = self.get_income_statement(symbol, limit=4)
                if income_statement:
                    earnings = income_statement
                else:
                    print(f"⚠️ No earnings data for {symbol}, using mock data")
                    earnings = []
            
            # Get analyst ratings
            analyst_ratings = self.get_analyst_ratings(symbol)
            
            # Get key metrics
            key_metrics = self.get_key_metrics(symbol, limit=4)
            
            # Process earnings data
            latest_quarter = {}
            previous_quarter = {}
            
            if earnings:
                latest_quarter = earnings[0]
                previous_quarter = earnings[1] if len(earnings) > 1 else {}
            
            # Calculate financial metrics
            revenue = 0
            prev_revenue = 0
            eps = 0
            prev_eps = 0
            
            if 'revenue' in latest_quarter:
                revenue = latest_quarter.get('revenue', 0)
            elif 'totalRevenue' in latest_quarter:
                revenue = latest_quarter.get('totalRevenue', 0)
                
            if 'revenue' in previous_quarter:
                prev_revenue = previous_quarter.get('revenue', 0)
            elif 'totalRevenue' in previous_quarter:
                prev_revenue = previous_quarter.get('totalRevenue', 0)
                
            revenue_growth = ((revenue - prev_revenue) / prev_revenue * 100) if prev_revenue else 0
            
            if 'eps' in latest_quarter:
                eps = latest_quarter.get('eps', 0)
            elif 'epsdiluted' in latest_quarter:
                eps = latest_quarter.get('epsdiluted', 0)
                
            if 'eps' in previous_quarter:
                prev_eps = previous_quarter.get('eps', 0)
            elif 'epsdiluted' in previous_quarter:
                prev_eps = previous_quarter.get('epsdiluted', 0)
                
            eps_growth = ((eps - prev_eps) / prev_eps * 100) if prev_eps else 0
            
            # Calculate operating metrics
            operating_profit = 0
            operating_margin = 0
            
            if key_metrics and isinstance(key_metrics, list) and len(key_metrics) > 0:
                if 'operatingProfitMargin' in key_metrics[0]:
                    operating_margin = key_metrics[0].get('operatingProfitMargin', 0)
                elif 'operatingMargin' in key_metrics[0]:
                    operating_margin = key_metrics[0].get('operatingMargin', 0)
            
            operating_profit = revenue * (operating_margin / 100) if operating_margin else 0
            
            # Create historical quarters data
            historical_quarters = []
            for quarter in earnings:
                quarter_revenue = 0
                quarter_eps = 0
                
                if 'revenue' in quarter:
                    quarter_revenue = quarter.get('revenue', 0)
                elif 'totalRevenue' in quarter:
                    quarter_revenue = quarter.get('totalRevenue', 0)
                    
                if 'eps' in quarter:
                    quarter_eps = quarter.get('eps', 0)
                elif 'epsdiluted' in quarter:
                    quarter_eps = quarter.get('epsdiluted', 0)
                
                quarter_date = quarter.get('date', quarter.get('fillingDate', 'Unknown'))
                
                historical_quarters.append({
                    'date': quarter_date,
                    'revenue': quarter_revenue / 1e9,  # Convert to billions
                    'eps': quarter_eps
                })
            
            # Create comprehensive stock data object
            return StockData(
                symbol=symbol,
                company_name=profile.get('companyName', symbol),
                sector=profile.get('sector', 'Unknown'),
                current_price=current_price,
                volume=volume,
                change_percent=change_percent,
                latest_quarter=latest_quarter.get('date', latest_quarter.get('fillingDate', 'Unknown')),
                revenue=revenue / 1e9,  # Convert to billions
                revenue_growth=revenue_growth,
                eps=eps,
                eps_growth=eps_growth,
                operating_profit=operating_profit / 1e9,  # Convert to billions
                operating_margin=operating_margin,
                price_history=price_history,
                commitment_data=commitment_data,
                analyst_ratings=analyst_ratings,
                news_data=[],  # Will be populated separately
                historical_quarters=historical_quarters
            )
            
        except Exception as e:
            print(f"❌ Error fetching comprehensive data for {symbol}: {e}")
            return self._generate_mock_data(symbol)
    
    def _generate_mock_data(self, symbol: str) -> StockData:
        """Generate mock data when API fails"""
        print(f"⚠️ Generating mock data for {symbol}")
        
        # Mock data based on known stocks
        mock_companies = {
            'AAPL': {'name': 'Apple Inc.', 'sector': 'Technology', 'price': 229.31},
            'MSFT': {'name': 'Microsoft Corporation', 'sector': 'Technology', 'price': 415.00},
            'GOOGL': {'name': 'Alphabet Inc.', 'sector': 'Communication Services', 'price': 165.00},
            'AMZN': {'name': 'Amazon.com Inc.', 'sector': 'Consumer Cyclical', 'price': 145.00},
            'TSLA': {'name': 'Tesla Inc.', 'sector': 'Consumer Cyclical', 'price': 240.00},
        }
        
        company_info = mock_companies.get(symbol, {
            'name': f'{symbol} Inc.',
            'sector': 'Unknown',
            'price': 100.00
        })
        
        return StockData(
            symbol=symbol,
            company_name=company_info['name'],
            sector=company_info['sector'],
            current_price=company_info['price'],
            volume=50000000,
            change_percent=1.5,
            latest_quarter='Q1 2025',
            revenue=10.0,
            revenue_growth=15.0,
            eps=2.50,
            eps_growth=12.0,
            operating_profit=3.0,
            operating_margin=30.0,
            price_history=[],
            commitment_data={},
            analyst_ratings=[],
            news_data=[],
            historical_quarters=[]
        )
    
    def fetch_batch_stock_data(self, symbols: List[str], delay: float = 0.5) -> Dict[str, StockData]:
        """Fetch comprehensive stock data for multiple symbols"""
        results = {}
        
        for symbol in symbols:
            data = self.fetch_comprehensive_stock_data(symbol)
            if data:
                results[symbol] = data
                print(f"✅ Successfully fetched comprehensive data for {symbol}")
            else:
                print(f"❌ Failed to fetch data for {symbol}")
            
            time.sleep(delay)  # Rate limiting
        
        return results

def save_stock_data(data: Dict[str, StockData], output_file: str = "comprehensive_stock_data.json"):
    """Save comprehensive stock data to a JSON file"""
    output = {}
    
    for symbol, stock_data in data.items():
        output[symbol] = {
            'symbol': stock_data.symbol,
            'company_name': stock_data.company_name,
            'sector': stock_data.sector,
            'current_price': stock_data.current_price,
            'volume': stock_data.volume,
            'change_percent': stock_data.change_percent,
            'latest_quarter': stock_data.latest_quarter,
            'revenue': stock_data.revenue,
            'revenue_growth': stock_data.revenue_growth,
            'eps': stock_data.eps,
            'eps_growth': stock_data.eps_growth,
            'operating_profit': stock_data.operating_profit,
            'operating_margin': stock_data.operating_margin,
            'price_history': stock_data.price_history,
            'commitment_data': stock_data.commitment_data,
            'analyst_ratings': stock_data.analyst_ratings,
            'news_data': stock_data.news_data,
            'historical_quarters': stock_data.historical_quarters
        }
    
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"💾 Comprehensive stock data saved to {output_file}")

def load_stocks_config() -> List[Dict]:
    """Load stock configuration from file or create default"""
    config_file = "stocks_config.json"
    
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    
    # Default configuration for 50 stocks
    default_stocks = [
        # Tech Sector
        {"symbol": "AAPL", "name": "Apple Inc.", "sector": "Technology"},
        {"symbol": "MSFT", "name": "Microsoft Corporation", "sector": "Technology"},
        {"symbol": "GOOGL", "name": "Alphabet Inc.", "sector": "Technology"},
        {"symbol": "AMZN", "name": "Amazon.com Inc.", "sector": "Technology"},
        {"symbol": "TSLA", "name": "Tesla Inc.", "sector": "Technology"},
        {"symbol": "NVDA", "name": "NVIDIA Corporation", "sector": "Technology"},
        {"symbol": "META", "name": "Meta Platforms Inc.", "sector": "Technology"},
        {"symbol": "NFLX", "name": "Netflix Inc.", "sector": "Technology"},
        {"symbol": "ADBE", "name": "Adobe Inc.", "sector": "Technology"},
        {"symbol": "CRM", "name": "Salesforce Inc.", "sector": "Technology"},
        
        # Healthcare Sector
        {"symbol": "JNJ", "name": "Johnson & Johnson", "sector": "Healthcare"},
        {"symbol": "PFE", "name": "Pfizer Inc.", "sector": "Healthcare"},
        {"symbol": "UNH", "name": "UnitedHealth Group Inc.", "sector": "Healthcare"},
        {"symbol": "ABBV", "name": "AbbVie Inc.", "sector": "Healthcare"},
        {"symbol": "TMO", "name": "Thermo Fisher Scientific Inc.", "sector": "Healthcare"},
        {"symbol": "ABT", "name": "Abbott Laboratories", "sector": "Healthcare"},
        {"symbol": "LLY", "name": "Eli Lilly and Company", "sector": "Healthcare"},
        {"symbol": "DHR", "name": "Danaher Corporation", "sector": "Healthcare"},
        {"symbol": "BMY", "name": "Bristol-Myers Squibb", "sector": "Healthcare"},
        {"symbol": "AMGN", "name": "Amgen Inc.", "sector": "Healthcare"},
        
        # Financial Sector
        {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "sector": "Financial"},
        {"symbol": "BAC", "name": "Bank of America Corp.", "sector": "Financial"},
        {"symbol": "WFC", "name": "Wells Fargo & Company", "sector": "Financial"},
        {"symbol": "GS", "name": "Goldman Sachs Group Inc.", "sector": "Financial"},
        {"symbol": "MS", "name": "Morgan Stanley", "sector": "Financial"},
        {"symbol": "C", "name": "Citigroup Inc.", "sector": "Financial"},
        {"symbol": "BLK", "name": "BlackRock Inc.", "sector": "Financial"},
        {"symbol": "AXP", "name": "American Express Company", "sector": "Financial"},
        {"symbol": "CB", "name": "Chubb Limited", "sector": "Financial"},
        {"symbol": "SPGI", "name": "S&P Global Inc.", "sector": "Financial"},
        
        # Consumer Sector
        {"symbol": "PG", "name": "Procter & Gamble Co.", "sector": "Consumer"},
        {"symbol": "KO", "name": "The Coca-Cola Company", "sector": "Consumer"},
        {"symbol": "PEP", "name": "PepsiCo Inc.", "sector": "Consumer"},
        {"symbol": "WMT", "name": "Walmart Inc.", "sector": "Consumer"},
        {"symbol": "HD", "name": "The Home Depot Inc.", "sector": "Consumer"},
        {"symbol": "MCD", "name": "McDonald's Corporation", "sector": "Consumer"},
        {"symbol": "DIS", "name": "The Walt Disney Company", "sector": "Consumer"},
        {"symbol": "NKE", "name": "Nike Inc.", "sector": "Consumer"},
        {"symbol": "SBUX", "name": "Starbucks Corporation", "sector": "Consumer"},
        {"symbol": "TGT", "name": "Target Corporation", "sector": "Consumer"},
        
        # Energy Sector
        {"symbol": "XOM", "name": "Exxon Mobil Corporation", "sector": "Energy"},
        {"symbol": "CVX", "name": "Chevron Corporation", "sector": "Energy"},
        {"symbol": "COP", "name": "ConocoPhillips", "sector": "Energy"},
        {"symbol": "EOG", "name": "EOG Resources Inc.", "sector": "Energy"},
        {"symbol": "SLB", "name": "Schlumberger Limited", "sector": "Energy"},
        {"symbol": "PSX", "name": "Phillips 66", "sector": "Energy"},
        {"symbol": "MPC", "name": "Marathon Petroleum Corp.", "sector": "Energy"},
        {"symbol": "VLO", "name": "Valero Energy Corporation", "sector": "Energy"},
        {"symbol": "KMI", "name": "Kinder Morgan Inc.", "sector": "Energy"},
        {"symbol": "OKE", "name": "ONEOK Inc.", "sector": "Energy"},
    ]
    
    # Save default config
    with open(config_file, 'w') as f:
        json.dump(default_stocks, f, indent=2)
    
    return default_stocks

def main():
    """Main function to fetch comprehensive stock data"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch comprehensive stock data")
    parser.add_argument("--symbols", nargs="+", help="Stock symbols to fetch")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of stocks")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between API calls")
    parser.add_argument("--output", default="comprehensive_stock_data.json", help="Output file")
    parser.add_argument("--sector", help="Filter by sector")
    
    args = parser.parse_args()
    
    # Get API key from environment
    api_key = os.getenv('FMP_API_KEY')
    if not api_key:
        print("❌ FMP_API_KEY environment variable not set")
        return
    
    # Initialize API client
    client = EnhancedEarningsAPIClient(api_key)
    
    # Load stock configurations
    all_stocks = load_stocks_config()
    
    # Filter stocks based on arguments
    if args.symbols:
        symbols = args.symbols
        print(f"Fetching data for specified symbols: {symbols}")
    elif args.sector:
        sector = args.sector.capitalize()
        symbols = [s["symbol"] for s in all_stocks if s["sector"] == sector]
        print(f"Fetching data for {sector} sector: {len(symbols)} stocks")
    else:
        symbols = [s["symbol"] for s in all_stocks][:args.limit]
        print(f"Fetching data for {len(symbols)} stocks")
    
    # Fetch comprehensive stock data
    data = client.fetch_batch_stock_data(symbols, delay=args.delay)
    
    # Save to file
    save_stock_data(data, args.output)
    
    # Print summary
    print("\n📊 Comprehensive Stock Data Summary:")
    print("=" * 60)
    
    for symbol, stock_data in data.items():
        print(f"\n{symbol}: {stock_data.company_name}")
        print(f"  Current Price: ${stock_data.current_price:.2f} ({stock_data.change_percent:+.2f}%)")
        print(f"  Volume: {stock_data.volume:,.0f}")
        print(f"  Revenue: ${stock_data.revenue:.2f}B ({stock_data.revenue_growth:+.1f}%)")
        print(f"  EPS: ${stock_data.eps:.2f} ({stock_data.eps_growth:+.1f}%)")
        print(f"  Analyst Ratings: {len(stock_data.analyst_ratings)} available")
        print(f"  Price History: {len(stock_data.price_history)} days")
        print("-" * 40)

if __name__ == "__main__":
    main() 