#!/usr/bin/env python3
"""
News Data Manager
================

Combines manually scraped news with Stock News API data.
Converts all news into the format expected by the SentimentAgent.
"""

import json
import os
import requests
import time
from datetime import datetime
from typing import Dict, List, Any
from dotenv import load_dotenv

class NewsDataManager:
    def __init__(self, output_dir: str = "news_data"):
        load_dotenv()
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize Stock News API
        self.api_key = os.getenv("STOCK_NEWS_API_KEY")
        if not self.api_key:
            raise ValueError("STOCK_NEWS_API_KEY environment variable not set")
        self.base_url = "https://stocknewsapi.com/api/v1"

    def fetch_api_news(self, symbol: str, days: int = 30, page: int = 1, date: str = None, start_date: str = None, end_date: str = None) -> List[Dict]:
        """
        Fetch news from Stock News API for a single stock
        
        Args:
            symbol: Stock ticker symbol
            days: Number of days to look back
            page: Page number for pagination
            date: Specific date to fetch (YYYY-MM-DD format)
            start_date: Start date for date range (MM/DD/YYYY format)
            end_date: End date for date range (MM/DD/YYYY format)
        """
        # Build URL with query parameters
        url = f"{self.base_url}?tickers={symbol}&items=50&page={page}&token={self.api_key}"
        if date:
            url += f"&date={date}"
        elif start_date and end_date:
            url += f"&date={start_date}:{end_date}"
        
        try:
            print(f"📡 API Request: {url.replace(self.api_key, '***')}")
            print(f"   Ticker: {symbol}")
            print(f"   Page: {page}")
            if date:
                print(f"   Date: {date}")
            
            # Simple GET request
            response = requests.get(url)
            response.raise_for_status()
            
            data = response.json()
            if 'data' in data:
                articles = data['data']
                print(f"✅ Found {len(articles)} articles for {symbol} on page {page}")
                return articles
            else:
                print("❌ No 'data' field in response")
                print(f"Response: {data}")
                return []
                
        except Exception as e:
            print(f"❌ API Error: {str(e)}")
            print(f"   URL: {url.replace(self.api_key, '***')}")
            return []

    def fetch_all_available_news(self, symbol: str, start_date: str = None, end_date: str = None) -> List[Dict]:
        """
        Fetch all available news for a symbol within date range
        
        Args:
            symbol: Stock ticker symbol
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
        """
        all_articles = []
        page = 1
        max_pages = 10  # Limit to avoid excessive API calls
        
        while page <= max_pages:
            articles = self.fetch_api_news(symbol, page=page)
            if not articles:
                break
                
            all_articles.extend(articles)
            
            # Check if we've reached the desired date range
            if start_date and articles[-1]['date'] < start_date:
                break
                
            # Add delay between pages
            if page < max_pages:
                print("⏳ Waiting 2 seconds before next page...")
                time.sleep(2)
            
            page += 1
        
        return all_articles

    def convert_api_news(self, articles: List[Dict]) -> List[Dict]:
        """Convert API news to our format"""
        converted = []
        for article in articles:
            # Match the example format
            converted.append({
                "title": article.get("title", ""),
                "date": article.get("date", ""),  # Format: "Fri, 19 Sep 2025 08:45:00 -0400"
                "source": article.get("source_name", "Stock News API"),
                "text": article.get("text", ""),
                "url": article.get("news_url", ""),
                "sentiment": article.get("sentiment", "neutral"),
                "tickers": article.get("tickers", []),
                "topics": article.get("topics", []),
                "source_type": "api"
            })
        return converted

    def convert_manual_news(self, articles: List[Dict]) -> List[Dict]:
        """Convert manually scraped news to our format"""
        converted = []
        for article in articles:
            converted.append({
                "title": article["title"],
                "date": article["date"],
                "source": article.get("source", "Manual Scrape"),
                "text": article.get("text", ""),
                "url": article.get("url", ""),
                "sentiment": "neutral",  # Will be analyzed by agent
                "topics": [],  # Empty for manual news
                "source_type": "manual"
            })
        return converted

    def combine_news_data(self, symbol: str, manual_news: List[Dict], days: int = 30) -> Dict[str, Any]:
        """Combine manual and API news data"""
        print(f"🔄 Processing news for {symbol}...")
        
        # Get API news
        api_articles = self.fetch_api_news(symbol, days=days)
        
        # Convert both sources
        converted_api = self.convert_api_news(api_articles)
        converted_manual = self.convert_manual_news(manual_news)
        
        # Combine and deduplicate (based on titles)
        seen_titles = set()
        combined_news = []
        
        # Add API news first
        for article in converted_api:
            title = article["title"].lower()
            if title not in seen_titles:
                seen_titles.add(title)
                combined_news.append(article)
        
        # Add manual news, skip if title already exists
        for article in converted_manual:
            title = article["title"].lower()
            if title not in seen_titles:
                seen_titles.add(title)
                combined_news.append(article)
        
        # Sort by date (newest first)
        combined_news.sort(key=lambda x: x["date"], reverse=True)
        
        # Create final format
        sentiment_data = {
            "stock_symbol": symbol,
            "search_date": datetime.now().isoformat(),
            "api_articles": len(converted_api),
            "manual_articles": len(converted_manual),
            "total_articles": len(combined_news),
            "parsed_results": {
                symbol: {
                    "news": combined_news,
                    "press_releases": [],
                    "analyst_actions": [],
                    "market_impact": f"Combined news analysis for {symbol} covering {len(combined_news)} articles"
                }
            }
        }
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{symbol}_combined_news_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(sentiment_data, f, indent=2)
        
        print(f"\n📊 News Summary for {symbol}:")
        print(f"   API Articles: {len(converted_api)}")
        print(f"   Manual Articles: {len(converted_manual)}")
        print(f"   Total Unique Articles: {len(combined_news)}")
        print(f"   Saved to: {filepath}")
        
        return sentiment_data

