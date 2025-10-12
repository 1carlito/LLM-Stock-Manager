"""
Fix the FundamentalAgent to load stock data from novo_data.json
"""

import os
import json

def fix_fundamental_agent():
    """Fix the FundamentalAgent to load stock data from novo_data.json."""
    with open("FundamentalAgent.py", "r") as f:
        content = f.read()
    
    # Replace the _load_stock_data method to use novo_data.json
    old_code = """            # Load stock data from valuation data directory
            stock_data_file = os.path.join(self.data_dir, "valuation_data/stock_data_valuation.json")
            print(f"DEBUG: Looking for stock data in: {stock_data_file}")
            
            if not os.path.exists(stock_data_file):
                print(f"❌ Stock data file not found: {stock_data_file}")
                return None
                
            with open(stock_data_file, 'r') as f:
                stock_data = json.load(f)
                
            if symbol not in stock_data:
                print(f"❌ No data found for {symbol}")
                return None"""
    
    new_code = """            # Load stock data from novo_data.json
            stock_data_file = os.path.join(self.data_dir, "novo_data.json")
            print(f"DEBUG: Looking for stock data in: {stock_data_file}")
            
            if not os.path.exists(stock_data_file):
                print(f"❌ Stock data file not found: {stock_data_file}")
                return None
                
            with open(stock_data_file, 'r') as f:
                data = json.load(f)
                
            # Return the data directly since it's already for the symbol
            return data"""
    
    updated_content = content.replace(old_code, new_code)
    
    with open("FundamentalAgent_fixed.py", "w") as f:
        f.write(updated_content)
    
    print("✅ Created fixed FundamentalAgent_fixed.py")

if __name__ == "__main__":
    fix_fundamental_agent()
