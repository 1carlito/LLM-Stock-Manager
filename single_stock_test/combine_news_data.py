"""
Combine News Data
===============

Combines and processes news data for NOVO.
"""

import os
import json
from datetime import datetime
from typing import List, Dict

def load_news_data() -> Dict:
    """Load news data from file."""
    news_file = os.path.join("news_data", "novo_news_data.json")
    with open(news_file, "r") as f:
        return json.load(f)

def save_news_data(data: Dict, output_file: str):
    """Save news data to file."""
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)

def combine_news():
    """Combine all news data."""
    print("\n🔄 COMBINING NEWS DATA")
    print("===================")
    
    # Load API news data
    print("\n📚 Loading news data...")
    news_data = load_news_data()
    
    # Get all articles
    articles = news_data["parsed_results"]["NOVO"]["news"]
    
    # Sort by date
    articles.sort(
        key=lambda x: datetime.strptime(x['date'].split(',')[1].strip(), '%d %b %Y %H:%M:%S %z'),
        reverse=True
    )
    
    # Update the news data structure
    news_data["parsed_results"]["NOVO"]["news"] = articles
    
    # Save combined data
    output_file = os.path.join("news_data", "novo_news_combined.json")
    save_news_data(news_data, output_file)
    
    # Print summary
    print("\n📊 RESULTS SUMMARY")
    print("================")
    print(f"Total Articles: {len(articles)}")
    
    # Print date range
    if articles:
        dates = [
            datetime.strptime(article['date'].split(',')[1].strip(), '%d %b %Y %H:%M:%S %z')
            for article in articles
            if article.get('date')
        ]
        if dates:
            earliest = min(dates)
            latest = max(dates)
            print(f"\n📅 Article Date Range:")
            print(f"Earliest: {earliest.strftime('%Y-%m-%d')}")
            print(f"Latest: {latest.strftime('%Y-%m-%d')}")
    
    print("\n💾 Combined news data saved to:", output_file)
    print("✨ Done!")

if __name__ == "__main__":
    combine_news()