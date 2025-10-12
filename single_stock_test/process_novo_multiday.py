"""
Process NOVO Multiday Analysis
============================

Processes NOVO data through all agents for multiple days.
"""

import os
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add parent directory to Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from FundamentalAgent import FundamentalAgent
from ValuationAgent import ValuationAgent
from SentimentAgent import SentimentAgent

def load_stock_data() -> Dict:
    """Load NOVO stock data."""
    with open("novo_data.json", "r") as f:
        return json.load(f)

def load_news_data() -> Dict:
    """Load NOVO news data."""
    with open(os.path.join("news_data", "novo_news_data.json"), "r") as f:
        return json.load(f)

def process_single_day(
    date: str,
    stock_data: Dict,
    news_data: Dict,
    fundamental_agent: FundamentalAgent,
    valuation_agent: ValuationAgent,
    sentiment_agent: SentimentAgent
) -> Dict[str, Any]:
    """Process a single day's analysis."""
    
    print(f"\n📅 Processing date: {date}")
    print("=" * 50)
    
    # Create output directories if they don't exist
    os.makedirs("fundamental_reports", exist_ok=True)
    os.makedirs("valuation_reports", exist_ok=True)
    os.makedirs("sentiment_data", exist_ok=True)
    
    try:
        # Run fundamental analysis
        print("\n🔍 Running fundamental analysis...")
        fundamental_report = fundamental_agent.analyze_fundamentals(
            symbol="NVO",
            current_date=date
        )
        
        # Save fundamental report
        fundamental_file = os.path.join(
            "fundamental_reports",
            f"NOVO_fundamental_analysis_{date.replace('-', '')}.json"
        )
        with open(fundamental_file, "w") as f:
            json.dump(fundamental_report, f, indent=2)
        print(f"✅ Saved fundamental report to {fundamental_file}")
        
        # Run valuation analysis
        print("\n💰 Running valuation analysis...")
        valuation_report = valuation_agent.analyze_valuation(
            symbol="NVO",
            current_date=date
        )
        
        # Save valuation report
        valuation_file = os.path.join(
            "valuation_reports",
            f"NOVO_valuation_analysis_{date.replace('-', '')}.json"
        )
        with open(valuation_file, "w") as f:
            json.dump(valuation_report, f, indent=2)
        print(f"✅ Saved valuation report to {valuation_file}")
        
        # Run sentiment analysis
        print("\n🎭 Running sentiment analysis...")
        sentiment_report = sentiment_agent.analyze_sentiment(
            symbol="NVO",
            current_date=date
        )
        
        # Save sentiment report
        sentiment_file = os.path.join(
            "sentiment_data",
            f"NOVO_sentiment_analysis_{date.replace('-', '')}.json"
        )
        with open(sentiment_file, "w") as f:
            json.dump(sentiment_report, f, indent=2)
        print(f"✅ Saved sentiment report to {sentiment_file}")
        
        return {
            "date": date,
            "fundamental_report": fundamental_report,
            "valuation_report": valuation_report,
            "sentiment_report": sentiment_report
        }
        
    except Exception as e:
        print(f"❌ Error processing date {date}: {str(e)}")
        return None

def main():
    """Process NOVO data through all agents."""
    print("\n🚀 PROCESSING NOVO MULTIDAY ANALYSIS")
    print("=================================")
    
    # Load data
    print("\n📊 Loading data...")
    stock_data = load_stock_data()
    news_data = load_news_data()
    print("✅ Data loaded successfully")
    
    # Initialize agents with current directory as data_dir
    fundamental_agent = FundamentalAgent(data_dir=".")
    valuation_agent = ValuationAgent(data_dir=".")
    sentiment_agent = SentimentAgent(data_dir=".")
    
    # Process full 9 months
    start_date = datetime.strptime("2025-01-02", "%Y-%m-%d")
    end_date = datetime.strptime("2025-09-18", "%Y-%m-%d")
    dates = []
    current_date = start_date
    
    while current_date <= end_date:
        dates.append(current_date.strftime("%Y-%m-%d"))
        current_date += timedelta(days=1)
    
    results = []
    for date in dates:
        result = process_single_day(
            date=date,
            stock_data=stock_data,
            news_data=news_data,
            fundamental_agent=fundamental_agent,
            valuation_agent=valuation_agent,
            sentiment_agent=sentiment_agent
        )
        if result:
            results.append(result)
    
    print("\n✨ Analysis complete!")
    print(f"Processed {len(results)} days successfully")

if __name__ == "__main__":
    main()

