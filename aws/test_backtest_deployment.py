#!/usr/bin/env python3
"""
Test script for AWS backtest deployment.
Tests file loading, data filtering, and backtest execution.
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List

def test_directory_structure(data_dir: str = "/home/ubuntu") -> bool:
    """Test that required directories exist and contain data."""
    print("Testing directory structure...")
    
    required_dirs = [
        "valuation_reports",
        "fundamental_reports", 
        "sentiment_data",
        "news_data"
    ]
    
    all_good = True
    for dir_name in required_dirs:
        dir_path = os.path.join(data_dir, dir_name)
        if not os.path.exists(dir_path):
            print(f"❌ Missing directory: {dir_path}")
            all_good = False
        else:
            files = os.listdir(dir_path)
            json_files = [f for f in files if f.endswith('.json')]
            print(f"✓ {dir_name}: {len(json_files)} JSON files found")
    
    return all_good

def test_analysis_files(data_dir: str = "/home/ubuntu") -> bool:
    """Test loading and parsing analysis files."""
    print("\nTesting analysis file loading...")
    
    # Test symbols
    test_symbols = ["GOOGL", "NVDA", "AAPL"]
    
    for symbol in test_symbols:
        print(f"\nTesting {symbol}:")
        
        # Test valuation files
        val_pattern = os.path.join(data_dir, "valuation_reports", f"{symbol}_technical_analysis_*.json")
        import glob
        val_files = glob.glob(val_pattern)
        
        if val_files:
            latest_val = max(val_files, key=os.path.getctime)
            try:
                with open(latest_val, 'r') as f:
                    val_data = json.load(f)
                    date = val_data.get('date', 'No date')
                    price = val_data.get('current_price', 'No price')
                    print(f"  ✓ Valuation: {os.path.basename(latest_val)} (date: {date}, price: ${price})")
            except Exception as e:
                print(f"  ❌ Error loading valuation: {str(e)}")
        else:
            print(f"  ❌ No valuation files found for {symbol}")
        
        # Test fundamental files
        fund_pattern = os.path.join(data_dir, "fundamental_reports", f"{symbol}_fundamental_analysis_*.json")
        fund_files = glob.glob(fund_pattern)
        
        if fund_files:
            latest_fund = max(fund_files, key=os.path.getctime)
            try:
                with open(latest_fund, 'r') as f:
                    fund_data = json.load(f)
                    date = fund_data.get('date', 'No date')
                    print(f"  ✓ Fundamental: {os.path.basename(latest_fund)} (date: {date})")
            except Exception as e:
                print(f"  ❌ Error loading fundamental: {str(e)}")
        else:
            print(f"  ❌ No fundamental files found for {symbol}")
        
        # Test sentiment files
        sent_pattern = os.path.join(data_dir, "sentiment_data", f"{symbol}_sentiment_analysis_*.json")
        sent_files = glob.glob(sent_pattern)
        
        if sent_files:
            latest_sent = max(sent_files, key=os.path.getctime)
            try:
                with open(latest_sent, 'r') as f:
                    sent_data = json.load(f)
                    date = sent_data.get('date', 'No date')
                    print(f"  ✓ Sentiment: {os.path.basename(latest_sent)} (date: {date})")
            except Exception as e:
                print(f"  ❌ Error loading sentiment: {str(e)}")
        else:
            print(f"  ❌ No sentiment files found for {symbol}")
    
    return True

def test_date_filtering(data_dir: str = "/home/ubuntu") -> bool:
    """Test date filtering functionality."""
    print("\nTesting date filtering...")
    
    # Import the backtest orchestrator
    try:
        from backtest_orchestrator import BacktestOrchestrator
        
        orchestrator = BacktestOrchestrator(data_dir=data_dir)
        
        # Test date filtering for a specific symbol and date
        test_symbol = "GOOGL"
        test_date = "2025-06-12"
        
        print(f"Testing date filtering for {test_symbol} on {test_date}")
        
        # Test valuation analysis
        valuation = orchestrator._get_latest_analysis_before_date(
            test_symbol, 'technical', 'valuation_reports', test_date
        )
        
        if valuation:
            file_date = valuation.get('date', 'No date')
            print(f"  ✓ Valuation analysis found (date: {file_date})")
            if file_date <= test_date:
                print(f"    ✓ Date filter working correctly")
            else:
                print(f"    ❌ Date filter failed: {file_date} > {test_date}")
        else:
            print(f"  ❌ No valuation analysis found for {test_symbol}")
        
        # Test fundamental analysis
        fundamental = orchestrator._get_latest_analysis_before_date(
            test_symbol, 'fundamental', 'fundamental_reports', test_date
        )
        
        if fundamental:
            file_date = fundamental.get('date', 'No date')
            print(f"  ✓ Fundamental analysis found (date: {file_date})")
        else:
            print(f"  ❌ No fundamental analysis found for {test_symbol}")
        
        # Test sentiment analysis
        sentiment = orchestrator._get_latest_analysis_before_date(
            test_symbol, 'sentiment', 'sentiment_data', test_date
        )
        
        if sentiment:
            file_date = sentiment.get('date', 'No date')
            print(f"  ✓ Sentiment analysis found (date: {file_date})")
        else:
            print(f"  ❌ No sentiment analysis found for {test_symbol}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing date filtering: {str(e)}")
        return False

def test_mini_backtest(data_dir: str = "/home/ubuntu") -> bool:
    """Run a mini backtest with one symbol for one day."""
    print("\nTesting mini backtest...")
    
    try:
        from backtest_orchestrator import BacktestOrchestrator
        
        orchestrator = BacktestOrchestrator(data_dir=data_dir)
        
        # Run backtest for just one symbol for one day
        test_symbols = ["GOOGL"]
        start_date = "2025-06-12"
        end_date = "2025-06-12"
        
        print(f"Running mini backtest for {test_symbols} from {start_date} to {end_date}")
        
        orchestrator.run_workflow(test_symbols, start_date=start_date, end_date=end_date)
        
        # Check if results were saved
        results_file = os.path.join(data_dir, 'backtest_results.json')
        if os.path.exists(results_file):
            with open(results_file, 'r') as f:
                results = json.load(f)
            print(f"  ✓ Results saved successfully")
            print(f"  ✓ Final value: ${results.get('final_value', 0):,.2f}")
            print(f"  ✓ Total trades: {results.get('total_trades', 0)}")
            return True
        else:
            print(f"  ❌ Results file not found: {results_file}")
            return False
            
    except Exception as e:
        print(f"❌ Error in mini backtest: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("=== AWS Backtest Deployment Test ===\n")
    
    # Get data directory from environment or use default
    data_dir = os.getenv("DATA_DIR", "/home/ubuntu")
    print(f"Using data directory: {data_dir}")
    
    # Run tests
    tests = [
        ("Directory Structure", lambda: test_directory_structure(data_dir)),
        ("Analysis Files", lambda: test_analysis_files(data_dir)),
        ("Date Filtering", lambda: test_date_filtering(data_dir)),
        ("Mini Backtest", lambda: test_mini_backtest(data_dir)),
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running {test_name} Test")
        print('='*50)
        
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {str(e)}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print('='*50)
    
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 All tests passed! The backtest should work on AWS.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 