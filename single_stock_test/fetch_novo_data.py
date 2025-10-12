"""
Fetch NOVO Data
===================

Fetches stock price, valuation, and fundamental data for NOVO.
"""

import os
import json
from datetime import datetime, timedelta
import sys

# Add parent directory to Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from StockData_FmpApi import StockDataFmpApi

# Date range
FROM_DATE = "2024-11-02"
TO_DATE = "2025-09-18"

def main():
    """Fetch NOVO data."""
    # Set API key
    os.environ['FMP_API_KEY'] = 'ycgZTG3ZghcrJBNwLsqWUckPXyK8sB5Z'
    
    # Initialize API client
    api_client = StockDataFmpApi()
    
    print(f"\nFetching NOVO data from {FROM_DATE} to {TO_DATE}")
    print("=" * 50)
    
    try:
        # Fetch price data
        price_data = api_client.fetch_stock_data(
            symbol="NVO",
            from_date=FROM_DATE,
            to_date=TO_DATE,
            include_financials=False  # Get price data only first
        )
        
        if not price_data:
            print("❌ Failed to fetch price data")
            return
            
        # Fetch financial statements separately
        print("\nFetching financial statements...")
        
        # Get both quarterly and annual statements
        income_statements = {
            'quarterly': api_client.get_income_statement("NVO", period='quarter', limit=8),
            'annual': api_client.get_income_statement("NVO", period='annual', limit=4)
        }
        
        balance_sheets = {
            'quarterly': api_client.get_balance_sheet("NVO", period='quarter', limit=8),
            'annual': api_client.get_balance_sheet("NVO", period='annual', limit=4)
        }
        
        cash_flows = {
            'quarterly': api_client.get_cash_flow("NVO", period='quarter', limit=8),
            'annual': api_client.get_cash_flow("NVO", period='annual', limit=4)
        }
        
        # Add period type to each statement
        for statement in income_statements['quarterly']:
            statement['period'] = 'Q'
        for statement in income_statements['annual']:
            statement['period'] = 'FY'
            
        for statement in balance_sheets['quarterly']:
            statement['period'] = 'Q'
        for statement in balance_sheets['annual']:
            statement['period'] = 'FY'
            
        for statement in cash_flows['quarterly']:
            statement['period'] = 'Q'
        for statement in cash_flows['annual']:
            statement['period'] = 'FY'
        
        # Combine quarterly and annual statements
        all_income = income_statements['quarterly'] + income_statements['annual']
        all_balance = balance_sheets['quarterly'] + balance_sheets['annual']
        all_cash_flow = cash_flows['quarterly'] + cash_flows['annual']
        
        # Sort by date (newest first)
        all_income.sort(key=lambda x: x['date'], reverse=True)
        all_balance.sort(key=lambda x: x['date'], reverse=True)
        all_cash_flow.sort(key=lambda x: x['date'], reverse=True)
        
        # Combine all data
        data = price_data.to_dict()
        data.update({
            'income_statements': all_income,
            'balance_sheets': all_balance,
            'cash_flow_statements': all_cash_flow
        })
        
        # Save to file
        output_file = "valuation_data/novo_data.json"
        os.makedirs("valuation_data", exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)
        print(f"✅ Successfully saved data to {output_file}")
        
        # Verify daily coverage
        dates = sorted(set(price['date'] for price in data['historical_prices']))
        start_date = datetime.strptime(FROM_DATE, "%Y-%m-%d")
        end_date = datetime.strptime(TO_DATE, "%Y-%m-%d")
        
        # Check for missing dates
        current_date = start_date
        missing_dates = []
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            if date_str not in dates:
                missing_dates.append(date_str)
            current_date += timedelta(days=1)
            
        if missing_dates:
            print("\n⚠️ Missing data for the following dates:")
            for date in missing_dates:
                print(f"  - {date}")
        else:
            print("\n✅ Have data for all dates in the range")
        
        # Print summary
        print("\nData Summary:")
        print(f"Company: {data['company_name']} ({data['symbol']})")
        print(f"Sector: {data['sector']}")
        print(f"Current Price: ${data['current_price']:.2f}")
        print(f"Historical Data Points: {len(data['historical_prices'])}")
        
        # Print financial statement summary
        print("\nFinancial Statements:")
        print("Income Statements:")
        quarterly_income = [s for s in all_income if s['period'] == 'Q']
        annual_income = [s for s in all_income if s['period'] == 'FY']
        print(f"  - Quarterly: {len(quarterly_income)} statements")
        print(f"  - Annual: {len(annual_income)} statements")
        
        print("Balance Sheets:")
        quarterly_balance = [s for s in all_balance if s['period'] == 'Q']
        annual_balance = [s for s in all_balance if s['period'] == 'FY']
        print(f"  - Quarterly: {len(quarterly_balance)} statements")
        print(f"  - Annual: {len(annual_balance)} statements")
        
        print("Cash Flow Statements:")
        quarterly_cash = [s for s in all_cash_flow if s['period'] == 'Q']
        annual_cash = [s for s in all_cash_flow if s['period'] == 'FY']
        print(f"  - Quarterly: {len(quarterly_cash)} statements")
        print(f"  - Annual: {len(annual_cash)} statements")
        
        # Print latest quarter summary if available
        latest_q = next((s for s in all_income if s['period'] == 'Q'), None)
        if latest_q:
            print("\nLatest Quarter Summary:")
            print(f"Period: {latest_q.get('date', 'Unknown')}")
            print(f"Revenue: ${latest_q.get('revenue', 0)/1e6:.1f}M")
            print(f"Net Income: ${latest_q.get('netIncome', 0)/1e6:.1f}M")
            print(f"EPS: ${latest_q.get('eps', 0):.2f}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()

