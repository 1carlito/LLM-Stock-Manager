"""
FMP Analyst Ratings Fetcher
===========================

This script fetches analyst ratings from Financial Modeling Prep API for:
- PLTR: After August 4, 2025 earnings
- NVO: After August 6, 2025 earnings  
- BP: After August 5, 2025 earnings

Focuses on July 2025 analyst ratings and updates after earnings releases.
Note: Some endpoints may require paid subscription.
"""

import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import os
from typing import Dict, List, Any
import time

class FMPAnalystRatings:
    """Fetch and analyze analyst ratings from FMP API"""
    
    def __init__(self, api_key: str):
        """
        Initialize FMP API client
        
        Args:
            api_key: FMP API key
        """
        self.api_key = api_key
        self.base_url = "https://financialmodelingprep.com/stable"
        
    def _make_request(self, endpoint: str, params: Dict = None) -> List[Dict]:
        """
        Make API request to FMP
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            API response as list of dictionaries
        """
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
            
            if isinstance(data, list):
                return data
            else:
                print(f"Unexpected response format: {type(data)}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return []
    
    def get_price_target_news(self, symbol: str, limit: int = 50) -> List[Dict]:
        """
        Get price target news and analyst ratings
        Note: This endpoint may require paid subscription
        
        Args:
            symbol: Stock symbol
            limit: Number of records to retrieve
            
        Returns:
            List of analyst rating dictionaries
        """
        endpoint = "price-target-news"
        params = {
            'symbol': symbol,
            'limit': limit,
            'page': 0
        }
        
        return self._make_request(endpoint, params)
    
    def get_latest_price_target_news(self, limit: int = 100) -> List[Dict]:
        """
        Get latest price target news across all stocks
        Note: This endpoint may require paid subscription
        
        Args:
            limit: Number of records to retrieve
            
        Returns:
            List of latest analyst rating dictionaries
        """
        endpoint = "price-target-latest-news"
        params = {
            'limit': limit,
            'page': 0
        }
        
        return self._make_request(endpoint, params)
    
    def get_grades(self, symbol: str) -> List[Dict]:
        """
        Get current stock grades/ratings
        
        Args:
            symbol: Stock symbol
            
        Returns:
            List of grade dictionaries
        """
        endpoint = "grades"
        params = {'symbol': symbol}
        
        return self._make_request(endpoint, params)
    
    def get_historical_grades(self, symbol: str, limit: int = 50) -> List[Dict]:
        """
        Get historical stock grades
        
        Args:
            symbol: Stock symbol
            limit: Number of records to retrieve
            
        Returns:
            List of historical grade dictionaries
        """
        endpoint = "grades-historical"
        params = {
            'symbol': symbol,
            'limit': limit
        }
        
        return self._make_request(endpoint, params)
    
    def get_price_target_summary(self, symbol: str) -> List[Dict]:
        """
        Get price target summary
        
        Args:
            symbol: Stock symbol
            
        Returns:
            List of price target summary dictionaries
        """
        endpoint = "price-target-summary"
        params = {'symbol': symbol}
        
        return self._make_request(endpoint, params)
    
    def get_price_target_consensus(self, symbol: str) -> List[Dict]:
        """
        Get price target consensus
        
        Args:
            symbol: Stock symbol
            
        Returns:
            List of price target consensus dictionaries
        """
        endpoint = "price-target-consensus"
        params = {'symbol': symbol}
        
        return self._make_request(endpoint, params)
    
    def get_analyst_estimates(self, symbol: str, period: str = 'quarter', limit: int = 10) -> List[Dict]:
        """
        Get analyst financial estimates
        
        Args:
            symbol: Stock symbol
            period: 'annual' or 'quarter'
            limit: Number of records to retrieve
            
        Returns:
            List of analyst estimate dictionaries
        """
        endpoint = "analyst-estimates"
        params = {
            'symbol': symbol,
            'period': period,
            'limit': limit,
            'page': 0
        }
        
        return self._make_request(endpoint, params)
    
    def get_ratings_snapshot(self, symbol: str) -> List[Dict]:
        """
        Get ratings snapshot for a symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            List of rating snapshots
        """
        endpoint = "ratings-snapshot"
        params = {'symbol': symbol}
        
        return self._make_request(endpoint, params)
    
    def get_company_profile(self, symbol: str) -> List[Dict]:
        """
        Get company profile data
        
        Args:
            symbol: Stock symbol
            
        Returns:
            List of company profile data
        """
        endpoint = "profile"
        params = {'symbol': symbol}
        
        return self._make_request(endpoint, params)
    
    def get_historical_prices(self, symbol: str, limit: int = 30) -> List[Dict]:
        """
        Get historical stock prices (end-of-day)
        
        Args:
            symbol: Stock symbol
            limit: Number of days to retrieve
            
        Returns:
            List of historical price data
        """
        endpoint = f"historical-price-eod/full"
        params = {
            'symbol': symbol,
            'limit': limit
        }
        
        return self._make_request(endpoint, params)
    
    def get_earnings_data(self, symbol: str, limit: int = 10) -> List[Dict]:
        """
        Get earnings report data
        
        Args:
            symbol: Stock symbol
            limit: Number of earnings reports to retrieve
            
        Returns:
            List of earnings data
        """
        endpoint = "earnings"
        params = {
            'symbol': symbol,
            'limit': limit
        }
        
        return self._make_request(endpoint, params)
    
    def get_financial_statements_income(self, symbol: str, limit: int = 4) -> List[Dict]:
        """
        Get income statement data
        
        Args:
            symbol: Stock symbol
            limit: Number of periods to retrieve
            
        Returns:
            List of income statement data
        """
        endpoint = "income-statement"
        params = {
            'symbol': symbol,
            'limit': limit
        }
        
        return self._make_request(endpoint, params)
    
    def get_key_metrics(self, symbol: str, limit: int = 4) -> List[Dict]:
        """
        Get key financial metrics
        
        Args:
            symbol: Stock symbol
            limit: Number of periods to retrieve
            
        Returns:
            List of key metrics data
        """
        endpoint = "key-metrics"
        params = {
            'symbol': symbol,
            'limit': limit
        }
        
        return self._make_request(endpoint, params)
    
    def filter_july_2025_ratings(self, ratings: List[Dict]) -> List[Dict]:
        """
        Filter ratings for July 2025
        
        Args:
            ratings: List of rating dictionaries
            
        Returns:
            Filtered list of July 2025 ratings
        """
        july_ratings = []
        
        for rating in ratings:
            if 'publishedDate' in rating:
                try:
                    # Parse the date
                    date_str = rating['publishedDate']
                    if 'T' in date_str:
                        date_str = date_str.split('T')[0]  # Extract date part only
                    
                    rating_date = datetime.strptime(date_str, '%Y-%m-%d')
                    
                    # Check if it's July 2025
                    if rating_date.year == 2025 and rating_date.month == 7:
                        july_ratings.append(rating)
                        
                except (ValueError, TypeError) as e:
                    print(f"Error parsing date {rating.get('publishedDate', 'unknown')}: {e}")
                    continue
        
        return july_ratings
    
    def filter_post_earnings_ratings(self, ratings: List[Dict], earnings_date: str) -> List[Dict]:
        """
        Filter ratings that came after earnings date
        
        Args:
            ratings: List of rating dictionaries
            earnings_date: Earnings date in YYYY-MM-DD format
            
        Returns:
            Filtered list of post-earnings ratings
        """
        post_earnings_ratings = []
        earnings_dt = datetime.strptime(earnings_date, '%Y-%m-%d')
        
        for rating in ratings:
            if 'publishedDate' in rating:
                try:
                    # Parse the rating date
                    date_str = rating['publishedDate']
                    if 'T' in date_str:
                        date_str = date_str.split('T')[0]
                    
                    rating_date = datetime.strptime(date_str, '%Y-%m-%d')
                    
                    # Check if rating came after earnings
                    if rating_date > earnings_dt:
                        post_earnings_ratings.append(rating)
                        
                except (ValueError, TypeError) as e:
                    print(f"Error parsing date {rating.get('publishedDate', 'unknown')}: {e}")
                    continue
        
        return post_earnings_ratings
    
    def format_analyst_rating(self, rating: Dict) -> Dict:
        """
        Format analyst rating for our data structure
        
        Args:
            rating: Raw rating dictionary from API
            
        Returns:
            Formatted rating dictionary
        """
        formatted = {
            'symbol': rating.get('symbol', 'Unknown'),
            'published_date': rating.get('publishedDate', 'Unknown'),
            'analyst_name': rating.get('analystName', 'Unknown'),
            'analyst_company': rating.get('analystCompany', 'Unknown'),
            'price_target': rating.get('priceTarget', 0),
            'adjusted_price_target': rating.get('adjPriceTarget', 0),
            'price_when_posted': rating.get('priceWhenPosted', 0),
            'news_title': rating.get('newsTitle', ''),
            'news_url': rating.get('newsURL', ''),
            'news_publisher': rating.get('newsPublisher', 'Unknown'),
            'news_base_url': rating.get('newsBaseURL', 'Unknown')
        }
        
        # Extract rating action from news title
        title = formatted['news_title'].lower()
        if 'upgrade' in title:
            formatted['action'] = 'upgrade'
        elif 'downgrade' in title:
            formatted['action'] = 'downgrade'
        elif 'maintain' in title or 'reiterates' in title:
            formatted['action'] = 'maintain'
        else:
            formatted['action'] = 'unknown'
        
        return formatted
    
    def fetch_stock_analyst_ratings(self, symbol: str, earnings_date: str) -> Dict[str, Any]:
        """
        Fetch comprehensive analyst ratings for a stock
        
        Args:
            symbol: Stock symbol
            earnings_date: Earnings date in YYYY-MM-DD format
            
        Returns:
            Dictionary with all rating data
        """
        print(f"\n🔍 Fetching analyst ratings for {symbol} (earnings: {earnings_date})")
        
        # Get price target news (may require paid subscription)
        price_target_news = self.get_price_target_news(symbol, limit=50)
        print(f"📊 Found {len(price_target_news)} price target news items")
        
        # Get grades (available in free tier)
        grades = self.get_grades(symbol)
        print(f"📈 Found {len(grades)} current grades")
        
        # Get historical grades (available in free tier)
        historical_grades = self.get_historical_grades(symbol, limit=50)
        print(f"📅 Found {len(historical_grades)} historical grades")
        
        # Get price target summary (available in free tier)
        price_target_summary = self.get_price_target_summary(symbol)
        print(f"📋 Found {len(price_target_summary)} price target summaries")
        
        # Get price target consensus (available in free tier)
        price_target_consensus = self.get_price_target_consensus(symbol)
        print(f"🎯 Found {len(price_target_consensus)} price target consensus")
        
        # Get analyst estimates (available in free tier)
        analyst_estimates = self.get_analyst_estimates(symbol, period='quarter', limit=10)
        print(f"📊 Found {len(analyst_estimates)} analyst estimates")
        
        # Get ratings snapshot (available in free tier)
        ratings_snapshot = self.get_ratings_snapshot(symbol)
        print(f"📈 Found {len(ratings_snapshot)} ratings snapshots")
        
        # Filter for July 2025 ratings (if price target news is available)
        july_ratings = self.filter_july_2025_ratings(price_target_news)
        print(f"📅 Found {len(july_ratings)} July 2025 ratings")
        
        # Filter for post-earnings ratings (if price target news is available)
        post_earnings_ratings = self.filter_post_earnings_ratings(price_target_news, earnings_date)
        print(f"📈 Found {len(post_earnings_ratings)} post-earnings ratings")
        
        # Format July 2025 ratings
        formatted_july_ratings = [self.format_analyst_rating(rating) for rating in july_ratings]
        
        # Format post-earnings ratings
        formatted_post_earnings = [self.format_analyst_rating(rating) for rating in post_earnings_ratings]
        
        return {
            'symbol': symbol,
            'earnings_date': earnings_date,
            'july_2025_ratings': formatted_july_ratings,
            'post_earnings_ratings': formatted_post_earnings,
            'current_grades': grades,
            'historical_grades': historical_grades,
            'price_target_summary': price_target_summary,
            'price_target_consensus': price_target_consensus,
            'analyst_estimates': analyst_estimates,
            'ratings_snapshot': ratings_snapshot,
            'all_price_target_news': price_target_news
        }
    
    def fetch_all_stocks_ratings(self) -> Dict[str, Any]:
        """
        Fetch analyst ratings for all target stocks
        
        Returns:
            Dictionary with ratings for all stocks
        """
        # Stock earnings dates
        stock_earnings_dates = {
            'PLTR': '2025-08-04',  # August 4, 2025
            'NVO': '2025-08-06',   # August 6, 2025
            'BP': '2025-08-05'     # August 5, 2025
        }
        
        all_ratings = {}
        
        for symbol, earnings_date in stock_earnings_dates.items():
            print(f"\n{'='*60}")
            print(f"📊 ANALYZING {symbol} - Earnings Date: {earnings_date}")
            print(f"{'='*60}")
            
            ratings = self.fetch_stock_analyst_ratings(symbol, earnings_date)
            all_ratings[symbol] = ratings
            
            # Add delay to avoid rate limiting
            time.sleep(1)
        
        return all_ratings
    
    def save_ratings_to_files(self, all_ratings: Dict[str, Any]):
        """
        Save ratings data to CSV and JSON files
        
        Args:
            all_ratings: Dictionary with all ratings data
        """
        # Create output directory
        os.makedirs('analyst_ratings', exist_ok=True)
        
        # Save comprehensive JSON
        json_path = 'analyst_ratings/all_analyst_ratings.json'
        with open(json_path, 'w') as f:
            json.dump(all_ratings, f, indent=2, default=str)
        print(f"\n✅ Saved comprehensive data: {json_path}")
        
        # Create CSV for July 2025 ratings
        july_ratings_csv = []
        for symbol, data in all_ratings.items():
            for rating in data['july_2025_ratings']:
                rating['stock_symbol'] = symbol
                rating['earnings_date'] = data['earnings_date']
                july_ratings_csv.append(rating)
        
        if july_ratings_csv:
            df_july = pd.DataFrame(july_ratings_csv)
            csv_path = 'analyst_ratings/july_2025_ratings.csv'
            df_july.to_csv(csv_path, index=False)
            print(f"✅ Saved July 2025 ratings: {csv_path} ({len(july_ratings_csv)} records)")
        
        # Create CSV for post-earnings ratings
        post_earnings_csv = []
        for symbol, data in all_ratings.items():
            for rating in data['post_earnings_ratings']:
                rating['stock_symbol'] = symbol
                rating['earnings_date'] = data['earnings_date']
                post_earnings_csv.append(rating)
        
        if post_earnings_csv:
            df_post = pd.DataFrame(post_earnings_csv)
            csv_path = 'analyst_ratings/post_earnings_ratings.csv'
            df_post.to_csv(csv_path, index=False)
            print(f"✅ Saved post-earnings ratings: {csv_path} ({len(post_earnings_csv)} records)")
        
        # Create CSV for available data (grades, consensus, etc.)
        available_data_csv = []
        for symbol, data in all_ratings.items():
            # Add price target consensus
            if data['price_target_consensus']:
                for consensus in data['price_target_consensus']:
                    available_data_csv.append({
                        'symbol': symbol,
                        'data_type': 'price_target_consensus',
                        'target_high': consensus.get('targetHigh', 0),
                        'target_low': consensus.get('targetLow', 0),
                        'target_consensus': consensus.get('targetConsensus', 0),
                        'target_median': consensus.get('targetMedian', 0)
                    })
            
            # Add analyst estimates
            if data['analyst_estimates']:
                for estimate in data['analyst_estimates']:
                    available_data_csv.append({
                        'symbol': symbol,
                        'data_type': 'analyst_estimate',
                        'date': estimate.get('date', ''),
                        'revenue_avg': estimate.get('revenueAvg', 0),
                        'eps_avg': estimate.get('epsAvg', 0),
                        'num_analysts_revenue': estimate.get('numAnalystsRevenue', 0),
                        'num_analysts_eps': estimate.get('numAnalystsEps', 0)
                    })
        
        if available_data_csv:
            df_available = pd.DataFrame(available_data_csv)
            csv_path = 'analyst_ratings/available_analyst_data.csv'
            df_available.to_csv(csv_path, index=False)
            print(f"✅ Saved available analyst data: {csv_path} ({len(available_data_csv)} records)")
        
        # Create summary
        summary = {
            'fetch_date': datetime.now().isoformat(),
            'stocks_analyzed': list(all_ratings.keys()),
            'total_july_2025_ratings': sum(len(data['july_2025_ratings']) for data in all_ratings.values()),
            'total_post_earnings_ratings': sum(len(data['post_earnings_ratings']) for data in all_ratings.values()),
            'total_available_data_records': len(available_data_csv),
            'files_created': ['all_analyst_ratings.json', 'july_2025_ratings.csv', 'post_earnings_ratings.csv', 'available_analyst_data.csv'],
            'note': 'Some endpoints may require paid subscription. Available data includes grades, consensus, and estimates.'
        }
        
        summary_path = 'analyst_ratings/fetch_summary.json'
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"✅ Saved summary: {summary_path}")
    
    def print_summary(self, all_ratings: Dict[str, Any]):
        """
        Print a summary of fetched ratings
        
        Args:
            all_ratings: Dictionary with all ratings data
        """
        print(f"\n{'='*80}")
        print("📊 ANALYST RATINGS SUMMARY")
        print(f"{'='*80}")
        
        for symbol, data in all_ratings.items():
            print(f"\n🏢 {symbol} (Earnings: {data['earnings_date']})")
            print(f"   📅 July 2025 Ratings: {len(data['july_2025_ratings'])}")
            print(f"   📈 Post-Earnings Ratings: {len(data['post_earnings_ratings'])}")
            print(f"   📊 Current Grades: {len(data['current_grades'])}")
            print(f"   📋 Price Target Consensus: {len(data['price_target_consensus'])}")
            print(f"   📈 Analyst Estimates: {len(data['analyst_estimates'])}")
            
            if data['price_target_consensus']:
                consensus = data['price_target_consensus'][0]
                print(f"   🎯 Consensus: High ${consensus.get('targetHigh', 0):.2f}, Low ${consensus.get('targetLow', 0):.2f}, Avg ${consensus.get('targetConsensus', 0):.2f}")
            
            if data['july_2025_ratings']:
                print(f"   📋 July 2025 Analysts:")
                for rating in data['july_2025_ratings']:
                    print(f"      • {rating['analyst_company']} ({rating['analyst_name']}): ${rating['price_target']:.2f}")
            
            if data['post_earnings_ratings']:
                print(f"   📈 Post-Earnings Analysts:")
                for rating in data['post_earnings_ratings'][:3]:  # Show first 3
                    print(f"      • {rating['analyst_company']} ({rating['analyst_name']}): ${rating['price_target']:.2f}")
                    print(f"        Action: {rating['action']} | Date: {rating['published_date']}")

