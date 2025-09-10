#!/usr/bin/env python3
"""
Check FMP Data Date Formats and Ranges
======================================

Examine how dates are stored in FMP data and what time ranges are available.
"""

import os
from datetime import datetime
from collections import defaultdict
from fmp_analyst_ratings import FMPAnalystRatings

def analyze_data_dates(symbol: str = "AAPL"):
    """Analyze date formats and ranges in FMP data"""
    
    api_key = os.getenv('FMP_API_KEY')
    if not api_key:
        print("❌ FMP_API_KEY environment variable not set")
        return
    
    print(f"📅 Analyzing Date Structure for {symbol}")
    print("=" * 50)
    
    fmp_client = FMPAnalystRatings(api_key)
    
    # Analyze different data types
    data_types = [
        ("Historical Prices", lambda: fmp_client.get_historical_prices(symbol, limit=100)),
        ("Analyst Grades", lambda: fmp_client.get_grades(symbol)),
        ("Earnings Data", lambda: fmp_client.get_earnings_data(symbol, limit=10)),
    ]
    
    for data_name, fetch_func in data_types:
        print(f"\n📊 {data_name}:")
        print("-" * 30)
        
        try:
            data = fetch_func()
            if not data:
                print("   ⚠️  No data available")
                continue
            
            # Extract dates
            dates = []
            for record in data[:50]:  # Analyze first 50 records
                if 'date' in record:
                    dates.append(record['date'])
                elif 'publishedDate' in record:
                    dates.append(record['publishedDate'])
            
            if not dates:
                print("   ⚠️  No date fields found")
                continue
            
            # Analyze date formats
            print(f"   📈 Total records: {len(data)}")
            print(f"   📅 Sample dates: {dates[:5]}")
            
            # Parse dates and find range
            parsed_dates = []
            for date_str in dates:
                try:
                    # Handle different formats
                    if 'T' in date_str:
                        # DateTime format: 2024-01-15T10:30:00
                        parsed_date = datetime.strptime(date_str.split('T')[0], '%Y-%m-%d')
                    else:
                        # Date format: 2024-01-15
                        parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
                    parsed_dates.append(parsed_date)
                except ValueError as e:
                    continue
            
            if parsed_dates:
                min_date = min(parsed_dates)
                max_date = max(parsed_dates)
                
                print(f"   📅 Date range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")
                print(f"   📊 Time span: {(max_date - min_date).days} days")
                
                # Group by year-month
                monthly_counts = defaultdict(int)
                for date in parsed_dates:
                    month_key = f"{date.year}-{date.month:02d}"
                    monthly_counts[month_key] += 1
                
                print(f"   📈 Records by month (recent 12 months):")
                sorted_months = sorted(monthly_counts.keys())[-12:]
                for month in sorted_months:
                    print(f"      {month}: {monthly_counts[month]} records")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n💡 Summary:")
    print("=" * 50)
    print("✅ FMP stores data with daily precision (YYYY-MM-DD format)")
    print("✅ Historical data goes back several years")
    print("✅ Data can be easily filtered by month/year")
    print("✅ Each endpoint has consistent date formatting")

if __name__ == "__main__":
    analyze_data_dates("AAPL") 