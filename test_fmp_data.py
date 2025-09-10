#!/usr/bin/env python3
"""
Test FMP Data Fetching
======================

Simple script to test what FMP data we can actually fetch with the free tier.
NO LLM CALLS - just data fetching and display.
"""

import os
import json
from fmp_analyst_ratings import FMPAnalystRatings

def test_fmp_data(symbol: str = "AAPL"):
    """Test FMP data fetching for a single symbol"""
    
    # Get API key
    api_key = os.getenv('FMP_API_KEY')
    if not api_key:
        print("❌ FMP_API_KEY environment variable not set")
        print("Set it with: export FMP_API_KEY='your_key_here'")
        return
    
    print(f"🧪 Testing FMP Data Fetching for {symbol}")
    print("=" * 50)
    
    # Initialize FMP client
    fmp_client = FMPAnalystRatings(api_key)
    
    # Test each endpoint
    endpoints_to_test = [
        ("Price Target News", lambda: fmp_client.get_price_target_news(symbol, limit=5)),
        ("Latest Price Target News", lambda: fmp_client.get_latest_price_target_news(limit=5)),
        ("Analyst Grades", lambda: fmp_client.get_grades(symbol)),
        ("Company Profile", lambda: fmp_client.get_company_profile(symbol)),
        ("Ratings Snapshot", lambda: fmp_client.get_ratings_snapshot(symbol)),
        ("Historical Prices", lambda: fmp_client.get_historical_prices(symbol, limit=5)),
        ("Earnings Data", lambda: fmp_client.get_earnings_data(symbol, limit=3)),
        ("Income Statement", lambda: fmp_client.get_financial_statements_income(symbol, limit=2)),
        ("Key Metrics", lambda: fmp_client.get_key_metrics(symbol, limit=2)),
    ]
    
    results = {}
    
    for endpoint_name, fetch_func in endpoints_to_test:
        print(f"\n📊 Testing: {endpoint_name}")
        try:
            data = fetch_func()
            if data:
                results[endpoint_name] = data
                print(f"   ✅ Success: Retrieved {len(data)} records")
                # Show first record structure
                if isinstance(data, list) and len(data) > 0:
                    first_record = data[0]
                    if isinstance(first_record, dict):
                        keys = list(first_record.keys())[:5]  # Show first 5 keys
                        print(f"   📋 Sample keys: {keys}")
            else:
                print(f"   ⚠️  No data returned")
                results[endpoint_name] = []
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results[endpoint_name] = {"error": str(e)}
    
    # Summary
    print(f"\n📊 Summary for {symbol}:")
    print("=" * 50)
    
    successful_endpoints = [name for name, data in results.items() 
                          if data and not isinstance(data, dict) and not data.get("error")]
    
    failed_endpoints = [name for name, data in results.items() 
                       if not data or isinstance(data, dict) and data.get("error")]
    
    print(f"✅ Successful endpoints: {len(successful_endpoints)}")
    for endpoint in successful_endpoints:
        count = len(results[endpoint]) if isinstance(results[endpoint], list) else 1
        print(f"   - {endpoint}: {count} records")
    
    print(f"\n❌ Failed endpoints: {len(failed_endpoints)}")
    for endpoint in failed_endpoints:
        print(f"   - {endpoint}")
    
    # Save detailed results
    results_file = f"fmp_test_results_{symbol}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {results_file}")
    
    # Check if we have enough data for predictions
    essential_data = ["Company Profile", "Historical Prices", "Analyst Grades"]
    available_essential = [endpoint for endpoint in essential_data if endpoint in successful_endpoints]
    
    print(f"\n🎯 Essential Data Available: {len(available_essential)}/{len(essential_data)}")
    for endpoint in essential_data:
        status = "✅" if endpoint in successful_endpoints else "❌"
        print(f"   {status} {endpoint}")
    
    if len(available_essential) >= 2:
        print("\n🎉 You have enough data to run basic predictions!")
    else:
        print("\n⚠️  You may need a paid subscription for better prediction quality.")

if __name__ == "__main__":
    test_fmp_data("AAPL") 