"""
Data Format Converter
====================

This script converts all text data files into CSV and JSON formats for better data management and analysis.

Files to convert:
- earnings_data.txt -> earnings_data.csv, earnings_data.json
- tech_stocks_predictions.txt -> tech_predictions.csv, tech_predictions.json
- pharma_stocks_predictions.txt -> pharma_predictions.csv, pharma_predictions.json
- oil_stocks_predictions.txt -> oil_predictions.csv, oil_predictions.json
- stock_price_accuracy.txt -> accuracy_summary.csv, accuracy_summary.json
"""

import re
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any
import os

class DataConverter:
    """Convert text data files to CSV and JSON formats"""
    
    def __init__(self):
        self.output_dir = "data_exports"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def parse_earnings_data(self, file_path: str) -> Dict[str, Any]:
        """Parse earnings_data.txt into structured data"""
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        data = {
            'companies': {},
            'analyst_ratings': {},
            'patterns': []
        }
        
        # Split by company sections
        company_sections = re.split(r'\n(?=[A-Z][A-Z\s]+\([A-Z]+\))', content)
        
        for section in company_sections:
            if not section.strip():
                continue
                
            # Extract company name and symbol
            company_match = re.match(r'([A-Z][A-Z\s]+)\(([A-Z]+)\)', section)
            if not company_match:
                continue
                
            company_name = company_match.group(1).strip()
            symbol = company_match.group(2)
            
            company_data = {
                'name': company_name,
                'symbol': symbol,
                'quarters': [],
                'sector': self._determine_sector(symbol)
            }
            
            # Parse quarters
            quarter_pattern = r'Q[1-4]\s+20[23][0-9]:\s*\n(.*?)(?=\nQ[1-4]\s+20[23][0-9]:|\n[A-Z][A-Z\s]+\([A-Z]+\)|\nANALYST RATINGS|\nKey Patterns|\Z)'
            quarters = re.findall(quarter_pattern, section, re.DOTALL)
            
            for quarter in quarters:
                quarter_data = self._parse_quarter_data(quarter)
                if quarter_data:
                    company_data['quarters'].append(quarter_data)
            
            data['companies'][symbol] = company_data
        
        # Parse analyst ratings
        ratings_section = re.search(r'ANALYST RATINGS.*?(?=\nKey Patterns|\Z)', content, re.DOTALL)
        if ratings_section:
            data['analyst_ratings'] = self._parse_analyst_ratings(ratings_section.group(0))
        
        # Parse key patterns
        patterns_section = re.search(r'Key Patterns Observed:(.*?)(?=\Z)', content, re.DOTALL)
        if patterns_section:
            data['patterns'] = self._parse_patterns(patterns_section.group(1))
        
        return data
    
    def _determine_sector(self, symbol: str) -> str:
        """Determine sector based on symbol"""
        sectors = {
            'MSFT': 'Tech',
            'PLTR': 'Tech',
            'NVO': 'Pharmaceutical',
            'BP': 'Oil & Energy'
        }
        return sectors.get(symbol, 'Unknown')
    
    def _parse_quarter_data(self, quarter_text: str) -> Dict[str, Any]:
        """Parse individual quarter data"""
        quarter_data = {}
        
        # Extract quarter and year
        quarter_match = re.search(r'Q([1-4])\s+(20[23][0-9])', quarter_text)
        if quarter_match:
            quarter_data['quarter'] = int(quarter_match.group(1))
            quarter_data['year'] = int(quarter_match.group(2))
        
        # Extract metrics
        metrics_patterns = {
            'revenue': r'Revenue:\s*\$?([0-9,.]+[BKM]?)\s*(?:\(([+-]?\d+\.?\d*%)\s*YoY\))?',
            'operating_profit': r'Operating profit:\s*\$?([0-9,.]+[BKM]?)',
            'operating_margin': r'Operating margin:\s*([0-9.]+)%',
            'eps': r'EPS:\s*\$?([0-9.]+)',
            'pre_earnings_price': r'Pre-earnings price:\s*\$?([0-9.]+)',
            'one_day_price': r'1-day after price:\s*\$?([0-9.]+)\s*\(([+-]?\d+\.?\d*%)\)',
            'five_day_price': r'5-day after price:\s*\$?([0-9.]+)\s*\(([+-]?\d+\.?\d*%)\)'
        }
        
        for metric, pattern in metrics_patterns.items():
            match = re.search(pattern, quarter_text)
            if match:
                if metric in ['revenue', 'operating_profit']:
                    quarter_data[metric] = self._parse_number(match.group(1))
                    if len(match.groups()) > 1 and match.group(2):
                        quarter_data[f'{metric}_growth'] = float(match.group(2).replace('%', ''))
                elif metric in ['one_day_price', 'five_day_price']:
                    quarter_data[metric] = float(match.group(1))
                    quarter_data[f'{metric}_change'] = float(match.group(2).replace('%', ''))
                else:
                    quarter_data[metric] = float(match.group(1))
        
        return quarter_data if quarter_data else None
    
    def _parse_number(self, number_str: str) -> float:
        """Parse number with B/M/K suffixes"""
        number_str = number_str.replace(',', '')
        if 'B' in number_str:
            return float(number_str.replace('B', '')) * 1e9
        elif 'M' in number_str:
            return float(number_str.replace('M', '')) * 1e6
        elif 'K' in number_str:
            return float(number_str.replace('K', '')) * 1e3
        else:
            return float(number_str)
    
    def _parse_analyst_ratings(self, ratings_text: str) -> Dict[str, Any]:
        """Parse analyst ratings section"""
        ratings = {}
        
        # Extract ratings for each company
        company_pattern = r'([A-Z][A-Z\s]+)\(([A-Z]+)\)\s*-\s*([^:]+):\s*\n(.*?)(?=\n[A-Z][A-Z\s]+\([A-Z]+\)|\Z)'
        companies = re.findall(company_pattern, ratings_text, re.DOTALL)
        
        for company_name, symbol, period, ratings_data in companies:
            company_ratings = []
            
            # Parse individual analyst ratings
            analyst_pattern = r'-\s*([^:]+):\s*([^,]+),\s*Price Target \$([0-9.]+)'
            analysts = re.findall(analyst_pattern, ratings_data)
            
            for analyst, rating, target in analysts:
                company_ratings.append({
                    'analyst': analyst.strip(),
                    'rating': rating.strip(),
                    'price_target': float(target),
                    'period': period.strip()
                })
            
            ratings[symbol] = {
                'company_name': company_name.strip(),
                'period': period.strip(),
                'ratings': company_ratings
            }
        
        return ratings
    
    def _parse_patterns(self, patterns_text: str) -> List[str]:
        """Parse key patterns section"""
        patterns = []
        pattern_items = re.findall(r'\d+\.\s*(.+?)(?=\n\d+\.|\Z)', patterns_text, re.DOTALL)
        for item in pattern_items:
            patterns.append(item.strip())
        return patterns
    
    def parse_predictions_file(self, file_path: str) -> Dict[str, Any]:
        """Parse prediction files into structured data"""
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        data = {
            'sector': self._extract_sector_from_filename(file_path),
            'stocks': {},
            'predictions': [],
            'comparisons': []
        }
        
        # Extract stock sections
        stock_sections = re.split(r'\n(?=[A-Z][A-Z\s]+\([A-Z]+\)\s*-\s*[A-Z\s]+)', content)
        
        for section in stock_sections:
            if not section.strip():
                continue
            
            # Extract stock info
            stock_match = re.match(r'([A-Z][A-Z\s]+)\(([A-Z]+)\)\s*-\s*([A-Z\s]+)', section)
            if not stock_match:
                continue
            
            company_name = stock_match.group(1).strip()
            symbol = stock_match.group(2)
            sector = stock_match.group(3).strip()
            
            stock_data = {
                'name': company_name,
                'symbol': symbol,
                'sector': sector,
                'predictions': []
            }
            
            # Parse prediction results
            prediction_pattern = r'([A-Z]+)\s+PREDICTION.*?ACTUAL RESULTS:(.*?)(?=\n[A-Z]+ PREDICTION|\n[A-Z][A-Z\s]+\([A-Z]+\)|\Z)'
            predictions = re.findall(prediction_pattern, section, re.DOTALL)
            
            for model, prediction_text in predictions:
                prediction_data = self._parse_prediction_data(model, prediction_text)
                if prediction_data:
                    stock_data['predictions'].append(prediction_data)
            
            data['stocks'][symbol] = stock_data
        
        return data
    
    def _extract_sector_from_filename(self, file_path: str) -> str:
        """Extract sector from filename"""
        filename = os.path.basename(file_path)
        if 'tech' in filename.lower():
            return 'Tech'
        elif 'pharma' in filename.lower():
            return 'Pharmaceutical'
        elif 'oil' in filename.lower():
            return 'Oil & Energy'
        else:
            return 'General'
    
    def _parse_prediction_data(self, model: str, prediction_text: str) -> Dict[str, Any]:
        """Parse individual prediction data"""
        prediction_data = {
            'model': model,
            'metrics': {},
            'price_targets': {},
            'accuracy': {}
        }
        
        # Extract metrics
        metrics_patterns = {
            'revenue': r'Revenue:\s*\$?([0-9,.]+[BKM]?)\s*(?:\(([+-]?\d+\.?\d*%)\s*YoY\))?',
            'eps': r'EPS:\s*\$?([0-9.]+)',
            'operating_profit': r'Operating profit:\s*\$?([0-9,.]+[BKM]?)',
            'operating_margin': r'Operating margin:\s*([0-9.]+)%'
        }
        
        for metric, pattern in metrics_patterns.items():
            match = re.search(pattern, prediction_text)
            if match:
                prediction_data['metrics'][metric] = self._parse_number(match.group(1))
                if len(match.groups()) > 1 and match.group(2):
                    prediction_data['metrics'][f'{metric}_growth'] = float(match.group(2).replace('%', ''))
        
        # Extract price targets
        price_patterns = {
            'pre_earnings': r'Pre-earnings price estimate:\s*\$?([0-9.]+)',
            'one_day': r'1-day post-earnings:\s*\$?([0-9.]+)',
            'five_day': r'5-day post-earnings:\s*\$?([0-9.]+)'
        }
        
        for target, pattern in price_patterns.items():
            match = re.search(pattern, prediction_text)
            if match:
                prediction_data['price_targets'][target] = float(match.group(1))
        
        # Extract accuracy metrics
        accuracy_patterns = {
            'revenue_accuracy': r'Revenue Accuracy:\s*([0-9.]+)%',
            'eps_accuracy': r'EPS Accuracy:\s*([0-9.]+)%',
            'direction_accuracy': r'Direction Accuracy:\s*([✅❌]+)'
        }
        
        for accuracy, pattern in accuracy_patterns.items():
            match = re.search(pattern, prediction_text)
            if match:
                prediction_data['accuracy'][accuracy] = match.group(1)
        
        return prediction_data
    
    def convert_earnings_data(self):
        """Convert earnings_data.txt to CSV and JSON"""
        print("Converting earnings_data.txt...")
        
        data = self.parse_earnings_data('earnings_data.txt')
        
        # Convert to flat structure for CSV
        csv_data = []
        for symbol, company in data['companies'].items():
            for quarter in company['quarters']:
                row = {
                    'symbol': symbol,
                    'company_name': company['name'],
                    'sector': company['sector'],
                    'quarter': quarter.get('quarter'),
                    'year': quarter.get('year'),
                    'revenue': quarter.get('revenue'),
                    'revenue_growth': quarter.get('revenue_growth'),
                    'operating_profit': quarter.get('operating_profit'),
                    'operating_margin': quarter.get('operating_margin'),
                    'eps': quarter.get('eps'),
                    'pre_earnings_price': quarter.get('pre_earnings_price'),
                    'one_day_price': quarter.get('one_day_price'),
                    'one_day_change': quarter.get('one_day_price_change'),
                    'five_day_price': quarter.get('five_day_price'),
                    'five_day_change': quarter.get('five_day_price_change')
                }
                csv_data.append(row)
        
        # Save CSV
        df = pd.DataFrame(csv_data)
        csv_path = os.path.join(self.output_dir, 'earnings_data.csv')
        df.to_csv(csv_path, index=False)
        print(f"✅ Saved: {csv_path}")
        
        # Save JSON
        json_path = os.path.join(self.output_dir, 'earnings_data.json')
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"✅ Saved: {json_path}")
        
        return data
    
    def convert_predictions_file(self, file_path: str):
        """Convert prediction file to CSV and JSON"""
        filename = os.path.basename(file_path)
        print(f"Converting {filename}...")
        
        data = self.parse_predictions_file(file_path)
        
        # Convert to flat structure for CSV
        csv_data = []
        for symbol, stock in data['stocks'].items():
            for prediction in stock['predictions']:
                row = {
                    'symbol': symbol,
                    'company_name': stock['name'],
                    'sector': stock['sector'],
                    'model': prediction['model'],
                    'revenue': prediction['metrics'].get('revenue'),
                    'revenue_growth': prediction['metrics'].get('revenue_growth'),
                    'eps': prediction['metrics'].get('eps'),
                    'operating_profit': prediction['metrics'].get('operating_profit'),
                    'operating_margin': prediction['metrics'].get('operating_margin'),
                    'pre_earnings_target': prediction['price_targets'].get('pre_earnings'),
                    'one_day_target': prediction['price_targets'].get('one_day'),
                    'five_day_target': prediction['price_targets'].get('five_day'),
                    'revenue_accuracy': prediction['accuracy'].get('revenue_accuracy'),
                    'eps_accuracy': prediction['accuracy'].get('eps_accuracy'),
                    'direction_accuracy': prediction['accuracy'].get('direction_accuracy')
                }
                csv_data.append(row)
        
        # Save CSV
        df = pd.DataFrame(csv_data)
        csv_filename = filename.replace('.txt', '.csv')
        csv_path = os.path.join(self.output_dir, csv_filename)
        df.to_csv(csv_path, index=False)
        print(f"✅ Saved: {csv_path}")
        
        # Save JSON
        json_filename = filename.replace('.txt', '.json')
        json_path = os.path.join(self.output_dir, json_filename)
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"✅ Saved: {json_path}")
        
        return data
    
    def convert_all_files(self):
        """Convert all data files to CSV and JSON"""
        print("🚀 Starting data format conversion...")
        print("=" * 50)
        
        # Convert earnings data
        self.convert_earnings_data()
        
        # Convert prediction files
        prediction_files = [
            'tech_stocks_predictions.txt',
            'pharma_stocks_predictions.txt',
            'oil_stocks_predictions.txt',
            'stock_price_accuracy.txt'
        ]
        
        for file_path in prediction_files:
            if os.path.exists(file_path):
                self.convert_predictions_file(file_path)
            else:
                print(f"⚠️  File not found: {file_path}")
        
        print("\n🎯 Conversion complete!")
        print(f"📁 All files saved to: {self.output_dir}/")
        
        # Create summary
        self.create_summary()
    
    def create_summary(self):
        """Create a summary of all converted files"""
        summary = {
            'conversion_date': datetime.now().isoformat(),
            'files_converted': [],
            'total_records': 0
        }
        
        for file in os.listdir(self.output_dir):
            if file.endswith('.csv'):
                file_path = os.path.join(self.output_dir, file)
                df = pd.read_csv(file_path)
                summary['files_converted'].append({
                    'file': file,
                    'records': len(df),
                    'columns': list(df.columns)
                })
                summary['total_records'] += len(df)
        
        summary_path = os.path.join(self.output_dir, 'conversion_summary.json')
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"📊 Summary saved: {summary_path}")
        print(f"📈 Total records converted: {summary['total_records']}")

def main():
    """Main function"""
    converter = DataConverter()
    converter.convert_all_files()

if __name__ == "__main__":
    main() 