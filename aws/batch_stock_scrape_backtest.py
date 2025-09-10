#!/usr/bin/env python3
"""
Batch Stock Data Scraper for Backtesting
=======================================

This script collects comprehensive stock data for a predefined list of 50 stocks,
saving it in a format suitable for backtesting trading strategies.
It collects multiple types of data to provide a richer dataset for analysis.
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
import argparse
from typing import Dict, List, Any, Optional, Union
from dotenv import load_dotenv
from StockData_FmpApi import StockDataFmpApi, save_stock_data

# Pre-defined list of stocks by sector (matched with llm_news_search.py)
STOCKS_BY_SECTOR = {
    "Technology": [
    "GOOGL","NVDA", "PLTR",
    ],
    "Health_and_Pharma": [
    "ABBV", "TMO", "UNH"
    ],
    "Financial_Services": [
    "JPM", "BAC", "WFC"
    ],
    "Energy": [
    "XOM", "CVX", "COP"
    ]
}

# Flatten the list for convenience
ALL_STOCKS = [stock for sector_stocks in STOCKS_BY_SECTOR.values() for stock in sector_stocks]

class BatchStockScraper:
    """Batch processor for collecting stock data for multiple stocks"""
    
    def __init__(self, api_key: str = None, output_dir: str = "backtest_data"):
        """
        Initialize the batch stock scraper
        
        Args:
            api_key: FMP API key (if None, load from environment)
            output_dir: Directory to save output data
        """
        # Load environment variables if needed
        load_dotenv()
        
        # Set up API client
        self.api_key = api_key or os.getenv('FMP_API_KEY')
        if not self.api_key:
            raise ValueError("No API key provided and FMP_API_KEY environment variable not set")
        
        self.api_client = StockDataFmpApi(self.api_key)
        
        # Set up output directory
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Logging
        self.log_file = os.path.join(self.output_dir, "batch_log.txt")
        
        # Data collections
        self.stock_data = {}
        self.financial_data = {}
        self.ratios_data = {}
        self.market_data = {}
        
    def log(self, message: str):
        """Log a message to both console and log file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        
        with open(self.log_file, 'a') as f:
            f.write(log_message + "\n")
    
    def fetch_batch_with_retry(self, symbols: List[str], 
                               from_date: str = None, 
                               to_date: str = None,
                               historical_days: int = 365,
                               max_retries: int = 3,
                               batch_size: int = 5,
                               delay_between_stocks: float = 1.0,
                               delay_between_batches: float = 5.0) -> Dict[str, Any]:
        """
        Fetch data for multiple stocks with retries and batch processing
        
        Args:
            symbols: List of stock symbols to fetch
            from_date: Start date in YYYY-MM-DD format
            to_date: End date in YYYY-MM-DD format
            historical_days: Number of days of historical data if no date range
            max_retries: Maximum number of retry attempts for failed requests
            batch_size: Number of stocks to process in each batch
            delay_between_stocks: Seconds to wait between individual API calls
            delay_between_batches: Seconds to wait between batches
            
        Returns:
            Dictionary of stock data keyed by symbol
        """
        results = {}
        failed_symbols = []
        
        # Process stocks in batches
        total_batches = (len(symbols) + batch_size - 1) // batch_size
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min((batch_idx + 1) * batch_size, len(symbols))
            batch_symbols = symbols[start_idx:end_idx]
            
            self.log(f"Processing batch {batch_idx + 1}/{total_batches} ({len(batch_symbols)} stocks)")
            
            # Process each stock in the batch
            for symbol in batch_symbols:
                retries = 0
                success = False
                
                while retries < max_retries and not success:
                    try:
                        if retries > 0:
                            self.log(f"Retry {retries}/{max_retries} for {symbol}")
                            # Exponential backoff for retries
                            time.sleep(delay_between_stocks * (2 ** retries))
                        
                        self.log(f"Fetching data for {symbol}")
                        stock_data = self.api_client.fetch_stock_data(
                            symbol=symbol,
                            historical_days=historical_days,
                            from_date=from_date,
                            to_date=to_date
                        )
                        
                        if stock_data:
                            results[symbol] = stock_data
                            success = True
                            self.log(f"✅ Successfully fetched data for {symbol}")
                        else:
                            self.log(f"⚠️ No data returned for {symbol}")
                            retries += 1
                        
                    except Exception as e:
                        self.log(f"❌ Error fetching data for {symbol}: {str(e)}")
                        retries += 1
                
                if not success:
                    self.log(f"❌ Failed to fetch data for {symbol} after {max_retries} attempts")
                    failed_symbols.append(symbol)
                
                # Delay between individual stocks
                if symbol != batch_symbols[-1]:  # Don't delay after last stock in batch
                    time.sleep(delay_between_stocks)
            
            # Delay between batches
            if batch_idx < total_batches - 1:  # Don't delay after last batch
                self.log(f"Waiting {delay_between_batches} seconds before next batch...")
                time.sleep(delay_between_batches)
        
        # Log summary
        self.log(f"Batch processing complete: {len(results)}/{len(symbols)} stocks successful")
        if failed_symbols:
            self.log(f"Failed symbols: {', '.join(failed_symbols)}")
        
        return results
    
    def fetch_financial_data(self, symbols: List[str], period: str = 'quarter', limit: int = 4) -> Dict[str, List[Dict]]:
        """Fetch financial statement data for multiple stocks"""
        results = {}
        
        for symbol in symbols:
            try:
                self.log(f"Fetching financial data for {symbol}")
                # Get income statement
                income_data = self.api_client._make_request("income-statement", {
                    'symbol': symbol,
                    'period': period,
                    'limit': limit
                })
                
                # Get balance sheet
                balance_data = self.api_client._make_request("balance-sheet-statement", {
                    'symbol': symbol,
                    'period': period,
                    'limit': limit
                })
                
                # Get cash flow
                cashflow_data = self.api_client._make_request("cash-flow-statement", {
                    'symbol': symbol,
                    'period': period,
                    'limit': limit
                })
                
                results[symbol] = {
                    'income_statement': income_data,
                    'balance_sheet': balance_data,
                    'cash_flow': cashflow_data
                }
                
                self.log(f"✅ Successfully fetched financial data for {symbol}")
                time.sleep(1.0)  # Delay to avoid rate limiting
                
            except Exception as e:
                self.log(f"❌ Error fetching financial data for {symbol}: {str(e)}")
        
        return results
    
    def fetch_market_data(self) -> Dict[str, Any]:
        """Fetch overall market data like sector performance and indexes"""
        results = {}
        
        try:
            # Get market indexes
            self.log("Fetching market indexes")
            indexes = self.api_client.get_market_indexes()
            results['market_indexes'] = indexes
            
            # Get sector performance
            self.log("Fetching sector performance")
            sectors = self.api_client.get_sector_performance()
            results['sector_performance'] = sectors
            
            self.log(f"✅ Successfully fetched market data")
            
        except Exception as e:
            self.log(f"❌ Error fetching market data: {str(e)}")
        
        return results
    
    def run_batch_collection(self, 
                          symbols: List[str] = None, 
                          from_date: str = None,
                          to_date: str = None,
                          historical_days: int = 365,
                          include_financials: bool = True,
                          include_market_data: bool = True) -> bool:
        """
        Run a complete batch collection process
        
        Args:
            symbols: List of stock symbols (default: use predefined 50 stocks)
            from_date: Start date for historical data
            to_date: End date for historical data
            historical_days: Days of history if no date range specified
            include_financials: Whether to include financial statement data
            include_market_data: Whether to include market/sector data
            
        Returns:
            True if successful, False otherwise
        """
        # Use default stocks if none provided
        if symbols is None:
            symbols = ALL_STOCKS
        
        # Create timestamp for this run
        run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # Step 1: Fetch stock price and metrics data
            self.log(f"Starting batch collection for {len(symbols)} stocks")
            if from_date and to_date:
                self.log(f"Date range: {from_date} to {to_date}")
            else:
                self.log(f"Historical days: {historical_days}")
            
            self.stock_data = self.fetch_batch_with_retry(
                symbols=symbols,
                from_date=from_date,
                to_date=to_date,
                historical_days=historical_days
            )
            
            # Step 2: Fetch financial data if requested
            if include_financials:
                self.log("Fetching financial statement data")
                self.financial_data = self.fetch_financial_data(symbols)
            
            # Step 3: Fetch market data if requested
            if include_market_data:
                self.log("Fetching market data")
                self.market_data = self.fetch_market_data()
            
            # Step 4: Save all collected data
            self.save_batch_data(run_timestamp)
            
            self.log(f"Batch collection completed successfully")
            return True
            
        except Exception as e:
            self.log(f"❌ Error in batch collection: {str(e)}")
            # Try to save what we have so far
            self.save_batch_data(run_timestamp)
            return False
    
    def save_batch_data(self, timestamp: str):
        """Save all collected data to files"""
        # Save stock data
        if self.stock_data:
            stock_data_file = os.path.join(self.output_dir, f"stock_data_{timestamp}.json")
            save_stock_data(self.stock_data, stock_data_file)
        
        # Save financial data
        if self.financial_data:
            financial_data_file = os.path.join(self.output_dir, f"financial_data_{timestamp}.json")
            with open(financial_data_file, 'w') as f:
                json.dump(self.financial_data, f, indent=2)
            self.log(f"💾 Financial data saved to {financial_data_file}")
        
        # Save market data
        if self.market_data:
            market_data_file = os.path.join(self.output_dir, f"market_data_{timestamp}.json")
            with open(market_data_file, 'w') as f:
                json.dump(self.market_data, f, indent=2)
            self.log(f"💾 Market data saved to {market_data_file}")
        
        # Create metadata file
        metadata = {
            'collection_date': timestamp,
            'stocks_count': len(self.stock_data),
            'stocks': list(self.stock_data.keys()),
            'has_financials': bool(self.financial_data),
            'has_market_data': bool(self.market_data),
        }
        
        metadata_file = os.path.join(self.output_dir, f"metadata_{timestamp}.json")
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        self.log(f"📝 Collection metadata saved to {metadata_file}")

