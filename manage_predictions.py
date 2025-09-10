#!/usr/bin/env python3
"""
Stock Prediction Management CLI
===============================

Simple command-line interface for managing stock predictions.
"""

import argparse
import sys
import os
from pathlib import Path

def run_batch_predictions(symbols=None, max_concurrent=5):
    """Run batch predictions"""
    try:
        from batch_stock_predictor import BatchStockPredictor
        
        # Get FMP API key
        fmp_api_key = os.getenv('FMP_API_KEY')
        if not fmp_api_key:
            print("❌ FMP_API_KEY environment variable not set")
            print("Please set your FMP API key: export FMP_API_KEY='your_key_here'")
            return False
        
        # Initialize predictor
        predictor = BatchStockPredictor(fmp_api_key, max_concurrent=max_concurrent)
        
        # Run predictions
        import asyncio
        if symbols:
            print(f"🚀 Running predictions for specific symbols: {', '.join(symbols)}")
            # Filter stocks by symbols
            filtered_stocks = [s for s in predictor.stocks_config if s.symbol in symbols]
            predictor.stocks_config = filtered_stocks
        
        print(f"📊 Starting predictions for {len(predictor.stocks_config)} stocks...")
        asyncio.run(predictor.run_batch_predictions())
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all required packages are installed: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Error running predictions: {e}")
        return False

def start_scheduler(config_file="scheduler_config.json"):
    """Start the automated scheduler"""
    try:
        from automated_scheduler import PredictionScheduler
        
        print("🚀 Starting automated prediction scheduler...")
        scheduler = PredictionScheduler(config_file)
        
        # Check if manual mode is enabled
        if scheduler.config.get("manual_mode_only", False) or scheduler.config.get("auto_scheduling_disabled", False):
            print("⚠️  AUTOMATIC SCHEDULING IS DISABLED - Manual mode only")
            print("   To run predictions manually, use: python manage_predictions.py run-once")
            print("   To enable scheduling, edit scheduler_config.json and set 'manual_mode_only': false")
            return False
        
        scheduler.start_scheduler()
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all required packages are installed: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Error starting scheduler: {e}")

def show_status(config_file="scheduler_config.json"):
    """Show scheduler status"""
    try:
        from automated_scheduler import PredictionScheduler
        
        scheduler = PredictionScheduler(config_file)
        status = scheduler.get_status()
        
        print("📊 Scheduler Status:")
        print(f"   Status: {status['status']}")
        print(f"   Next Run: {status['next_run']}")
        print(f"   Total Jobs: {status['total_jobs']}")
        print(f"   Market Open: {status['market_open']}")
        
        print("\n⚙️  Configuration:")
        config = status['config']
        print(f"   Schedule Type: {config['schedule_type']}")
        print(f"   Max Concurrent: {config['max_concurrent']}")
        print(f"   Market Hours Only: {config['market_hours_only']}")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all required packages are installed: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Error getting status: {e}")

def list_stocks():
    """List configured stocks"""
    try:
        from batch_stock_predictor import BatchStockPredictor
        
        # Initialize predictor to load config
        fmp_api_key = os.getenv('FMP_API_KEY', 'dummy_key')
        predictor = BatchStockPredictor(fmp_api_key)
        
        print("📈 Configured Stocks:")
        print(f"{'Symbol':<8} {'Name':<25} {'Sector':<15} {'FMP':<5} {'LLM Providers':<20}")
        print("-" * 80)
        
        for stock in predictor.stocks_config:
            fmp_status = "✅" if stock.fmp_data_enabled else "❌"
            providers = ", ".join(stock.llm_providers[:2]) + ("..." if len(stock.llm_providers) > 2 else "")
            print(f"{stock.symbol:<8} {stock.name:<25} {stock.sector:<15} {fmp_status:<5} {providers:<20}")
        
        print(f"\nTotal: {len(predictor.stocks_config)} stocks")
        
    except Exception as e:
        print(f"❌ Error listing stocks: {e}")

def run_single_stock(symbol):
    """Run predictions for a single stock"""
    if not symbol:
        print("❌ Please provide a stock symbol")
        return False
    
    print(f"📊 Running predictions for {symbol}...")
    return run_batch_predictions([symbol])

def main():
    parser = argparse.ArgumentParser(description="Stock Prediction Management CLI")
    parser.add_argument("command", choices=[
        "run", "run-single", "start-scheduler", "status", "list-stocks", "help"
    ], help="Command to execute")
    
    parser.add_argument("--symbols", nargs="+", help="Stock symbols for run command")
    parser.add_argument("--single-symbol", help="Single stock symbol for run-single command")
    parser.add_argument("--max-concurrent", type=int, default=5, help="Max concurrent processing")
    parser.add_argument("--config", default="scheduler_config.json", help="Scheduler config file")
    
    args = parser.parse_args()
    
    if args.command == "run":
        if not args.symbols:
            print("🚀 Running predictions for all configured stocks...")
            success = run_batch_predictions(max_concurrent=args.max_concurrent)
        else:
            print(f"🚀 Running predictions for specific stocks: {', '.join(args.symbols)}")
            success = run_batch_predictions(args.symbols, args.max_concurrent)
        
        if success:
            print("✅ Predictions completed successfully!")
        else:
            print("❌ Predictions failed!")
            sys.exit(1)
    
    elif args.command == "run-single":
        success = run_single_stock(args.single_symbol)
        if not success:
            sys.exit(1)
    
    elif args.command == "start-scheduler":
        start_scheduler(args.config)
    
    elif args.command == "status":
        show_status(args.config)
    
    elif args.command == "list-stocks":
        list_stocks()
    
    elif args.command == "help":
        print("""
Stock Prediction Management CLI
===============================

⚠️  AUTOMATIC SCHEDULING IS DISABLED - Manual mode only
   This prevents accidental API calls during testing
   To run predictions, use: python manage_predictions.py run

Commands:
  run              Run predictions for all stocks or specific symbols
  run-single       Run predictions for a single stock
  start-scheduler  Start the automated scheduler (DISABLED in manual mode)
  status           Show scheduler status
  list-stocks      List all configured stocks
  help             Show this help message

Examples:
  python manage_predictions.py run                    # Run all 50 stocks
  python manage_predictions.py run --symbols AAPL MSFT GOOGL
  python manage_predictions.py run-single --single-symbol AAPL
  python manage_predictions.py list-stocks            # View configuration

Environment Variables:
  FMP_API_KEY      Your Financial Modeling Prep API key (required)

Note: Automatic scheduling is disabled to prevent API waste during testing.
      Use manual commands to run predictions when you're ready.
        """)

if __name__ == "__main__":
    main() 