"""
Fundamental Analysis Agent
=======================

Analyzes company fundamentals using financial statements and metrics.
"""

import os
import json
from typing import Dict, List, Optional
from datetime import datetime
from data_utils import DataManager
from dotenv import load_dotenv
import google.generativeai as genai
import numpy as np
import glob

# Load environment variables from .env file
load_dotenv()

# Configure Gemini
gemini_api_key = os.getenv('GEMINI_API_KEY')
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
MODEL_NAME = 'gemini-2.5-flash-lite'

class FundamentalAgent:
    """
    Fundamental Analysis Agent that examines financial statements,
    ratios, and company information for stock valuation.
    """

    def __init__(self, data_dir: str = ".", start_date: str = None, end_date: str = None):
        """Initialize the Fundamental Agent"""
        load_dotenv()
        self.data_dir = data_dir
        self.output_dir = os.path.join(data_dir, "fundamental_reports")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Set data range
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d") if start_date else datetime.strptime("2025-09-16", "%Y-%m-%d")
        self.cutoff_date = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.strptime("2025-09-18", "%Y-%m-%d")

        self.model = MODEL_NAME
        self.gemini_client = genai.GenerativeModel(self.model)

    def _get_previous_analyses(self, symbol: str, current_date: str = None, days: int = 4) -> List[Dict]:
        """Get the previous N days of analyses for this symbol"""
        try:
            # Convert current_date to datetime if provided
            analysis_date = datetime.now()
            if current_date:
                if isinstance(current_date, str):
                    analysis_date = datetime.strptime(current_date, '%Y-%m-%d')
                else:
                    analysis_date = current_date
                    
            analyses = []
            pattern = os.path.join(self.output_dir, f"{symbol}_fundamental_analysis_*.json")
            files = glob.glob(pattern)
            
            if not files:
                return []
                
            # Sort files by creation time (newest first)
            sorted_files = sorted(files, key=os.path.getmtime, reverse=True)
            
            # Skip the problematic file
            sorted_files = [f for f in sorted_files if "20250922_222509" not in f]
            
            # Get up to 'days' previous analyses
            for i, filepath in enumerate(sorted_files):
                if i >= days:
                    break
                    
                try:
                    with open(filepath, 'r') as f:
                        analysis = json.load(f)
                        
                        # Check if this analysis is from before the current date
                        analysis_date_str = analysis.get('analysis_date', '')
                        if analysis_date_str:
                            if isinstance(analysis_date_str, str) and 'T' in analysis_date_str:
                                file_date = datetime.fromisoformat(analysis_date_str.split('T')[0])
                            else:
                                file_date = datetime.fromisoformat(analysis_date_str[:10])
                                
                            # Skip if this analysis is from after the current date (avoid look-ahead bias)
                            if file_date >= analysis_date:
                                continue
                        
                        # Get recommendation and confidence
                        recommendation = "HOLD"
                        confidence = 50
                        reasoning = "Previous analysis"
                        
                        # Handle case where analysis is a dictionary
                        if 'analysis' in analysis and isinstance(analysis['analysis'], dict):
                            recommendation = analysis['analysis'].get('recommendation', 'HOLD')
                            confidence = analysis['analysis'].get('confidence', 50)
                            if isinstance(analysis['analysis'].get('analysis', ''), str):
                                reasoning = analysis['analysis']['analysis'].split('\n')[0][:100]
                        # Handle case where analysis is a string
                        elif 'analysis' in analysis and isinstance(analysis['analysis'], str):
                            # Try to extract recommendation and confidence from the string
                            text = analysis['analysis']
                            if "RECOMMENDATION:" in text:
                                rec_part = text.split("RECOMMENDATION:")[1].split("\n")[0].strip()
                                if rec_part in ["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]:
                                    recommendation = rec_part
                            if "CONFIDENCE:" in text:
                                conf_part = text.split("CONFIDENCE:")[1].split("\n")[0].strip()
                                try:
                                    confidence = int(conf_part)
                                except ValueError:
                                    pass
                            reasoning = text.split('\n')[0][:100] if text else ""
                        
                        analyses.append({
                            'date': analysis.get('analysis_date', ''),
                            'recommendation': recommendation,
                            'confidence': confidence,
                            'reasoning': reasoning
                        })
                except Exception as e:
                    print(f"Skipping problematic file {filepath}: {e}")
                    continue
                    
            return analyses
            
        except Exception as e:
            print(f"Error getting previous analyses: {e}")
            return []

    def _filter_data_by_date(self, data: List[Dict], current_date: datetime = None, date_key: str = 'date') -> List[Dict]:
        """Filter data to only include entries before cutoff date"""
        if not data:
            return data
        
        # Use provided current_date or default to cutoff_date
        end_date = current_date if current_date else self.cutoff_date
            
        filtered_data = []
        for entry in data:
            if date_key in entry:
                entry_date = datetime.strptime(entry[date_key], "%Y-%m-%d")
                if self.start_date <= entry_date <= end_date:
                    filtered_data.append(entry)
                    
        return filtered_data

    def _load_stock_data(self, symbol: str, current_date: str = None) -> Optional[Dict]:
        """Load stock data from file"""
        try:
            # Convert current_date to datetime if provided
            analysis_date = self.cutoff_date
            if current_date:
                if isinstance(current_date, str):
                    analysis_date = datetime.strptime(current_date, '%Y-%m-%d')
                else:
                    analysis_date = current_date
                    
            # Load stock data from new location
            stock_data_file = os.path.join(self.data_dir, "valuation_data/stock_data_valuation.json")
            if not os.path.exists(stock_data_file):
                print(f"❌ Stock data file not found: {stock_data_file}")
                return None
                
            with open(stock_data_file, 'r') as f:
                stock_data = json.load(f)
                
            if symbol not in stock_data:
                print(f"❌ No data found for {symbol}")
                return None
                
            # Get company data
            data = stock_data[symbol]
            
            # Extract current price from historical data up to current_date (like ValuationAgent does)                                                      
            historical_prices = data.get('historical_prices', [])
            current_price = data.get('current_price', 0)  # Fallback to static price                                                                        
            
            if historical_prices and current_date:
                # Filter prices up to current date
                current_date_str = current_date if isinstance(current_date, str) else current_date.strftime('%Y-%m-%d')                                     
                for price_data in reversed(historical_prices):
                    if price_data['date'] == current_date_str:
                        current_price = price_data['close']
                        break
            
            data['current_price_as_of_date'] = current_price
            
            # Get financial statements (use correct field names from stock_data)                                                                            
            data['income_statements'] = data.get('income_statement', [])
            data['balance_sheets'] = data.get('balance_sheet', [])
            data['cash_flow_statements'] = data.get('cash_flow', [])
            
            # Sort statements by date (most recent first)
            for key in ['income_statements', 'balance_sheets', 'cash_flow_statements']:
                data[key].sort(key=lambda x: x['date'], reverse=True)
            
            return data
                
        except Exception as e:
            print(f"Error loading data for {symbol}: {str(e)}")
            return None

    def _analyze_profitability(self, income_data: List[Dict]) -> Dict:
        """Analyze profitability metrics from income statement"""
        if not income_data:
            return {
                'status': 'No income statement data available',
                'metrics': {}
            }
            
        try:
            # Get quarterly and annual statements
            quarterly = [s for s in income_data if s.get('period') == 'Q']
            annual = [s for s in income_data if s.get('period') == 'FY']
            
            # Analyze latest quarter
            latest_q = quarterly[0] if quarterly else None
            prev_q = quarterly[1] if len(quarterly) > 1 else None
            
            # Analyze latest year
            latest_y = annual[0] if annual else None
            prev_y = annual[1] if len(annual) > 1 else None
            
            metrics = {
                'quarterly': {
                    'revenue': latest_q.get('revenue', 0) if latest_q else None,
                    'net_income': latest_q.get('netIncome', 0) if latest_q else None,
                    'operating_income': latest_q.get('operatingIncome', 0) if latest_q else None,
                    'gross_profit_margin': latest_q.get('grossProfitMargin', 0) if latest_q else None,
                    'operating_margin': latest_q.get('operatingMargin', 0) if latest_q else None,
                    'net_profit_margin': latest_q.get('netProfitMargin', 0) if latest_q else None,
                    'revenue_growth': ((latest_q.get('revenue', 0) - prev_q.get('revenue', 0)) / prev_q.get('revenue', 1)) if latest_q and prev_q else None,
                    'net_income_growth': ((latest_q.get('netIncome', 0) - prev_q.get('netIncome', 0)) / prev_q.get('netIncome', 1)) if latest_q and prev_q else None
                },
                'annual': {
                    'revenue': latest_y.get('revenue', 0) if latest_y else None,
                    'net_income': latest_y.get('netIncome', 0) if latest_y else None,
                    'operating_income': latest_y.get('operatingIncome', 0) if latest_y else None,
                    'gross_profit_margin': latest_y.get('grossProfitMargin', 0) if latest_y else None,
                    'operating_margin': latest_y.get('operatingMargin', 0) if latest_y else None,
                    'net_profit_margin': latest_y.get('netProfitMargin', 0) if latest_y else None,
                    'revenue_growth': ((latest_y.get('revenue', 0) - prev_y.get('revenue', 0)) / prev_y.get('revenue', 1)) if latest_y and prev_y else None,
                    'net_income_growth': ((latest_y.get('netIncome', 0) - prev_y.get('netIncome', 0)) / prev_y.get('netIncome', 1)) if latest_y and prev_y else None
                }
            }
            
            return {
                'status': 'success',
                'metrics': metrics
            }
            
        except Exception as e:
            return {
                'status': f'Error analyzing profitability: {str(e)}',
                'metrics': {}
            }

    def _analyze_financial_health(self, balance_sheet: List[Dict], cash_flow: List[Dict]) -> Dict:
        """Analyze financial health metrics from balance sheet and cash flow"""
        if not balance_sheet or not cash_flow:
            return {
                'status': 'Insufficient financial statement data',
                'metrics': {}
            }
            
        try:
            # Get quarterly and annual statements
            q_bs = [s for s in balance_sheet if s.get('period') == 'Q']
            q_cf = [s for s in cash_flow if s.get('period') == 'Q']
            y_bs = [s for s in balance_sheet if s.get('period') == 'FY']
            y_cf = [s for s in cash_flow if s.get('period') == 'FY']
            
            # Latest quarterly metrics
            latest_q_bs = q_bs[0] if q_bs else None
            latest_q_cf = q_cf[0] if q_cf else None
            
            # Latest annual metrics
            latest_y_bs = y_bs[0] if y_bs else None
            latest_y_cf = y_cf[0] if y_cf else None
            
            def calc_metrics(bs, cf):
                if not bs or not cf:
                    return {}
                    
                total_assets = bs.get('totalAssets', 0)
                total_liabilities = bs.get('totalLiabilities', 0)
                current_assets = bs.get('totalCurrentAssets', 0)
                current_liabilities = bs.get('totalCurrentLiabilities', 0)
                equity = total_assets - total_liabilities
                
                return {
                    'current_ratio': current_assets / current_liabilities if current_liabilities else None,
                    'quick_ratio': (current_assets - bs.get('inventory', 0)) / current_liabilities if current_liabilities else None,
                    'debt_to_equity': total_liabilities / equity if equity else None,
                    'debt_to_assets': total_liabilities / total_assets if total_assets else None,
                    'operating_cash_flow': cf.get('operatingCashFlow', 0),
                    'free_cash_flow': cf.get('freeCashFlow', 0),
                    'cash_and_equivalents': bs.get('cashAndCashEquivalents', 0),
                    'working_capital': current_assets - current_liabilities,
                    'return_on_assets': bs.get('netIncome', 0) / total_assets if total_assets else None,
                    'return_on_equity': bs.get('netIncome', 0) / equity if equity else None
                }
            
            metrics = {
                'quarterly': calc_metrics(latest_q_bs, latest_q_cf),
                'annual': calc_metrics(latest_y_bs, latest_y_cf)
            }
            
            return {
                'status': 'success',
                'metrics': metrics
            }
            
        except Exception as e:
            return {
                'status': f'Error analyzing financial health: {str(e)}',
                'metrics': {}
            }

    def _calculate_valuation_ratios(self, current_price: float, income_data: List[Dict], balance_sheet: List[Dict]) -> Dict:                                
        """Calculate valuation ratios using current price and fundamental data"""                                                                           
        try:
            if not current_price or not income_data or not balance_sheet:
                return {
                    'status': 'Insufficient data for valuation ratios',
                    'ratios': {}
                }
            
            # Get latest data
            latest_income = income_data[0] if income_data else {}
            latest_balance = balance_sheet[0] if balance_sheet else {}
            
            if not latest_income or not latest_balance:
                return {
                    'status': 'Missing latest financial data',
                    'ratios': {}
                }
            
            # Calculate P/E Ratio
            eps = latest_income.get('eps', 0)
            pe_ratio = current_price / eps if eps else None
            
            # Calculate P/B Ratio (Price to Book Value per Share)
            total_assets = latest_balance.get('totalAssets', 0)
            total_liabilities = latest_balance.get('totalLiabilities', 0)
            equity = total_assets - total_liabilities
            shares_outstanding = latest_income.get('weightedAverageShsOut', 0)                                                                              
            
            book_value_per_share = equity / shares_outstanding if shares_outstanding else None                                                              
            pb_ratio = current_price / book_value_per_share if book_value_per_share else None                                                               
            
            # Calculate Price to Sales
            revenue = latest_income.get('revenue', 0)
            revenue_per_share = revenue / shares_outstanding if shares_outstanding else None                                                                
            ps_ratio = current_price / revenue_per_share if revenue_per_share else None                                                                     
            
            # Calculate Price to Cash Flow
            # We'll use this in the next function if cash_flow is available
            
            ratios = {
                'pe_ratio': pe_ratio,
                'pb_ratio': pb_ratio,
                'ps_ratio': ps_ratio,
                'book_value_per_share': book_value_per_share,
                'revenue_per_share': revenue_per_share,
                'eps': eps,
                'current_price': current_price
            }
            
            return {
                'status': 'success',
                'ratios': ratios
            }
            
        except Exception as e:
            return {
                'status': f'Error calculating valuation ratios: {str(e)}',
                'ratios': {}
            }

    def _analyze_growth(self, income_data: List[Dict], balance_sheet: List[Dict]) -> Dict:
        """Analyze growth metrics"""
        if not income_data or not balance_sheet:
            return {
                'status': 'Insufficient data for growth analysis',
                'metrics': {}
            }
            
        try:
            # Get annual statements
            annual_income = [s for s in income_data if s.get('period') == 'FY']
            annual_bs = [s for s in balance_sheet if s.get('period') == 'FY']
            
            if len(annual_income) < 2 or len(annual_bs) < 2:
                return {
                    'status': 'Insufficient historical data for growth analysis',
                    'metrics': {}
                }
            
            # Calculate growth rates
            def calc_growth_rate(current, previous, field):
                curr_val = current.get(field, 0)
                prev_val = previous.get(field, 0)
                return (curr_val - prev_val) / abs(prev_val) if prev_val else None
            
            # Latest two years
            curr_year = annual_income[0]
            prev_year = annual_income[1]
            
            metrics = {
                'revenue_growth': calc_growth_rate(curr_year, prev_year, 'revenue'),
                'net_income_growth': calc_growth_rate(curr_year, prev_year, 'netIncome'),
                'operating_income_growth': calc_growth_rate(curr_year, prev_year, 'operatingIncome'),
                'eps_growth': calc_growth_rate(curr_year, prev_year, 'eps'),
                'asset_growth': calc_growth_rate(annual_bs[0], annual_bs[1], 'totalAssets'),
                'equity_growth': calc_growth_rate(
                    {'equity': annual_bs[0].get('totalAssets', 0) - annual_bs[0].get('totalLiabilities', 0)},
                    {'equity': annual_bs[1].get('totalAssets', 0) - annual_bs[1].get('totalLiabilities', 0)},
                    'equity'
                )
            }
            
            return {
                'status': 'success',
                'metrics': metrics
            }
            
        except Exception as e:
            return {
                'status': f'Error analyzing growth metrics: {str(e)}',
                'metrics': {}
            }

    def analyze_fundamentals(self, symbol: str, current_date: str = None) -> Optional[Dict]:
        """Analyze fundamentals for a stock symbol"""
        try:
            # Convert current_date to datetime if provided
            analysis_date = datetime.now()
            if current_date:
                if isinstance(current_date, str):
                    analysis_date = datetime.strptime(current_date, '%Y-%m-%d')
                else:
                    analysis_date = current_date
                    
            # Load data
            data = self._load_stock_data(symbol, current_date)
            if not data:
                return None
            
            # Check if we have financial statements
            has_income = bool(data.get('income_statements', []))
            has_balance = bool(data.get('balance_sheets', []))
            has_cash_flow = bool(data.get('cash_flow_statements', []))
            
            if not (has_income or has_balance or has_cash_flow):
                print(f"⚠️  No financial statement data available for {symbol}, using price-based analysis only")
                return self._analyze_price_only(data, current_date)
            
            # Run analyses
            profitability = self._analyze_profitability(data.get('income_statements', []))
            financial_health = self._analyze_financial_health(
                data.get('balance_sheets', []),
                data.get('cash_flow_statements', [])
            )
            growth = self._analyze_growth(
                data.get('income_statements', []),
                data.get('balance_sheets', [])
            )
            
            # Calculate valuation ratios with current price
            valuation_ratios = self._calculate_valuation_ratios(
                data.get('current_price_as_of_date', 0),
                data.get('income_statements', []),
                data.get('balance_sheets', [])
            )
            
            # Get previous analyses
            previous_analyses = self._get_previous_analyses(symbol, current_date)
            previous_analyses_text = ""
            
            if previous_analyses:
                previous_analyses_text = "\nPREVIOUS FUNDAMENTAL ANALYSES:\n"
                previous_analyses_text += "Date                     | Recommendation | Confidence | Summary\n"
                previous_analyses_text += "-------------------------|----------------|------------|--------\n"
                
                for analysis in previous_analyses:
                    date = analysis.get('date', '').split('T')[0] if 'T' in analysis.get('date', '') else analysis.get('date', '')[:10]
                    recommendation = analysis.get('recommendation', 'HOLD')
                    confidence = analysis.get('confidence', 50)
                    reasoning = analysis.get('reasoning', '')[:50] + "..." if analysis.get('reasoning', '') else "N/A"
                    
                    previous_analyses_text += f"{date} | {recommendation:14s} | {confidence:10d} | {reasoning}\n"
            
            # Prepare analysis prompt
            prompt = self._build_analysis_prompt(data, profitability, financial_health, growth, valuation_ratios, previous_analyses_text)
            
            # Get analysis from Gemini
            response = self.gemini_client.generate_content(prompt)
            if not response or not response.text:
                print(f"❌ No response from Gemini for {symbol}")
                return None
            
            # Parse and format results
            analysis_result = {
                'symbol': symbol,
                'company_name': data.get('company_name', symbol),
                'sector': data.get('sector', 'Unknown'),
                'analysis_date': analysis_date.isoformat(),
                'data_range': {
                    'start': self.start_date.isoformat(),
                    'end': analysis_date.isoformat()
                },
                'metrics': {
                    'profitability': profitability['metrics'],
                    'financial_health': financial_health['metrics'],
                    'growth': growth['metrics'],
                    'valuation_ratios': valuation_ratios['ratios']
                },
                'analysis': self._parse_analysis_response(response.text),
                'model_used': self.model
            }
            
            # Save analysis
            self._save_analysis(symbol, analysis_result)
            
            return analysis_result
            
        except Exception as e:
            print(f"❌ Error analyzing fundamentals for {symbol}: {e}")
            return None

    def _build_analysis_prompt(self, data: Dict, profitability: Dict, financial_health: Dict, growth: Dict, valuation_ratios: Dict, previous_analyses_text: str = "") -> str:
        """Build the prompt for fundamental analysis"""
        symbol = data.get('symbol', '')
        company = data.get('company_name', symbol)
        sector = data.get('sector', 'Unknown')
        current_price = data.get('current_price_as_of_date', data.get('current_price', 0))
        
        # Format metrics with proper handling of None values
        def fmt_price(val):
            return f"${val:,.2f}" if val is not None else "N/A"
            
        def fmt_pct(val):
            return f"{val*100:.1f}%" if val is not None else "N/A"
            
        def fmt_ratio(val):
            return f"{val:.2f}" if val is not None else "N/A"
        
        # Get quarterly statements for trend analysis
        quarterly_income = [s for s in data.get('income_statements', []) if s.get('period') == 'Q']
        quarterly_income = quarterly_income[:4]  # Use up to 4 most recent quarters
        
        # Format quarterly trend data
        quarterly_trend = ""
        if quarterly_income:
            quarterly_trend = "QUARTERLY FINANCIAL TRENDS (Most Recent 4 Quarters):\n"
            quarterly_trend += "Quarter | Revenue | Net Income | Operating Income | Net Margin\n"
            quarterly_trend += "--------|---------|------------|------------------|----------\n"
            
            for q in quarterly_income:
                quarter_date = q.get('date', 'Unknown')
                revenue = q.get('revenue', 0)
                net_income = q.get('netIncome', 0)
                op_income = q.get('operatingIncome', 0)
                margin = q.get('netProfitMargin', 0)
                
                quarterly_trend += f"{quarter_date} | {fmt_price(revenue)} | {fmt_price(net_income)} | "
                quarterly_trend += f"{fmt_price(op_income)} | {fmt_pct(margin)}\n"
        
        prompt = f"""
Analyze the fundamental health and outlook for {company} ({symbol}) in the {sector} sector.

Current Price: ${current_price:.2f}
Analysis Period: {self.start_date.strftime('%Y-%m-%d')} to {self.cutoff_date.strftime('%Y-%m-%d')}

{quarterly_trend}

{previous_analyses_text}

1. PROFITABILITY METRICS:

Quarterly (Most Recent):
- Revenue: {fmt_price(profitability['metrics']['quarterly'].get('revenue'))}
- Net Income: {fmt_price(profitability['metrics']['quarterly'].get('net_income'))}
- Operating Income: {fmt_price(profitability['metrics']['quarterly'].get('operating_income'))}
- Gross Margin: {fmt_pct(profitability['metrics']['quarterly'].get('gross_profit_margin'))}
- Operating Margin: {fmt_pct(profitability['metrics']['quarterly'].get('operating_margin'))}
- Net Margin: {fmt_pct(profitability['metrics']['quarterly'].get('net_profit_margin'))}
- Revenue Growth (QoQ): {fmt_pct(profitability['metrics']['quarterly'].get('revenue_growth'))}
- Net Income Growth (QoQ): {fmt_pct(profitability['metrics']['quarterly'].get('net_income_growth'))}

Annual (Most Recent):
- Revenue: {fmt_price(profitability['metrics']['annual'].get('revenue'))}
- Net Income: {fmt_price(profitability['metrics']['annual'].get('net_income'))}
- Operating Income: {fmt_price(profitability['metrics']['annual'].get('operating_income'))}
- Gross Margin: {fmt_pct(profitability['metrics']['annual'].get('gross_profit_margin'))}
- Operating Margin: {fmt_pct(profitability['metrics']['annual'].get('operating_margin'))}
- Net Margin: {fmt_pct(profitability['metrics']['annual'].get('net_profit_margin'))}
- Revenue Growth (YoY): {fmt_pct(profitability['metrics']['annual'].get('revenue_growth'))}
- Net Income Growth (YoY): {fmt_pct(profitability['metrics']['annual'].get('net_income_growth'))}

2. FINANCIAL HEALTH:

Quarterly Metrics:
- Current Ratio: {fmt_ratio(financial_health['metrics']['quarterly'].get('current_ratio'))}
- Quick Ratio: {fmt_ratio(financial_health['metrics']['quarterly'].get('quick_ratio'))}
- Debt/Equity: {fmt_ratio(financial_health['metrics']['quarterly'].get('debt_to_equity'))}
- Operating Cash Flow: {fmt_price(financial_health['metrics']['quarterly'].get('operating_cash_flow'))}
- Free Cash Flow: {fmt_price(financial_health['metrics']['quarterly'].get('free_cash_flow'))}

Annual Metrics:
- Current Ratio: {fmt_ratio(financial_health['metrics']['annual'].get('current_ratio'))}
- Quick Ratio: {fmt_ratio(financial_health['metrics']['annual'].get('quick_ratio'))}
- Debt/Equity: {fmt_ratio(financial_health['metrics']['annual'].get('debt_to_equity'))}
- Operating Cash Flow: {fmt_price(financial_health['metrics']['annual'].get('operating_cash_flow'))}
- Free Cash Flow: {fmt_price(financial_health['metrics']['annual'].get('free_cash_flow'))}

3. GROWTH METRICS (Year-over-Year):
- Revenue Growth: {fmt_pct(growth['metrics'].get('revenue_growth'))}
- Net Income Growth: {fmt_pct(growth['metrics'].get('net_income_growth'))}
- Operating Income Growth: {fmt_pct(growth['metrics'].get('operating_income_growth'))}
- EPS Growth: {fmt_pct(growth['metrics'].get('eps_growth'))}
- Asset Growth: {fmt_pct(growth['metrics'].get('asset_growth'))}
- Equity Growth: {fmt_pct(growth['metrics'].get('equity_growth'))}

4. VALUATION RATIOS:
- P/E Ratio: {fmt_ratio(valuation_ratios['ratios'].get('pe_ratio'))}
- P/B Ratio: {fmt_ratio(valuation_ratios['ratios'].get('pb_ratio'))}
- P/S Ratio: {fmt_ratio(valuation_ratios['ratios'].get('ps_ratio'))}
- Book Value per Share: {fmt_price(valuation_ratios['ratios'].get('book_value_per_share'))}
- Revenue per Share: {fmt_price(valuation_ratios['ratios'].get('revenue_per_share'))}
- EPS: {fmt_price(valuation_ratios['ratios'].get('eps'))}

Please provide a comprehensive fundamental analysis including:

1. PROFITABILITY ANALYSIS:
   - Revenue and income trends
   - Margin analysis and trends
   - Operating efficiency
   - Comparison to industry standards
   - IMPORTANT: Analyze the quarterly trends shown above
   - IMPORTANT: Consider how your analysis compares to previous recommendations

2. FINANCIAL HEALTH ASSESSMENT:
   - Liquidity position
   - Debt management
   - Cash flow analysis
   - Balance sheet strength

3. GROWTH ANALYSIS:
   - Historical growth rates
   - Growth sustainability
   - Future growth potential
   - Growth quality assessment

5. RISK ASSESSMENT:
   - Financial risks
   - Business risks
   - Market position risks
   - Growth execution risks

6. INVESTMENT RECOMMENDATION:
   - Fundamental outlook
   - Investment thesis
   - Risk/reward assessment
   - Price target range
   - Investment horizon

Format your response as:
RECOMMENDATION: [STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL]
CONFIDENCE: [1-100]
PRICE_TARGET_RANGE: $[low] - $[high]
TIME_HORIZON: [SHORT/MEDIUM/LONG]
RISK_LEVEL: [LOW/MEDIUM/HIGH]
ANALYSIS: [Detailed analysis]
"""
        
        return prompt

    def _parse_analysis_response(self, response_text: str) -> Dict:
        """Parse the analysis response"""
        try:
            # Extract key information
            recommendation = "HOLD"
            confidence = 50
            price_target_low = None
            price_target_high = None
            time_horizon = "MEDIUM"
            risk_level = "MEDIUM"
            analysis = response_text
            
            # Parse recommendation
            if "RECOMMENDATION:" in response_text:
                rec_match = response_text.split("RECOMMENDATION:")[1].split("\n")[0].strip()
                if rec_match in ["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]:
                    recommendation = rec_match
            
            # Parse confidence
            if "CONFIDENCE:" in response_text:
                conf_match = response_text.split("CONFIDENCE:")[1].split("\n")[0].strip()
                try:
                    confidence = int(conf_match)
                except ValueError:
                    pass
            
            # Parse price target range
            if "PRICE_TARGET_RANGE:" in response_text:
                target_match = response_text.split("PRICE_TARGET_RANGE:")[1].split("\n")[0].strip()
                try:
                    low, high = target_match.replace("$", "").split("-")
                    price_target_low = float(low.strip())
                    price_target_high = float(high.strip())
                except (ValueError, IndexError):
                    pass
            
            # Parse time horizon
            if "TIME_HORIZON:" in response_text:
                horizon_match = response_text.split("TIME_HORIZON:")[1].split("\n")[0].strip()
                if horizon_match in ["SHORT", "MEDIUM", "LONG"]:
                    time_horizon = horizon_match
            
            # Parse risk level
            if "RISK_LEVEL:" in response_text:
                risk_match = response_text.split("RISK_LEVEL:")[1].split("\n")[0].strip()
                if risk_match in ["LOW", "MEDIUM", "HIGH"]:
                    risk_level = risk_match
            
            return {
                'recommendation': recommendation,
                'confidence': confidence,
                'price_target': {
                    'low': price_target_low,
                    'high': price_target_high
                },
                'time_horizon': time_horizon,
                'risk_level': risk_level,
                'analysis': analysis
            }
            
        except Exception as e:
            print(f"❌ Error parsing fundamental analysis: {e}")
            return {
                'recommendation': 'HOLD',
                'confidence': 50,
                'price_target': {'low': None, 'high': None},
                'time_horizon': 'MEDIUM',
                'risk_level': 'MEDIUM',
                'analysis': response_text,
                'parse_error': str(e)
            }

    def _save_analysis(self, symbol: str, analysis_data: Dict):
        """Save fundamental analysis to file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{symbol}_fundamental_analysis_{timestamp}.json"
            filepath = os.path.join(self.output_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(analysis_data, f, indent=2)
            
            print(f"✅ Fundamental analysis saved: {filepath}")
            
        except Exception as e:
            print(f"❌ Error saving fundamental analysis for {symbol}: {e}")

    def _analyze_price_only(self, data: Dict, current_date: str = None) -> Dict:
        """Analyze fundamentals using only price data when financial statements are unavailable"""
        try:
            symbol = data.get('symbol', '')
            company = data.get('company_name', symbol)
            sector = data.get('sector', 'Unknown')
            current_price = data.get('current_price', 0)
            
            # Convert current_date to datetime if provided
            analysis_date = datetime.now()
            if current_date:
                if isinstance(current_date, str):
                    analysis_date = datetime.strptime(current_date, '%Y-%m-%d')
                else:
                    analysis_date = current_date
                    
            # Calculate basic price metrics
            historical_data = data.get('historical_prices', [])
            if historical_data:
                prices = [float(d['close']) for d in historical_data]
                volumes = [float(d['volume']) for d in historical_data]
                
                # Calculate price performance
                price_1y_ago = prices[0] if len(prices) >= 200 else None
                price_6m_ago = prices[int(len(prices)*0.5)] if len(prices) >= 120 else None
                price_3m_ago = prices[int(len(prices)*0.75)] if len(prices) >= 60 else None
                
                metrics = {
                    'price_performance': {
                        '1y_return': (current_price - price_1y_ago) / price_1y_ago if price_1y_ago else None,
                        '6m_return': (current_price - price_6m_ago) / price_6m_ago if price_6m_ago else None,
                        '3m_return': (current_price - price_3m_ago) / price_3m_ago if price_3m_ago else None,
                        'volatility': np.std([(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]) * np.sqrt(252) if len(prices) > 1 else None
                    },
                    'trading_metrics': {
                        'avg_volume': np.mean(volumes) if volumes else None,
                        'current_price': current_price,
                        'price_range': {
                            'high': max(prices) if prices else None,
                            'low': min(prices) if prices else None
                        }
                    }
                }
            else:
                metrics = {}
            
            # Build simplified prompt
            prompt = f"""
Analyze the fundamental outlook for {company} ({symbol}) in the {sector} sector.

**Important Note**: Financial statement data is not available for this analysis. Please provide an assessment based on:
1. The company's business model and sector position
2. Market performance and trading characteristics
3. Industry trends and competitive position
4. General investment outlook

Current Price: ${current_price:.2f}
Analysis Period: {self.start_date.strftime('%Y-%m-%d')} to {analysis_date.strftime('%Y-%m-%d')}

Please provide a comprehensive fundamental analysis including:

1. BUSINESS MODEL ASSESSMENT:
   - Core business strengths
   - Revenue model sustainability
   - Market position
   - Competitive advantages

2. SECTOR ANALYSIS:
   - {sector} sector outlook
   - Industry trends
   - Growth drivers
   - Competitive landscape

3. INVESTMENT THESIS:
   - Long-term growth potential
   - Key value drivers
   - Market opportunities
   - Strategic positioning

4. RISK ASSESSMENT:
   - Business risks
   - Market risks
   - Execution risks
   - Regulatory risks

5. INVESTMENT RECOMMENDATION:
   - Fundamental outlook
   - Investment thesis
   - Risk/reward assessment
   - Price outlook
   - Investment horizon

Format your response as:
RECOMMENDATION: [STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL]
CONFIDENCE: [1-100]
PRICE_OUTLOOK: [POSITIVE/NEUTRAL/NEGATIVE]
TIME_HORIZON: [SHORT/MEDIUM/LONG]
RISK_LEVEL: [LOW/MEDIUM/HIGH]
ANALYSIS: [Detailed analysis]
"""
            
            # Get analysis from Gemini
            response = self.gemini_client.generate_content(prompt)
            if not response or not response.text:
                print(f"❌ No response from Gemini for {symbol}")
                return None
            
            # Parse response
            analysis_parsed = self._parse_price_only_response(response.text)
            
            # Format result
            result = {
                'symbol': symbol,
                'company_name': company,
                'sector': sector,
                'analysis_date': analysis_date.isoformat(),
                'data_range': {
                    'start': self.start_date.isoformat(),
                    'end': analysis_date.isoformat()
                },
                'note': 'Analysis based on price data only - financial statements not available',
                'metrics': metrics,
                'analysis': analysis_parsed,
                'model_used': self.model
            }
            
            # Save analysis
            self._save_analysis(symbol, result)
            
            return result
            
        except Exception as e:
            print(f"❌ Error in price-only analysis for {symbol}: {e}")
            return None

    def _parse_price_only_response(self, response_text: str) -> Dict:
        """Parse response for price-only analysis"""
        try:
            # Extract key information
            recommendation = "HOLD"
            confidence = 50
            price_outlook = "NEUTRAL"
            time_horizon = "MEDIUM"
            risk_level = "MEDIUM"
            analysis = response_text
            
            # Parse recommendation
            if "RECOMMENDATION:" in response_text:
                rec_match = response_text.split("RECOMMENDATION:")[1].split("\n")[0].strip()
                if rec_match in ["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]:
                    recommendation = rec_match
            
            # Parse confidence
            if "CONFIDENCE:" in response_text:
                conf_match = response_text.split("CONFIDENCE:")[1].split("\n")[0].strip()
                try:
                    confidence = int(conf_match)
                except ValueError:
                    pass
            
            # Parse price outlook
            if "PRICE_OUTLOOK:" in response_text:
                outlook_match = response_text.split("PRICE_OUTLOOK:")[1].split("\n")[0].strip()
                if outlook_match in ["POSITIVE", "NEUTRAL", "NEGATIVE"]:
                    price_outlook = outlook_match
            
            # Parse time horizon
            if "TIME_HORIZON:" in response_text:
                horizon_match = response_text.split("TIME_HORIZON:")[1].split("\n")[0].strip()
                if horizon_match in ["SHORT", "MEDIUM", "LONG"]:
                    time_horizon = horizon_match
            
            # Parse risk level
            if "RISK_LEVEL:" in response_text:
                risk_match = response_text.split("RISK_LEVEL:")[1].split("\n")[0].strip()
                if risk_match in ["LOW", "MEDIUM", "HIGH"]:
                    risk_level = risk_match
            
            return {
                'recommendation': recommendation,
                'confidence': confidence,
                'price_outlook': price_outlook,
                'time_horizon': time_horizon,
                'risk_level': risk_level,
                'analysis': analysis
            }
            
        except Exception as e:
            print(f"❌ Error parsing price-only analysis: {e}")
            return {
                'recommendation': 'HOLD',
                'confidence': 50,
                'price_outlook': 'NEUTRAL',
                'time_horizon': 'MEDIUM',
                'risk_level': 'MEDIUM',
                'analysis': response_text,
                'parse_error': str(e)
            }
