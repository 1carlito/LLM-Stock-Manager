#!/usr/bin/env python3

with open('FundamentalAgent.py', 'r') as f:
    content = f.read()

# Replace the _load_stock_data method with the corrected version
old_method = """    def _load_stock_data(self, symbol: str, current_date: str = None) -> Optional[Dict]:
        \"\"\"Load stock data from file\"\"\"
        try:
            # Load stock data from new location"""

new_method = """    def _load_stock_data(self, symbol: str, current_date: str = None) -> Optional[Dict]:
        \"\"\"Load stock data from file\"\"\"
        try:
            # Convert current_date to datetime if provided
            analysis_date = self.cutoff_date
            if current_date:
                if isinstance(current_date, str):
                    analysis_date = datetime.strptime(current_date, '%Y-%m-%d')
                else:
                    analysis_date = current_date
                    
            # Load stock data from new location"""

updated_content = content.replace(old_method, new_method)

with open('FundamentalAgent.py', 'w') as f:
    f.write(updated_content)

print("FundamentalAgent.py updated with properly indented current_date handling code.")
