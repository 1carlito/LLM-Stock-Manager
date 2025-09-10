"""
Automated Stock Prediction Scheduler
===================================

This script automates the running of stock predictions at scheduled intervals.
It can be configured to run daily, weekly, or on specific market conditions.
"""

import schedule
import time
import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import subprocess
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PredictionScheduler:
    """Automated scheduler for stock predictions"""
    
    def __init__(self, config_file: str = "scheduler_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        self.batch_script = "batch_stock_predictor.py"
        self.results_dir = "batch_predictions"
        
        # Create results directory if it doesn't exist
        Path(self.results_dir).mkdir(exist_ok=True)
        
        logger.info("Prediction Scheduler initialized")
    
    def load_config(self) -> Dict[str, Any]:
        """Load scheduler configuration"""
        default_config = {
            "schedule_type": "daily",  # daily, weekly, market_hours, custom
            "daily_time": "09:30",     # Time to run daily predictions (market open)
            "weekly_day": "monday",    # Day of week for weekly predictions
            "weekly_time": "09:30",    # Time for weekly predictions
            "market_hours_only": True, # Only run during market hours
            "market_open": "09:30",    # Market open time
            "market_close": "16:00",   # Market close time
            "custom_schedule": [],     # Custom schedule entries
            "enabled_stocks": [],      # Empty = all stocks, or specific symbols
            "max_concurrent": 5,      # Max concurrent processing
            "retry_failed": True,     # Retry failed predictions
            "max_retries": 3,         # Maximum retry attempts
            "notifications": {
                "email": False,
                "slack": False,
                "webhook": False
            },
            "data_retention_days": 30, # Keep results for X days
            "cleanup_old_results": True,
            "manual_mode_only": False, # Prevent automatic scheduling
            "auto_scheduling_disabled": False # Prevent automatic scheduling
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                    # Merge user config with defaults
                    default_config.update(user_config)
                    logger.info(f"Loaded configuration from {self.config_file}")
            except Exception as e:
                logger.error(f"Error loading config: {e}, using defaults")
        else:
            # Save default config
            self.save_config(default_config)
            logger.info(f"Created default configuration file: {self.config_file}")
        
        return default_config
    
    def save_config(self, config: Dict[str, Any]):
        """Save scheduler configuration"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info("Configuration saved")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def is_market_open(self) -> bool:
        """Check if market is currently open"""
        if not self.config["market_hours_only"]:
            return True
        
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        # Simple market hours check (9:30 AM - 4:00 PM ET, Monday-Friday)
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        return self.config["market_open"] <= current_time <= self.config["market_close"]
    
    def run_predictions(self, symbols: List[str] = None):
        """Run batch predictions"""
        try:
            logger.info("Starting automated batch predictions")
            
            # Check if market is open (if configured)
            if not self.is_market_open():
                logger.info("Market is closed, skipping predictions")
                return
            
            # Prepare command
            cmd = [sys.executable, self.batch_script]
            
            # Add specific symbols if provided
            if symbols:
                cmd.extend(["--symbols"] + symbols)
            
            # Add max concurrent parameter
            cmd.extend(["--max-concurrent", str(self.config["max_concurrent"])])
            
            logger.info(f"Running command: {' '.join(cmd)}")
            
            # Run the batch predictor
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode == 0:
                logger.info("Batch predictions completed successfully")
                logger.info(f"Output: {result.stdout}")
            else:
                logger.error(f"Batch predictions failed: {result.stderr}")
                
                # Retry logic
                if self.config["retry_failed"]:
                    self.retry_failed_predictions(symbols)
                    
        except subprocess.TimeoutExpired:
            logger.error("Batch predictions timed out")
        except Exception as e:
            logger.error(f"Error running predictions: {e}")
    
    def retry_failed_predictions(self, symbols: List[str] = None):
        """Retry failed predictions"""
        max_retries = self.config["max_retries"]
        
        for attempt in range(1, max_retries + 1):
            logger.info(f"Retry attempt {attempt}/{max_retries}")
            
            try:
                time.sleep(300)  # Wait 5 minutes before retry
                self.run_predictions(symbols)
                break
            except Exception as e:
                logger.error(f"Retry attempt {attempt} failed: {e}")
                if attempt == max_retries:
                    logger.error("Max retries reached, giving up")
    
    def cleanup_old_results(self):
        """Clean up old prediction results"""
        if not self.config["cleanup_old_results"]:
            return
        
        try:
            retention_days = self.config["data_retention_days"]
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            results_dir = Path(self.results_dir)
            if not results_dir.exists():
                return
            
            files_removed = 0
            for file_path in results_dir.rglob("*"):
                if file_path.is_file():
                    file_age = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_age < cutoff_date:
                        file_path.unlink()
                        files_removed += 1
            
            if files_removed > 0:
                logger.info(f"Cleaned up {files_removed} old result files")
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def setup_schedule(self):
        """Setup the scheduling based on configuration"""
        # Safety check - prevent automatic scheduling if manual mode is enabled
        if self.config.get("manual_mode_only", False) or self.config.get("auto_scheduling_disabled", False):
            logger.warning("⚠️  AUTOMATIC SCHEDULING IS DISABLED - Manual mode only")
            logger.warning("   To run predictions, use: python manage_predictions.py run-once")
            logger.warning("   To enable scheduling, set 'manual_mode_only': false in config")
            return False
        
        # Clear any existing schedules
        schedule.clear()
        
        schedule_type = self.config["schedule_type"]
        
        if schedule_type == "daily":
            daily_time = self.config["daily_time"]
            if daily_time:
                schedule.every().day.at(daily_time).do(self.run_predictions)
                logger.info(f"Daily schedule set for {daily_time}")
        
        elif schedule_type == "weekly":
            weekly_day = self.config["weekly_day"]
            weekly_time = self.config["weekly_time"]
            if weekly_day and weekly_time:
                getattr(schedule.every(), weekly_day.lower()).at(weekly_time).do(self.run_predictions)
                logger.info(f"Weekly schedule set for {weekly_day} at {weekly_time}")
        
        elif schedule_type == "market_hours":
            # Run every hour during market hours
            schedule.every().hour.do(self.run_predictions_if_market_open)
            logger.info("Market hours schedule set (every hour during market hours)")
        
        elif schedule_type == "custom":
            for custom_entry in self.config["custom_schedule"]:
                # Handle custom schedule entries
                pass
            logger.info("Custom schedule configured")
        
        else:
            logger.warning(f"Unknown schedule type: {schedule_type}")
            return False
        
        return True
    
    def run_once(self, symbols: List[str] = None):
        """Run predictions once immediately"""
        logger.info("Running predictions once")
        self.run_predictions(symbols)
    
    def start_scheduler(self):
        """Start the automated scheduler"""
        logger.info("Starting automated prediction scheduler")
        
        # Safety check - prevent automatic scheduling if manual mode is enabled
        if self.config.get("manual_mode_only", False) or self.config.get("auto_scheduling_disabled", False):
            logger.warning("⚠️  AUTOMATIC SCHEDULING IS DISABLED - Manual mode only")
            logger.warning("   To run predictions, use: python manage_predictions.py run-once")
            logger.warning("   To enable scheduling, set 'manual_mode_only': false in config")
            return False
        
        # Setup schedule
        if not self.setup_schedule():
            logger.error("Failed to setup schedule")
            return False
        
        # Run initial predictions if market is open
        if self.is_market_open():
            logger.info("Market is open, running initial predictions")
            self.run_predictions()
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status"""
        return {
            "status": "running" if schedule.jobs else "stopped",
            "next_run": str(schedule.next_run()) if schedule.jobs else "None",
            "total_jobs": len(schedule.jobs),
            "market_open": self.is_market_open(),
            "config": self.config
        }

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Automated Stock Prediction Scheduler")
    parser.add_argument("--run-once", action="store_true", help="Run predictions once and exit")
    parser.add_argument("--symbols", nargs="+", help="Specific stock symbols to predict")
    parser.add_argument("--status", action="store_true", help="Show scheduler status")
    parser.add_argument("--config", default="scheduler_config.json", help="Configuration file path")
    
    args = parser.parse_args()
    
    # Initialize scheduler
    scheduler = PredictionScheduler(args.config)
    
    if args.status:
        status = scheduler.get_status()
        print(json.dumps(status, indent=2))
        return
    
    if args.run_once:
        scheduler.run_once(args.symbols)
    else:
        scheduler.start_scheduler()

if __name__ == "__main__":
    main() 