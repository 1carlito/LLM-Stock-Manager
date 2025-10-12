import json
import os

# Test the portfolio calculation with the positions from your working logs
portfolio = {
    'cash': 753201.28,
    'positions': {
        'GOOGL': {'shares': 688, 'cost_basis': 201.42},
        'NVDA': {'shares': 320, 'cost_basis': 182.70},
        'TMO': {'shares': 108, 'cost_basis': 460.72}
    }
}

def calculate_portfolio_value():
    total_value = portfolio['cash']
    for symbol, position in portfolio['positions'].items():
        try:
            valuation_files = [f for f in os.listdir('valuation_reports') if f.startswith(f'{symbol}_technical_analysis_')]
            if valuation_files:
                latest_file = sorted(valuation_files)[-1]
                with open(os.path.join('valuation_reports', latest_file), 'r') as f:
                    valuation_data = json.load(f)
                    current_price = valuation_data.get('current_price', position['cost_basis'])
            else:
                current_price = position['cost_basis']
        except Exception as e:
            print(f'Error loading current price for {symbol}: {str(e)}')
            current_price = position['cost_basis']
        
        total_value += position['shares'] * current_price
        print(f'{symbol}: {position["shares"]} shares @ ${current_price:.2f} = ${position["shares"] * current_price:,.2f}')
    
    return total_value

final_value = calculate_portfolio_value()
print(f'\nCash: ${portfolio["cash"]:,.2f}')
print(f'Total Portfolio Value: ${final_value:,.2f}')
print(f'Return: {((final_value - 1000000) / 1000000 * 100):.2f}%')