def main():
    """Main function to fetch analyst ratings"""
    
    # Get API key from environment variable
    api_key = os.getenv('FMP_API_KEY')
    if not api_key:
        print("❌ FMP_API_KEY environment variable not set")
        print("Please set your FMP API key:")
        print("export FMP_API_KEY='your_api_key_here'")
        print("\nGet your API key from: https://financialmodelingprep.com/developer/docs/")
        return
    
    print("🚀 FMP Analyst Ratings Fetcher")
    print("=" * 50)
    print("📊 Fetching analyst ratings for:")
    print("   • PLTR: After August 4, 2025 earnings")
    print("   • NVO: After August 6, 2025 earnings")
    print("   • BP: After August 5, 2025 earnings")
    print("   • Focus: July 2025 ratings")
    print("   • Note: Some endpoints may require paid subscription")
    print("=" * 50)
    
    # Initialize fetcher
    fetcher = FMPAnalystRatings(api_key)
    
    # Fetch all ratings
    all_ratings = fetcher.fetch_all_stocks_ratings()
    
    # Save to files
    fetcher.save_ratings_to_files(all_ratings)
    
    # Print summary
    fetcher.print_summary(all_ratings)
    
    print(f"\n🎯 Analysis complete!")
    print(f"📁 All files saved to: analyst_ratings/")

if __name__ == "__main__":
    main() 