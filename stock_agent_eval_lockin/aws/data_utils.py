"""
Shared utilities for data loading and management across agents
"""

import os
import json
from typing import Dict, Optional, List
from datetime import datetime
from glob import glob

class DataManager:
    """
    Centralized data management for stock analysis agents.
    Handles finding and loading the latest data files.
    """
    
    def __init__(self, base_dir: str = "."):
        """
        Initialize the DataManager
        
        Args:
            base_dir: Base directory for data files (defaults to current directory)
        """
        self.base_dir = base_dir
        
    def get_latest_data_file(self, symbol: Optional[str] = None) -> Optional[str]:
        """
        Find the latest data file for a symbol or latest overall data file
        
        Args:
            symbol: Optional stock symbol to search for
            
        Returns:
            Path to latest data file or None if not found
        """
        # Patterns to search for
        patterns = []
        if symbol:
            # Look for symbol-specific files first
            patterns.extend([
                f"{symbol.lower()}_*.json",
                f"{symbol.upper()}_*.json",
            ])
        # Also look for general stock data files
        patterns.append("stock_data_*.json")
        
        latest_file = None
        latest_timestamp = None
        
        for pattern in patterns:
            # Search in base directory
            search_path = os.path.join(self.base_dir, pattern)
            matching_files = glob(search_path)
            
            for file_path in matching_files:
                try:
                    # Get file modification time
                    file_timestamp = os.path.getmtime(file_path)
                    
                    # Update if this is the latest file seen
                    if latest_timestamp is None or file_timestamp > latest_timestamp:
                        latest_timestamp = file_timestamp
                        latest_file = file_path
                except Exception as e:
                    print(f"Error checking file {file_path}: {str(e)}")
                    continue
        
        return latest_file
    
    def load_stock_data(self, symbol: str) -> Optional[Dict]:
        """
        Load latest stock data for a symbol
        
        Args:
            symbol: Stock symbol to load data for
            
        Returns:
            Dictionary containing stock data or None if not found
        """
        latest_file = self.get_latest_data_file(symbol)
        if not latest_file:
            print(f"No data file found for {symbol}")
            return None
            
        try:
            print(f"Loading data from {latest_file}")
            with open(latest_file, 'r') as f:
                data = json.load(f)
                
            # Handle both single-stock and multi-stock files
            if symbol in data:
                return data[symbol]
            elif isinstance(data, dict) and len(data) == 1:
                # Single stock file
                return list(data.values())[0]
            else:
                print(f"Could not find data for {symbol} in {latest_file}")
                return None
                
        except Exception as e:
            print(f"Error loading data from {latest_file}: {str(e)}")
            return None
            
    def save_analysis_result(self, 
                           symbol: str, 
                           analysis_data: Dict,
                           analysis_type: str,
                           output_dir: str) -> str:
        """
        Save analysis results in a standardized format
        
        Args:
            symbol: Stock symbol
            analysis_data: Analysis data to save
            analysis_type: Type of analysis (e.g., 'sentiment', 'technical', 'fundamental')
            output_dir: Directory to save results in
            
        Returns:
            Path to saved file
        """
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{symbol}_{analysis_type}_analysis_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        
        try:
            with open(filepath, 'w') as f:
                json.dump(analysis_data, f, indent=2)
            print(f"Analysis saved to {filepath}")
            return filepath
        except Exception as e:
            print(f"Error saving analysis to {filepath}: {str(e)}")
            return "" 