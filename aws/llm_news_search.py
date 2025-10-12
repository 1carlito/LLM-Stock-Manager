#!/usr/bin/env python3
"""
News Data API Client
===================

Fetches news data from Stock News API including:
- General market news
- Stock-specific news
- Historical news (up to March 2019)
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
import requests
from dotenv import load_dotenv

class NewsDataAPI:
    def __init__(self, api_key: str = None):
        """Initialize the News Data API client"""
        load_dotenv()
        self.api_key = api_key or os.getenv("STOCK_NEWS_API_KEY")
        if not self.api_key:
            raise ValueError("Stock News API key is required. Add STOCK_NEWS_API_KEY to your .env file")
            
        self.base_url = "https://stocknewsapi.com/api/v1"
        self.results_dir = "news_data"
        os.makedirs(self.results_dir, exist_ok=True)

    def _make_request(self, params: Dict) -> List[Dict]:
        """Make request to Stock News API with error handling"""
        params["token"] = self.api_key
        params["type"] = "article"  # Articles only, no videos
        params["sortby"] = "rank"   # Sort by importance
        
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching news data: {str(e)}")
            return []
        
    def get_general_news(self, limit: int = 50, date_range: str = "last7days") -> List[Dict]:
        """Get latest general market news"""
        params = {
            "items": limit,
            "page": 1,
            "date": date_range
        }
        return self._make_request(params)

    def get_stock_news(self, symbols: List[str], limit: int = 50, date_range: str = "last7days") -> List[Dict]:
        """Get news specific to stock symbols"""
        params = {
            "tickers-include": ",".join(symbols),
            "items": limit,
            "page": 1,
            "date": date_range
        }
        return self._make_request(params)
        
    def search_news_period(self, 
                         symbols: List[str],
                         from_date: str = None,
                         to_date: str = None,
                         limit: int = 100) -> Dict[str, List[Dict]]:
        """
        Search news for multiple symbols within a date range
        
        Args:
            symbols: List of stock symbols
            from_date: Start date in YYYY-MM-DD format
            to_date: End date in YYYY-MM-DD format
            limit: Max number of news items per symbol
            
        Returns:
            Dict mapping symbols to their news items
        """
        # Convert dates to MMDDYYYY format for the API
        if from_date and to_date:
            try:
                from_date_formatted = datetime.strptime(from_date, "%Y-%m-%d").strftime("%m%d%Y")
                to_date_formatted = datetime.strptime(to_date, "%Y-%m-%d").strftime("%m%d%Y")
                date_range = f"{from_date_formatted}-{to_date_formatted}"
            except ValueError:
                print(f"Invalid date format. Use YYYY-MM-DD. Using last30days instead.")
                date_range = "last30days"
        else:
            date_range = "last30days"
            
        print(f"Searching news for {len(symbols)} symbols from {date_range}")
        
        # Get news for all symbols at once
        all_news = self.get_stock_news(symbols, limit, date_range)
        
        # Group by symbol
        results = {symbol: [] for symbol in symbols}
        
        for item in all_news:
            # Check which symbols are mentioned in this news item
            title = item.get("title", "").upper()
            text = item.get("text", "").upper()
            
            for symbol in symbols:
                if symbol.upper() in title or symbol.upper() in text:
                    results[symbol].append(item)
            
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"stock_news_data_{timestamp}.json"
        filepath = os.path.join(self.results_dir, filename)
        
        with open(filepath, "w") as f:
            json.dump({
                "search_date": datetime.now().isoformat(),
                "from_date": from_date,
                "to_date": to_date,
                "date_range_used": date_range,
                "symbols": symbols,
                "total_news_items": len(all_news),
                "results": results
            }, f, indent=2)
            
        return results

    def get_historical_news(self, symbols: List[str], from_date: str, to_date: str, limit: int = 100) -> Dict[str, List[Dict]]:
        """
        Get historical news data (up to March 2019)
        
        Args:
            symbols: List of stock symbols
            from_date: Start date in YYYY-MM-DD format
            to_date: End date in YYYY-MM-DD format
            limit: Max number of news items
            
        Returns:
            Dict mapping symbols to their news items
        """
        return self.search_news_period(symbols, from_date, to_date, limit)

if __name__ == "__main__":
    # Example usage
    api = NewsDataAPI()
    
    # Get general market news
    general_news = api.get_general_news(limit=10)
    print(f"Retrieved {len(general_news)} general news items")
    
    # Get news for specific stocks
    symbols = ["AAPL", "GOOGL", "MSFT"]
    news_data = api.search_news_period(
        symbols=symbols,
        from_date="2024-06-01",
        to_date="2024-08-10"
    )
    print(f"Retrieved news for {len(news_data)} symbols")
