"""
Simple Data Converter
====================

A simpler, more robust converter for text data files to CSV and JSON formats.
"""

import re
import json
import pandas as pd
from datetime import datetime
import os

def convert_earnings_data():
    """Convert earnings_data.txt to structured formats"""
    print("Converting earnings_data.txt...")
    
    with open('earnings_data.txt', 'r') as f:
        content = f.read()
    
    # Extract all quarter data
    quarter_pattern = r'Q([1-4])\s+(20[23][0-9]):\s*\n(.*?)(?=\nQ[1-4]\s+20[23][0-9]:|\n[A-Z][A-Z\s]+\([A-Z]+\)|\nANALYST RATINGS|\Z)'
    quarters = re.findall(quarter_pattern, content, re.DOTALL)
    
    csv_data = []
    json_data = {
        'quarters': [],
        'analyst_ratings': {},
        'metadata': {
            'conversion_date': datetime.now().isoformat(),
            'source_file': 'earnings_data.txt'
        }
    }
    
    for quarter_num, year, quarter_content in quarters:
        # Find which company this quarter belongs to
        # Look backwards to find the company name
        lines = content.split('\n')
        company_name = "Unknown"
        symbol = "Unknown"
        
        for i, line in enumerate(lines):
            if f"Q{quarter_num} {year}:" in line:
                # Look backwards for company name
                for j in range(i, max(0, i-10), -1):
                    company_match = re.match(r'([A-Z][A-Z\s]+)\(([A-Z]+)\)', lines[j])
                    if company_match:
                        company_name = company_match.group(1).strip()
                        symbol = company_match.group(2)
                        break
                break
        
        # Extract metrics
        revenue_match = re.search(r'Revenue:\s*\$?([0-9,.]+[BKM]?)\s*(?:\(([+-]?\d+\.?\d*%)\s*YoY\))?', quarter_content)
        eps_match = re.search(r'EPS:\s*\$?([0-9.]+)', quarter_content)
        operating_profit_match = re.search(r'Operating profit:\s*\$?([0-9,.]+[BKM]?)', quarter_content)
        operating_margin_match = re.search(r'Operating margin:\s*([0-9.]+)%', quarter_content)
        pre_price_match = re.search(r'Pre-earnings price:\s*\$?([0-9.]+)', quarter_content)
        one_day_match = re.search(r'1-day after price:\s*\$?([0-9.]+)\s*\(([+-]?\d+\.?\d*%)\)', quarter_content)
        five_day_match = re.search(r'5-day after price:\s*\$?([0-9.]+)\s*\(([+-]?\d+\.?\d*%)\)', quarter_content)
        
        # Parse revenue
        revenue = None
        revenue_growth = None
        if revenue_match:
            revenue_str = revenue_match.group(1).replace(',', '')
            if 'B' in revenue_str:
                revenue = float(revenue_str.replace('B', '')) * 1e9
            elif 'M' in revenue_str:
                revenue = float(revenue_str.replace('M', '')) * 1e6
            elif 'K' in revenue_str:
                revenue = float(revenue_str.replace('K', '')) * 1e3
            else:
                revenue = float(revenue_str)
            
            if revenue_match.group(2):
                revenue_growth = float(revenue_match.group(2).replace('%', ''))
        
        # Parse other metrics
        eps = float(eps_match.group(1)) if eps_match else None
        operating_profit = None
        if operating_profit_match:
            op_str = operating_profit_match.group(1).replace(',', '')
            if 'B' in op_str:
                operating_profit = float(op_str.replace('B', '')) * 1e9
            elif 'M' in op_str:
                operating_profit = float(op_str.replace('M', '')) * 1e6
            else:
                operating_profit = float(op_str)
        
        operating_margin = float(operating_margin_match.group(1)) if operating_margin_match else None
        pre_price = float(pre_price_match.group(1)) if pre_price_match else None
        one_day_price = float(one_day_match.group(1)) if one_day_match else None
        one_day_change = float(one_day_match.group(2).replace('%', '')) if one_day_match else None
        five_day_price = float(five_day_match.group(1)) if five_day_match else None
        five_day_change = float(five_day_match.group(2).replace('%', '')) if five_day_match else None
        
        # Create CSV row
        row = {
            'symbol': symbol,
            'company_name': company_name,
            'quarter': int(quarter_num),
            'year': int(year),
            'revenue': revenue,
            'revenue_growth_yoy': revenue_growth,
            'eps': eps,
            'operating_profit': operating_profit,
            'operating_margin': operating_margin,
            'pre_earnings_price': pre_price,
            'one_day_price': one_day_price,
            'one_day_change_pct': one_day_change,
            'five_day_price': five_day_price,
            'five_day_change_pct': five_day_change
        }
        csv_data.append(row)
        
        # Add to JSON
        json_data['quarters'].append(row)
    
    # Save CSV
    df = pd.DataFrame(csv_data)
    os.makedirs('data_exports', exist_ok=True)
    csv_path = 'data_exports/earnings_data_structured.csv'
    df.to_csv(csv_path, index=False)
    print(f"✅ Saved: {csv_path} ({len(csv_data)} records)")
    
    # Save JSON
    json_path = 'data_exports/earnings_data_structured.json'
    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2, default=str)
    print(f"✅ Saved: {json_path}")
    
    return csv_data