def process_stock_news():
    """Process news data for multiple stocks from Sep 5 to Oct 1"""
    
    # List of stocks to process
    stocks = [
        "GOOGL",  # Alphabet Inc.
        "NVDA",   # NVIDIA Corporation  
        "PLTR",   # Palantir Technologies Inc.
        "ABBV",   # AbbVie Inc.
        "UNH",    # UnitedHealth Group Incorporated
        "JPM",    # JPMorgan Chase & Co.
        "RKLB"    # Rocket Lab USA, Inc.
    ]
    
    # Date range: Aug 20 to Oct 1, 2025
    start_date = "08/20/2025"
    end_date = "10/01/2025"
    
    print(f"\n🔄 Processing news data for multiple stocks from {start_date} to {end_date}...")
    print("=" * 50)
    
    # Initialize manager
    manager = NewsDataManager()
    
    # Process each stock individually
    for symbol in stocks:
        print(f"\n📰 Processing {symbol}...")
        
        try:
            # Fetch news for this specific stock (API returns most recent articles)
            articles = manager.fetch_api_news(
                symbol=symbol, 
                page=1
            )
            
            if articles:
                # Convert and save
                converted = manager.convert_api_news(articles)
                
                # Create sentiment data structure
                sentiment_data = {
                    "stock_symbol": symbol,
                    "search_date": datetime.now().isoformat(),
                    "api_articles": len(converted),
                    "manual_articles": 0,
                    "total_articles": len(converted),
                    "date_range": {
                        "start": start_date,
                        "end": end_date
                    },
                    "parsed_results": {
                        symbol: {
                            "news": converted,
                            "press_releases": [],
                            "analyst_actions": [],
                            "market_impact": f"News analysis for {symbol} covering {len(converted)} articles"
                        }
                    }
                }
                
                # Save to file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{symbol}_combined_news_{timestamp}.json"
                filepath = os.path.join(manager.output_dir, filename)
                
                with open(filepath, 'w') as f:
                    json.dump(sentiment_data, f, indent=2)
                
                print(f"✅ Successfully processed {symbol}: {len(converted)} articles")
                print(f"   Saved to: {filepath}")
            else:
                print(f"⚠️ No articles found for {symbol}")
                
        except Exception as e:
            print(f"❌ Error processing {symbol}: {e}")
    
    print("\n✅ News collection complete!")

if __name__ == "__main__":
    # Process news for all stocks
    process_stock_news()
