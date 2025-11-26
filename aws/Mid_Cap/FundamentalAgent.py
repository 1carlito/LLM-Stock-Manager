"""
Fundamental Analysis Agent
=======================

Analyzes company fundamentals using financial statements and metrics.
"""

import os
import json
import re
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv
import numpy as np
import glob
import requests

# Load environment variables, prefer global ~/.env then local .env
home_env_path = os.path.expanduser('~/.env')
if os.path.exists(home_env_path):
    load_dotenv(dotenv_path=home_env_path)

# Load default API key - use DeepSeek via Chutes
default_api_key = os.getenv('DEEPSEEK_API_KEY_2') 
MODEL_NAME = 'deepseek-ai/DeepSeek-V3.1'
CHUTES_API_URL = os.getenv("CHUTES_API_URL", "https://llm.chutes.ai/v1/chat/completions")

class FundamentalAgent:
    """
    Fundamental Analysis Agent that examines financial statements,
    ratios, and company information for stock valuation.
    """
    # Class-level cache for analysis results
    _analysis_cache = {}  # Format: {symbol: {date: analysis_result}}
    _last_earnings_date = {}  # Format: {symbol: latest_earnings_date}
    _regenerate_cycle = 1  # Regenerate analysis every day for P/E and P/B updates

    def __init__(self, data_dir: str = ".", start_date: str = None, end_date: str = None, api_key_override: str = None, stock_data_path: str = None):
        """Initialize the Fundamental Agent
        
        Args:
            data_dir: Directory for data storage
            start_date: Start date for analysis (optional)
            end_date: End date for analysis (optional)
            api_key_override: Optional API key to use instead of default from .env
            stock_data_path: Optional path to historical price data file (e.g., stock_data_20251009_163317.json)
                            If provided, this file will be used for price lookups to calculate PE/PB ratios
        """
        # .env already loaded at module level
        self.data_dir = data_dir
        self.output_dir = os.path.join(data_dir, "fundamental_test_reports")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Store historical price data file path (for PE/PB calculations)
        self.historical_price_file = stock_data_path
        
        # Set data range (dates should be provided by caller, no defaults)
        if not start_date or not end_date:
            raise ValueError("start_date and end_date must be provided to FundamentalAgent")
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.cutoff_date = datetime.strptime(end_date, "%Y-%m-%d")

        # Use override API key if provided, otherwise use default DeepSeek key
        self.api_key = api_key_override or default_api_key
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY_2 environment variable not set and no override provided")
        
        self.model = MODEL_NAME
        if self.historical_price_file:
            print(f"✅ DeepSeek FundamentalAgent initialized with {MODEL_NAME} (historical prices from: {self.historical_price_file})")
        else:
            print(f"✅ DeepSeek FundamentalAgent initialized with {MODEL_NAME}")

    def _get_previous_analyses(self, symbol: str, current_date: str = None, days: int = 4) -> List[Dict]:
        """Get the previous N days of analyses for this symbol"""
        try:
            # Get previous fundamental analysis files
            files = glob.glob(os.path.join(self.output_dir, f"{symbol}_fundamental_analysis_*.json"))
            
            if not files:
                return []
                
            # Parse dates from filenames
            previous_analyses = []
            target_date = datetime.strptime(current_date, "%Y-%m-%d") if current_date else datetime.now()
            
            for file_path in files:
                try:
                    # Extract date from filename
                    # Format: SYMBOL_fundamental_analysis_YYYYMMDD_HHMMSS.json
                    file_parts = os.path.basename(file_path).split('_')
                    if len(file_parts) < 5:
                        continue
                        
                    # Get date part (second to last) and time part (last, remove .json)
                    date_part = file_parts[-2]  # YYYYMMDD
                    time_part = file_parts[-1].replace('.json', '')  # HHMMSS
                    date_str = f"{date_part}_{time_part}"  # YYYYMMDD_HHMMSS
                    file_date = datetime.strptime(date_str, "%Y%m%d_%H%M%S")
                    
                    # Only include analyses before current date
                    if file_date.date() < target_date.date():
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                            previous_analyses.append(data)
                except Exception as e:
                    print(f"Error parsing previous analysis {file_path}: {e}")
            
            # Sort by date
            previous_analyses.sort(key=lambda x: x.get('analysis_date', '2000-01-01'))
            
            # Return most recent N
            return previous_analyses[-days:] if previous_analyses else []
            
        except Exception as e:
            print(f"Error getting previous analyses: {e}")
            return []

    def analyze_fundamentals(self, symbol: str, current_date: str = None) -> Dict:
        """
        Analyze company fundamentals for the given stock symbol.
        
        Args:
            symbol: Stock ticker symbol
            current_date: Analysis date in YYYY-MM-DD format
            
        Returns:
            Dictionary with fundamental analysis results
        """
        print(f"\n🔍 Analyzing {symbol} fundamentals...")
        try:
            # Normalize date
            if current_date:
                target_date = datetime.strptime(current_date, "%Y-%m-%d")
            else:
                target_date = datetime.now()
                current_date = target_date.strftime("%Y-%m-%d")
            
            # Get data from stock_data.json
            stock_data = self._find_stock_data(symbol)

            if not stock_data:
                print(f"❌ No stock data found for {symbol}")
                return {
                    'symbol': symbol,
                    'analysis_date': current_date,
                    'recommendation': 'HOLD',
                    'confidence': 0.5,
                    'summary': 'No fundamental data available',
                    'error': 'No data found'
                }

            # Check if we need to regenerate the analysis
            should_regenerate = self._should_regenerate_analysis(symbol, current_date, stock_data)
            
            if should_regenerate:
                print(f"Generating new fundamental analysis for {symbol} on {current_date}")
                # Create context for analysis (pass current_date to filter future data)
                prompt = self._create_fundamental_prompt(symbol, stock_data, current_date)
    
                # Get previous analyses for context
                previous_analyses = self._get_previous_analyses(symbol, current_date)
                if previous_analyses:
                    prompt += "\n\nPREVIOUS ANALYSES:\n"
                    prompt += json.dumps(previous_analyses, indent=2)
                    prompt += "\n\nConsider these previous analyses for consistency, but update based on new data."
    
                # Call OpenAI API
                print(f"Calling Claude API for {symbol} fundamental analysis...")
                analysis_result = self._call_llm_api(prompt)
                
                # Parse the response
                result = self._parse_fundamental_analysis(analysis_result, symbol, current_date, stock_data)
                
                # Cache the analysis result
                if symbol not in self._analysis_cache:
                    self._analysis_cache[symbol] = {}
                self._analysis_cache[symbol][current_date] = result
                
                # Update last earnings date
                latest_income_stmt = self._get_latest_statement(stock_data.get('income_statement', []))
                if latest_income_stmt and 'date' in latest_income_stmt:
                    self._last_earnings_date[symbol] = latest_income_stmt['date']
                
                return result
            else:
                print(f"Reusing cached analysis for {symbol}, updating price/ratios only")
                # Get the cached analysis and update price/ratios
                cached_analysis = self._update_cached_analysis(symbol, current_date, stock_data)
                return cached_analysis

        except Exception as e:
            print(f"❌ Error in fundamental analysis: {e}")
            return {
                'symbol': symbol,
                'analysis_date': current_date or datetime.now().strftime("%Y-%m-%d"),
                'recommendation': 'HOLD',
                'confidence': 0.5,
                'summary': f'Error performing analysis: {str(e)}',
                'error': str(e)
            }

    def _should_regenerate_analysis(self, symbol: str, current_date: str, stock_data: Dict) -> bool:
        """Determine if we need to regenerate the analysis"""
        # Case 1: No cached analysis for this symbol or date
        if (symbol not in self._analysis_cache or 
            current_date not in self._analysis_cache[symbol]):
            return True
            
        # Case 2: New earnings data available
        latest_income_stmt = self._get_latest_statement(stock_data.get('income_statement', []))
        if latest_income_stmt and 'date' in latest_income_stmt:
            latest_date = latest_income_stmt['date']
            if (symbol not in self._last_earnings_date or 
                latest_date != self._last_earnings_date[symbol]):
                return True
        
        # Case 3: Every day for PE/PB recalculation
        if symbol in self._analysis_cache and current_date in self._analysis_cache[symbol]:
            cached_analysis = self._analysis_cache[symbol][current_date]
            analysis_date = cached_analysis.get('analysis_date')
            if analysis_date:
                try:
                    date_obj = datetime.strptime(analysis_date, "%Y-%m-%d")
                    current_date_obj = datetime.strptime(current_date, "%Y-%m-%d")
                    days_diff = (current_date_obj - date_obj).days
                    if days_diff >= self._regenerate_cycle and days_diff > 0:
                        return True
                except ValueError:
                    pass
        
        return False
    
    def _get_latest_statement(self, statements: List[Dict]) -> Optional[Dict]:
        """Get the most recent financial statement BY FILING DATE (not statement date)"""
        if not statements:
            return None
            
        sorted_statements = sorted(
            statements, 
            key=lambda x: (x.get('fillingDate') or x.get('date', '1900-01-01')).split()[0], 
            reverse=True
        )
        return sorted_statements[0] if sorted_statements else None
        
    def _update_cached_analysis(self, symbol: str, current_date: str, stock_data: Dict) -> Dict:
        """Update price and ratios in cached analysis"""
        # Get the cached analysis
        cached_analysis = self._analysis_cache[symbol][current_date].copy()
        
        # Update the analysis date
        cached_analysis['analysis_date'] = current_date
        
        # Update the current price
        current_price = self._get_current_price(symbol, current_date, stock_data)
        cached_analysis['current_price'] = current_price
        
        # Calculate and update PE/PB ratios
        latest_eps = self._get_latest_eps(stock_data)
        if current_price is not None and latest_eps and latest_eps != 0:
            pe_ratio = current_price / latest_eps
            cached_analysis['pe_ratio'] = pe_ratio
        
        # Calculate PB ratio if available
        latest_book_value_per_share = self._get_latest_book_value_per_share(stock_data)
        if current_price is not None and latest_book_value_per_share and latest_book_value_per_share > 0:
            pb_ratio = current_price / latest_book_value_per_share
            cached_analysis['pb_ratio'] = pb_ratio
        
        return cached_analysis
    
    def _get_current_price(self, symbol: str, current_date: str, stock_data: Dict) -> Optional[float]:
        """Extract current price from data for the given date
        
        First tries to get price from historical_price_file if provided,
        otherwise falls back to stock_data historical_prices.
        """
        current_price: Optional[float] = None
        historical_prices = []
        
        # Try to get historical prices from dedicated price file first
        if self.historical_price_file and os.path.exists(self.historical_price_file):
            try:
                with open(self.historical_price_file, 'r') as f:
                    price_data = json.load(f)
                    if symbol in price_data:
                        historical_prices = price_data[symbol].get('historical_prices', [])
            except Exception as e:
                print(f"⚠️  Error loading historical price file {self.historical_price_file}: {e}")
        
        # Fall back to stock_data historical_prices if not found in price file
        if not historical_prices:
            historical_prices = stock_data.get('historical_prices', [])
        
        if historical_prices and current_date:
            target_date_obj = datetime.strptime(current_date, "%Y-%m-%d")
            sorted_prices = sorted(historical_prices, key=lambda x: x.get('date', ''), reverse=True)
            
            for price_entry in sorted_prices:
                price_date_str = price_entry.get('date', '')
                if price_date_str:
                    try:
                        price_date = datetime.strptime(price_date_str, '%Y-%m-%d')
                        if price_date <= target_date_obj:
                            price_value = price_entry.get('close')
                            if isinstance(price_value, (int, float)):
                                current_price = float(price_value)
                                break
                    except ValueError:
                        continue
        
        return current_price
    
    def _get_latest_eps(self, stock_data: Dict) -> Optional[float]:
        """Get TTM (Trailing Twelve Months) EPS from income statements"""
        # Get from income statement (most reliable and time-filtered source)
        income_statements = stock_data.get('income_statement', [])
        if not income_statements:
            return None
        
        # Sort by filing date to get most recent statements
        sorted_statements = sorted(
            income_statements,
            key=lambda x: (x.get('fillingDate') or x.get('date', '1900-01-01')).split()[0],
            reverse=True
        )
        
        # Sum last 4 quarters to get TTM EPS (if quarterly data)
        # or use annual EPS if available
        ttm_eps = 0
        quarters_found = 0
        
        for stmt in sorted_statements[:4]:  # Look at up to 4 most recent statements
            eps = stmt.get('eps', 0)
            period = stmt.get('period', '')
            
            # If it's annual data, use it directly
            if period == 'FY':
                return eps
            
            # Otherwise sum quarterly EPS
            if eps and period.startswith('Q'):
                ttm_eps += eps
                quarters_found += 1
        
        # Return TTM EPS if we found at least 4 quarters
        if quarters_found >= 4:
            return ttm_eps
        elif quarters_found > 0:
            # If less than 4 quarters, still return what we have (better than nothing)
            return ttm_eps
        
        return None
    
    def _get_latest_book_value_per_share(self, stock_data: Dict) -> Optional[float]:
        """Calculate book value per share from latest balance sheet"""
        balance_sheets = stock_data.get('balance_sheet', [])
        if not balance_sheets:
            return None
            
        latest_balance = self._get_latest_statement(balance_sheets)
        if not latest_balance:
            return None
        
        # Calculate book value (total equity)
        total_equity = latest_balance.get('totalEquity') or latest_balance.get('totalStockholdersEquity', 0)
        if not total_equity or total_equity <= 0:
            return None
        
        # Get shares outstanding from income statement (most reliable source)
        shares_outstanding = None
        
        income_statements = stock_data.get('income_statement', [])
        if income_statements:
            latest_income = self._get_latest_statement(income_statements)
            if latest_income:
                shares_outstanding = (
                    latest_income.get('weightedAverageShsOut') or 
                    latest_income.get('weightedAverageShsOutDil') or
                    None
                )
        
        if shares_outstanding and shares_outstanding > 0:
            return total_equity / shares_outstanding
            
        return None
        
    def _call_llm_api(self, prompt: str) -> str:
        """Call DeepSeek API via Chutes with the given prompt"""
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a professional fundamental analyst."},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "max_tokens": 4000,
            "temperature": 0.2,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                CHUTES_API_URL,
                headers=headers,
                json=body,
                timeout=120,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"Chutes API request failed: {exc}") from exc

        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected Chutes response format: {data}") from exc

    def _create_fundamental_prompt(self, symbol: str, stock_data: Dict, current_date: str = None) -> str:
        """Create a prompt for fundamental analysis with date filtering to prevent look-ahead bias"""
        # Filter financial statements by date to prevent look-ahead bias
        if current_date:
            target_date = datetime.strptime(current_date, "%Y-%m-%d")
        else:
            target_date = datetime.now()
            current_date = target_date.strftime("%Y-%m-%d")
        
        # Filter income statements - only use those filed on or before analysis date
        # Use fillingDate (when filed with SEC) instead of date (statement period end) to avoid look-ahead bias
        income_statements = stock_data.get('income_statement', [])
        filtered_income = []
        for stmt in income_statements:
            # Try fillingDate first (when actually filed), fallback to date if not available
            filing_date_str = stmt.get('fillingDate', '') or stmt.get('date', '')
            if filing_date_str:
                try:
                    # Handle both full datetime format and date-only format
                    filing_date = datetime.strptime(filing_date_str.split()[0], '%Y-%m-%d')
                    if filing_date <= target_date:
                        filtered_income.append(stmt)
                except ValueError:
                    continue
        
        # Filter balance sheets - use filing date to avoid look-ahead bias
        balance_sheets = stock_data.get('balance_sheet', [])
        filtered_balance = []
        for stmt in balance_sheets:
            # Try fillingDate first (when actually filed), fallback to date if not available
            filing_date_str = stmt.get('fillingDate', '') or stmt.get('date', '')
            if filing_date_str:
                try:
                    # Handle both full datetime format and date-only format
                    filing_date = datetime.strptime(filing_date_str.split()[0], '%Y-%m-%d')
                    if filing_date <= target_date:
                        filtered_balance.append(stmt)
                except ValueError:
                    continue
        
        # Filter cash flow statements - use filing date to avoid look-ahead bias
        cash_flows = stock_data.get('cash_flow', [])
        filtered_cash_flow = []
        for stmt in cash_flows:
            # Try fillingDate first (when actually filed), fallback to date if not available
            filing_date_str = stmt.get('fillingDate', '') or stmt.get('date', '')
            if filing_date_str:
                try:
                    # Handle both full datetime format and date-only format
                    filing_date = datetime.strptime(filing_date_str.split()[0], '%Y-%m-%d')
                    if filing_date <= target_date:
                        filtered_cash_flow.append(stmt)
                except ValueError:
                    continue
        
        # Rebuild financial_data arrays from filtered statements
        financial_data = {
            'revenue': [],
            'netIncome': [],
            'eps': []
        }
        
        for stmt in filtered_income:
            financial_data['revenue'].append(stmt.get('revenue', 0))
            financial_data['netIncome'].append(stmt.get('netIncome', 0))
            financial_data['eps'].append(stmt.get('eps', 0))
        
        # Extract other data
        profile = stock_data.get('profile', {})
        
        company_name = profile.get('companyName', symbol)
        sector = profile.get('sector', 'Unknown')
        industry = profile.get('industry', 'Unknown')
        description = profile.get('description', 'No description available')
        
        # Calculate current price and key ratios
        current_price = self._get_current_price(symbol, current_date, stock_data)
        
        # Calculate PE ratio
        latest_eps = self._get_latest_eps(stock_data)
        pe_ratio = None
        if current_price is not None and latest_eps and latest_eps > 0:
            pe_ratio = current_price / latest_eps
            
        # Calculate PB ratio
        latest_book_value = self._get_latest_book_value_per_share(stock_data)
        pb_ratio = None
        if current_price is not None and latest_book_value and latest_book_value > 0:
            pb_ratio = current_price / latest_book_value
        
        # Calculate ratio strings for display
        pe_ratio_str = f"{pe_ratio:.2f}" if pe_ratio is not None else "N/A"
        pb_ratio_str = f"{pb_ratio:.2f}" if pb_ratio is not None else "N/A"
        current_price_str = f"${current_price:.2f}" if current_price is not None else "Not available"
        
        # Create prompt with filtered data - limit to 6 quarters for sliding window
        prompt = f"""
You are a professional fundamental analyst analyzing {symbol} ({company_name}) on {current_date}.

COMPANY PROFILE:
- Sector: {sector}
- Industry: {industry}
- Description: {description}

FINANCIAL DATA (as of {current_date}):
{json.dumps(financial_data, indent=2)}

INCOME STATEMENTS (filtered to {current_date}, last 6 quarters):
{json.dumps(filtered_income[:6], indent=2) if filtered_income else "[]"}

BALANCE SHEETS (filtered to {current_date}, last 6 quarters):
{json.dumps(filtered_balance[:6], indent=2) if filtered_balance else "[]"}

CASH FLOW STATEMENTS (filtered to {current_date}, last 6 quarters):
{json.dumps(filtered_cash_flow[:6], indent=2) if filtered_cash_flow else "[]"}

CURRENT PRICE AND KEY RATIOS:
- Current Price: {current_price_str}
- P/E Ratio: {pe_ratio_str}
- P/B Ratio: {pb_ratio_str}

TASK: Perform a comprehensive fundamental analysis of {symbol}. Analyze the company's financials, growth trajectory, market position, and overall health.

Consider:
1. Profitability metrics (margins, ROE, ROA)
2. Growth trends (revenue, earnings, cash flow)
3. Debt levels and financial stability
4. Valuation metrics (P/E, P/S, PEG, etc.)
5. Industry positioning and competitive advantages
6. Management quality and capital allocation
7. Long-term business model sustainability

Based on this fundamental analysis, provide:
1. A RECOMMENDATION: BUY, HOLD, or SELL
2. A CONFIDENCE level: Low (0.5-0.64), Medium (0.65-0.79), or High (0.8-1.0)
3. Explanation of key positive factors
4. Explanation of key negative factors
5. Overall assessment of investment attractiveness

FORMAT YOUR RESPONSE AS:
RECOMMENDATION: [BUY/HOLD/SELL]
CONFIDENCE: [0.0-1.0]
SUMMARY: [One-sentence summary]

ANALYSIS:
[Detailed analysis with bullet points under sections]

STRENGTHS:
- [Strength 1]
- [Strength 2]
...

WEAKNESSES:
- [Weakness 1]
- [Weakness 2]
...

FINANCIAL HEALTH:
[Assessment of financial health with metrics]

CONCLUSION:
[Paragraph that justifies the recommendation and confidence level]

Make sure your recommendation is consistent with the overall analysis. If the data suggests mixed signals, reflect this in your confidence level. Provide a nuanced view, not just simplistic "good" or "bad" observations.
"""
        return prompt

    def _parse_fundamental_analysis(self, response: str, symbol: str, current_date: str, stock_data: Dict) -> Dict:
        """Parse the LLM response into structured fundamental analysis"""
        try:
            # Extract current price from historical prices for the target date
            current_price = self._get_current_price(symbol, current_date, stock_data)
            
            # Calculate PE and PB ratios
            latest_eps = self._get_latest_eps(stock_data)
            if current_price is not None and latest_eps and latest_eps > 0:
                pe_ratio = current_price / latest_eps
            else:
                pe_ratio = None
            
            latest_book_value = self._get_latest_book_value_per_share(stock_data)
            if current_price is not None and latest_book_value and latest_book_value > 0:
                pb_ratio = current_price / latest_book_value
            else:
                pb_ratio = None
            
            result = {
                'symbol': symbol,
                'analysis_date': current_date,
                'target_date': current_date,
                'current_price': current_price,
                'pe_ratio': pe_ratio,
                'pb_ratio': pb_ratio,
                'raw_response': response
            }
            
            # Extract recommendation
            recommendation_match = re.search(r'RECOMMENDATION:\s*(BUY|HOLD|SELL)', response, re.IGNORECASE)
            if recommendation_match:
                result['recommendation'] = recommendation_match.group(1).upper()
            else:
                result['recommendation'] = 'HOLD'
                
            # Extract confidence
            confidence_match = re.search(r'CONFIDENCE:\s*(0\.\d+|1\.0)', response)
            if confidence_match:
                result['confidence'] = float(confidence_match.group(1))
            else:
                result['confidence'] = 0.5
                
            # Extract summary
            summary_match = re.search(r'SUMMARY:\s*(.+?)(?:\n|$)', response)
            if summary_match:
                result['summary'] = summary_match.group(1).strip()
            else:
                result['summary'] = 'No summary provided'
            
            # Extract strengths
            strengths = []
            strengths_section = re.search(r'STRENGTHS:(.*?)(?:WEAKNESSES:|FINANCIAL HEALTH:|VALUATION:|CONCLUSION:)', response, re.DOTALL)
            if strengths_section:
                for line in strengths_section.group(1).strip().split('\n'):
                    if line.strip().startswith('-'):
                        strengths.append(line.strip()[1:].strip())
            result['strengths'] = strengths
                
            # Extract weaknesses
            weaknesses = []
            weaknesses_section = re.search(r'WEAKNESSES:(.*?)(?:FINANCIAL HEALTH:|VALUATION:|CONCLUSION:)', response, re.DOTALL)
            if weaknesses_section:
                for line in weaknesses_section.group(1).strip().split('\n'):
                    if line.strip().startswith('-'):
                        weaknesses.append(line.strip()[1:].strip())
            result['weaknesses'] = weaknesses
            
            # Extract conclusion
            conclusion_match = re.search(r'CONCLUSION:(.*?)(?:$)', response, re.DOTALL)
            if conclusion_match:
                result['conclusion'] = conclusion_match.group(1).strip()
            else:
                result['conclusion'] = 'No conclusion provided'
            
            # Add model used
            result['model_used'] = self.model
                
            # Save to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{symbol}_fundamental_analysis_{timestamp}.json"
            filepath = os.path.join(self.output_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(result, f, indent=2)
            
            print(f"✅ Fundamental analysis saved to {filepath}")
            
            return result
            
        except Exception as e:
            print(f"❌ Error parsing fundamental analysis: {e}")
            return {
                'symbol': symbol,
                'analysis_date': current_date,
                'recommendation': 'HOLD',
                'confidence': 0.5,
                'summary': f'Error parsing analysis: {str(e)}',
                'model_used': self.model
            }
            
    def _find_stock_data(self, symbol: str) -> Optional[Dict]:
        """Find stock data in JSON files - uses same data source as ValuationAgent"""
        try:
            import glob
            
            # Primary file: quant_data/mid_cap_stock_data_*.json (same as ValuationAgent)
            quant_data_dir = os.path.join(self.data_dir, "quant_data")
            primary_file = os.path.join(quant_data_dir, "mid_cap_stock_data_20250701_20251101_20251116_132209.json")
            
            # Try the primary file first
            if os.path.exists(primary_file):
                try:
                    with open(primary_file, 'r') as f:
                        data = json.load(f)
                    
                    # Check if symbol exists in this file
                    if isinstance(data, dict):
                        if symbol in data:
                            print(f"✅ Found {symbol} in {primary_file}")
                            return data[symbol]
                        else:
                            print(f"⚠️ Symbol {symbol} not found in {primary_file}")
                except Exception as e:
                    print(f"⚠️ Error reading {primary_file}: {e}")
            
            # Fallback: Try to find any mid_cap_stock_data file in quant_data directory
            if os.path.exists(quant_data_dir):
                mid_cap_files = glob.glob(os.path.join(quant_data_dir, "mid_cap_stock_data_*.json"))
                if mid_cap_files:
                    # Sort by modification time (newest first)
                    mid_cap_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                    
                    for file_path in mid_cap_files:
                        try:
                            with open(file_path, 'r') as f:
                                data = json.load(f)
                            
                            if isinstance(data, dict) and symbol in data:
                                print(f"✅ Found {symbol} in {file_path}")
                                return data[symbol]
                        except Exception:
                            continue
            
            # Fallback: Try stock_data.json (legacy)
            file_path = os.path.join(self.data_dir, "stock_data.json")
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    
                    if isinstance(data, dict) and symbol in data:
                        print(f"✅ Found {symbol} in {file_path}")
                        return data[symbol]
                except Exception as e:
                    print(f"⚠️ Error loading stock_data.json: {e}")
            
            print(f"❌ Could not find stock data for {symbol}")
            return None
            
        except Exception as e:
            print(f"❌ Error finding stock data: {e}")
            return None