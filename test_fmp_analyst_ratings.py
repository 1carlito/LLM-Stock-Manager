"""
Test FMP Analyst Ratings API
============================

This script tests the FMP API connection and shows example usage.
"""

import os
from fmp_analyst_ratings import FMPAnalystRatings

def test_fmp_connection():
    """Test FMP API connection"""
    
    # Get API key
    api_key = os.getenv('FMP_API_KEY')
    if not api_key:
        print("❌ FMP_API_KEY environment variable not set")
        print("Please set your FMP API key:")
        print("export FMP_API_KEY='your_api_key_here'")
        return False
    
    print("✅ FMP API key found")
    
    # Initialize fetcher
    fetcher = FMPAnalystRatings(api_key)
    
    # Test with a known stock (AAPL)
    print("\n🔍 Testing with AAPL...")
    
    try:
        # Test price target news
        price_target_news = fetcher.get_price_target_news('AAPL', limit=5)
        print(f"✅ Price target news: {len(price_target_news)} items found")
        
        if price_target_news:
            print("📋 Sample price target news:")
            for i, news in enumerate(price_target_news[:2]):
                print(f"   {i+1}. {news.get('analystCompany', 'Unknown')} - ${news.get('priceTarget', 0):.2f}")
                print(f"      Date: {news.get('publishedDate', 'Unknown')}")
                print(f"      Title: {news.get('newsTitle', 'Unknown')[:80]}...")
        
        # Test grades
        grades = fetcher.get_grades('AAPL')
        print(f"✅ Grades: {len(grades)} items found")
        
        # Test price target consensus
        consensus = fetcher.get_price_target_consensus('AAPL')
        print(f"✅ Price target consensus: {len(consensus)} items found")
        
        if consensus:
            print("🎯 Sample consensus:")
            for item in consensus:
                print(f"   High: ${item.get('targetHigh', 0):.2f}")
                print(f"   Low: ${item.get('targetLow', 0):.2f}")
                print(f"   Consensus: ${item.get('targetConsensus', 0):.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

def show_usage_examples():
    """Show usage examples"""
    
    print("\n📚 USAGE EXAMPLES:")
    print("=" * 50)
    
    examples = [
        ("Fetch all analyst ratings", "python fmp_analyst_ratings.py"),
        ("Test API connection", "python test_fmp_analyst_ratings.py"),
        ("Set API key", "export FMP_API_KEY='your_api_key_here'"),
    ]
    
    for description, command in examples:
        print(f"\n{description}:")
        print(f"  {command}")

def main():
    """Main test function"""
    
    print("🧪 FMP Analyst Ratings API Test")
    print("=" * 50)
    
    success = test_fmp_connection()
    
    if success:
        print("\n✅ API connection successful!")
        show_usage_examples()
    else:
        print("\n❌ API connection failed. Please check your API key.")

if __name__ == "__main__":
    main() 