def parse_date(date_str: str) -> str:
    """Parse date string to ensure YYYY-MM-DD format"""
    if not date_str:
        return None
    
    # Handle various date formats
    try:
        # Try direct parsing (assuming YYYY-MM-DD)
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        try:
            # Try with slashes (MM/DD/YYYY)
            dt = datetime.strptime(date_str, "%m/%d/%Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            try:
                # Try month name format (Jun 1, 2023)
                dt = datetime.strptime(date_str, "%b %d, %Y")
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                raise ValueError(f"Unsupported date format: {date_str}")

def main():
    """Main function to run batch stock data collection"""
    parser = argparse.ArgumentParser(description="Batch Stock Data Collection for Backtesting")
    
    # Basic options
    parser.add_argument("--sector", choices=list(STOCKS_BY_SECTOR.keys()),
                      help="Only collect data for a specific sector")
    parser.add_argument("--symbols", nargs="+", help="Specific stock symbols to collect")
    parser.add_argument("--output-dir", default="backtest_data",
                      help="Directory to save output data")
    
    # Date range options
    parser.add_argument("--from-date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--to-date", help="End date (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, default=365,
                      help="Number of historical days (default: 365)")
    parser.add_argument("--last-month", action="store_true",
                      help="Collect data for the last month")
    parser.add_argument("--last-quarter", action="store_true",
                      help="Collect data for the last quarter")
    parser.add_argument("--last-year", action="store_true",
                      help="Collect data for the last year")
    
    # Data type options
    parser.add_argument("--no-financials", action="store_true",
                      help="Skip collecting financial statement data")
    parser.add_argument("--no-market-data", action="store_true",
                      help="Skip collecting market and sector data")
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Check API key
    api_key = os.getenv('FMP_API_KEY')
    if not api_key:
        print("❌ FMP_API_KEY environment variable not set")
        print("Please set your API key: export FMP_API_KEY='your_api_key'")
        sys.exit(1)
    
    # Determine which stocks to collect
    symbols = None
    if args.symbols:
        symbols = [s.upper() for s in args.symbols]
    elif args.sector:
        symbols = STOCKS_BY_SECTOR[args.sector]
    
    # Determine date range
    from_date = None
    to_date = None
    historical_days = args.days
    
    today = datetime.now()
    
    if args.last_month:
        to_date = today.strftime("%Y-%m-%d")
        from_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    elif args.last_quarter:
        to_date = today.strftime("%Y-%m-%d")
        from_date = (today - timedelta(days=90)).strftime("%Y-%m-%d")
    elif args.last_year:
        to_date = today.strftime("%Y-%m-%d")
        from_date = (today - timedelta(days=365)).strftime("%Y-%m-%d")
    elif args.from_date or args.to_date:
        if args.from_date:
            from_date = parse_date(args.from_date)
        if args.to_date:
            to_date = parse_date(args.to_date)
    
    # Create scraper and run batch collection
    try:
        scraper = BatchStockScraper(api_key=api_key, output_dir=args.output_dir)
        
        success = scraper.run_batch_collection(
            symbols=symbols,
            from_date=from_date,
            to_date=to_date,
            historical_days=historical_days,
            include_financials=not args.no_financials,
            include_market_data=not args.no_market_data
        )
        
        if not success:
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 