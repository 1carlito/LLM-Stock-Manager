"""
Fetch NOVO News
================

Fetches news data for NOVO.
"""

import os
import sys
import time
from datetime import datetime
import json
from typing import List, Dict

# Add parent directory to Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from convert_news_data import NewsDataManager

def fetch_novo_news():
    """Fetch and combine all news for NOVO"""
    # Create news data directory
    os.makedirs("news_data", exist_ok=True)
    
    manager = NewsDataManager(output_dir="news_data")
    
    print("\n🚀 FETCHING NOVO NEWS")
    print("===================")
    print("📅 Target Date Range: Sep 2024 - Sep 2025")
    print("=" * 50)
    
    # Fetch API news
    print("\n🌐 Fetching API news data...")
    api_articles = manager.fetch_all_available_news(
        symbol="NVO",
        start_date="2025-01-01",
        end_date="2025-09-19"
    )
    print(f"✅ Fetched {len(api_articles)} API articles")
    
    # Convert API articles to our format
    converted_api = manager.convert_api_news(api_articles)
    
    # Sort by date
    converted_api.sort(key=lambda x: datetime.strptime(x['date'].split(',')[1].strip(), '%d %b %Y %H:%M:%S %z'), reverse=True)
    
    # Create news data structure
    news_data = {
        "stock_symbol": "NOVO",
        "search_date": datetime.now().isoformat(),
        "api_articles": len(converted_api),
        "manual_articles": 0,
        "total_articles": len(converted_api),
        "parsed_results": {
            "NOVO": {
                "news": converted_api,
                "press_releases": [],
                "analyst_actions": [],
                "market_impact": f"News analysis for NOVO covering {len(converted_api)} articles"
            }
        }
    }
    
    # Save combined data
    output_file = os.path.join("news_data", "novo_news_data.json")
    with open(output_file, "w") as f:
        json.dump(news_data, f, indent=2)
    
    # Print summary
    print("\n📊 RESULTS SUMMARY")
    print("================")
    print(f"API Articles: {len(converted_api)}")
    print(f"Total Articles: {len(converted_api)}")
    
    # Check date range of articles
    if converted_api:
        dates = [datetime.strptime(article['date'].split(',')[1].strip(), '%d %b %Y %H:%M:%S %z')
                for article in converted_api
                if article.get('date')]
        if dates:
            earliest = min(dates)
            latest = max(dates)
            print(f"\n📅 Article Date Range:")
            print(f"Earliest: {earliest.strftime('%Y-%m-%d')}")
            print(f"Latest: {latest.strftime('%Y-%m-%d')}")
    
    print("\n💾 News data saved to:", output_file)
    print("✨ Done!")

if __name__ == "__main__":
    fetch_novo_news()