def convert_predictions_to_csv():
    """Convert prediction files to CSV format"""
    
    prediction_files = [
        'tech_stocks_predictions.txt',
        'pharma_stocks_predictions.txt', 
        'oil_stocks_predictions.txt'
    ]
    
    all_predictions = []
    
    for file_path in prediction_files:
        if not os.path.exists(file_path):
            print(f"⚠️  File not found: {file_path}")
            continue
            
        print(f"Converting {file_path}...")
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Extract sector from filename
        sector = "Unknown"
        if 'tech' in file_path.lower():
            sector = "Tech"
        elif 'pharma' in file_path.lower():
            sector = "Pharmaceutical"
        elif 'oil' in file_path.lower():
            sector = "Oil & Energy"
        
        # Find all prediction sections
        prediction_sections = re.findall(r'([A-Z]+)\s+PREDICTION.*?ACTUAL RESULTS:(.*?)(?=\n[A-Z]+ PREDICTION|\n[A-Z][A-Z\s]+\([A-Z]+\)|\Z)', content, re.DOTALL)
        
        for model, prediction_text in prediction_sections:
            # Extract stock symbol from context
            symbol_match = re.search(r'([A-Z]+)\s+Q[1-4]\s+20[23][0-9]', prediction_text)
            symbol = symbol_match.group(1) if symbol_match else "Unknown"
            
            # Extract metrics
            revenue_match = re.search(r'Revenue:\s*\$?([0-9,.]+[BKM]?)\s*(?:\(([+-]?\d+\.?\d*%)\s*YoY\))?', prediction_text)
            eps_match = re.search(r'EPS:\s*\$?([0-9.]+)', prediction_text)
            
            # Extract price targets
            pre_target_match = re.search(r'Pre-earnings price estimate:\s*\$?([0-9.]+)', prediction_text)
            one_day_match = re.search(r'1-day post-earnings:\s*\$?([0-9.]+)', prediction_text)
            five_day_match = re.search(r'5-day post-earnings:\s*\$?([0-9.]+)', prediction_text)
            
            # Extract accuracy
            revenue_acc_match = re.search(r'Revenue Accuracy:\s*([0-9.]+)%', prediction_text)
            eps_acc_match = re.search(r'EPS Accuracy:\s*([0-9.]+)%', prediction_text)
            direction_acc_match = re.search(r'Direction Accuracy:\s*([✅❌]+)', prediction_text)
            
            # Parse values
            revenue = None
            if revenue_match:
                rev_str = revenue_match.group(1).replace(',', '')
                if 'B' in rev_str:
                    revenue = float(rev_str.replace('B', '')) * 1e9
                elif 'M' in rev_str:
                    revenue = float(rev_str.replace('M', '')) * 1e6
                else:
                    revenue = float(rev_str)
            
            row = {
                'sector': sector,
                'symbol': symbol,
                'model': model,
                'revenue': revenue,
                'eps': float(eps_match.group(1)) if eps_match else None,
                'pre_earnings_target': float(pre_target_match.group(1)) if pre_target_match else None,
                'one_day_target': float(one_day_match.group(1)) if one_day_match else None,
                'five_day_target': float(five_day_match.group(1)) if five_day_match else None,
                'revenue_accuracy': float(revenue_acc_match.group(1)) if revenue_acc_match else None,
                'eps_accuracy': float(eps_acc_match.group(1)) if eps_acc_match else None,
                'direction_accuracy': direction_acc_match.group(1) if direction_acc_match else None,
                'source_file': file_path
            }
            all_predictions.append(row)
    
    # Save combined predictions CSV
    if all_predictions:
        df = pd.DataFrame(all_predictions)
        csv_path = 'data_exports/all_predictions.csv'
        df.to_csv(csv_path, index=False)
        print(f"✅ Saved: {csv_path} ({len(all_predictions)} records)")
    
    return all_predictions

def create_summary():
    """Create a summary of all converted data"""
    summary = {
        'conversion_date': datetime.now().isoformat(),
        'files_created': [],
        'total_records': 0
    }
    
    if os.path.exists('data_exports'):
        for file in os.listdir('data_exports'):
            if file.endswith('.csv'):
                file_path = os.path.join('data_exports', file)
                try:
                    df = pd.read_csv(file_path)
                    summary['files_created'].append({
                        'file': file,
                        'records': len(df),
                        'columns': list(df.columns)
                    })
                    summary['total_records'] += len(df)
                except:
                    summary['files_created'].append({
                        'file': file,
                        'records': 0,
                        'columns': []
                    })
    
    summary_path = 'data_exports/conversion_summary.json'
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"📊 Summary saved: {summary_path}")
    print(f"📈 Total records: {summary['total_records']}")

def main():
    """Main conversion function"""
    print("🚀 Starting simple data conversion...")
    print("=" * 50)
    
    # Convert earnings data
    earnings_data = convert_earnings_data()
    
    # Convert predictions
    predictions_data = convert_predictions_to_csv()
    
    # Create summary
    create_summary()
    
    print("\n🎯 Conversion complete!")
    print("📁 All files saved to: data_exports/")

if __name__ == "__main__":
    main() 