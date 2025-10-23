#!/usr/bin/env python3
"""
Debug script to check news distribution
"""

import json

# Read the convert_news_data.py file and extract the manual_news_data
with open('convert_news_data.py', 'r') as f:
    content = f.read()

# Find the manual_news_data section
start = content.find('manual_news_data = [')
if start == -1:
    print("Could not find manual_news_data")
    exit(1)

# Extract the data (this is a simplified approach)
print("Found manual_news_data section")

# Let's check the distribution logic manually
stocks = ["GOOGL", "NVDA", "PLTR", "ABBV", "UNH", "JPM", "RKLB", "MARKET"]
stock_news = {symbol: [] for symbol in stocks}

# Sample news items to test
test_articles = [
    {
        "title": "Test Market News",
        "date": "Mon, 01 Jul 2025 12:00:00 -0400",
        "source": "Manual News Collection",
        "text": "This is a test market news item",
        "url": "",
        "sentiment": "neutral",
        "tickers": ["MARKET"],
        "topics": [],
        "source_type": "manual"
    },
    {
        "title": "Test GOOGL News",
        "date": "Mon, 01 Jul 2025 12:00:00 -0400",
        "source": "Manual News Collection",
        "text": "This is a test GOOGL news item",
        "url": "",
        "sentiment": "positive",
        "tickers": ["GOOGL"],
        "topics": [],
        "source_type": "manual"
    }
]

# Test the distribution logic
for article in test_articles:
    print(f"Processing article: {article['title']}")
    print(f"Tickers: {article['tickers']}")
    
    if article["tickers"] == ["MARKET"]:
        print("  -> Distributing to all stocks")
        for symbol in stocks:
            article_copy = article.copy()
            article_copy["tickers"] = [symbol]
            stock_news[symbol].append(article_copy)
    else:
        print("  -> Stock-specific news")
        for ticker in article["tickers"]:
            if ticker in stock_news:
                print(f"    -> Adding to {ticker}")
                stock_news[ticker].append(article)
            else:
                print(f"    -> {ticker} not in stock_news")

print("\nResults:")
for symbol, articles in stock_news.items():
    print(f"{symbol}: {len(articles)} articles")
    for article in articles:
        print(f"  - {article['title']}")

