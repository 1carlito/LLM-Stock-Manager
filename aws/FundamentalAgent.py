import os
import json
from typing import Dict, List, Optional
from datetime import datetime
from data_utils import DataManager
from dotenv import load_dotenv
import openai

# Load environment variables from .env file
load_dotenv()

# Configure OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')
MODEL_NAME = os.getenv('MODEL_NAME', 'gpt-3.5-turbo')

class FundamentalAgent:
    """
    Fundamental Analysis Agent that examines financial statements,
    ratios, and company information for stock valuation.
    """

    def __init__(self, data_dir: str = ".", cutoff_date: Optional[str] = None):
        self.data_dir = data_dir
        self.data_manager = DataManager(base_dir=data_dir)
        self.output_dir = os.path.join(data_dir, "fundamental_reports")
        self.cutoff_date = datetime.strptime(cutoff_date, "%Y-%m-%d") if cutoff_date else None
        os.makedirs(self.output_dir, exist_ok=True)

    def _filter_data_by_date(self, data: List[Dict], date_key: str = 'date') -> List[Dict]:
        """Filter data to only include entries before cutoff date"""
        if not self.cutoff_date or not data:
            return data
            
        filtered_data = []
        for entry in data:
            if date_key in entry:
                entry_date = datetime.strptime(entry[date_key], "%Y-%m-%d")
                if entry_date <= self.cutoff_date:
                    filtered_data.append(entry)
                    
        return filtered_data

    def _load_stock_data(self, symbol: str) -> Optional[Dict]:
        """Load and filter fundamental data for a stock"""
        try:
            raw_data = self.data_manager.load_stock_data(symbol)
            if not raw_data:
                return None
            
            # Filter financial statements by date if cutoff_date is set
            if self.cutoff_date:
                raw_data['income_statement'] = self._filter_data_by_date(raw_data.get('income_statement', []))
                raw_data['balance_sheet'] = self._filter_data_by_date(raw_data.get('balance_sheet', []))
                raw_data['cash_flow'] = self._filter_data_by_date(raw_data.get('cash_flow', []))
            
            fundamental_data = {
                'company_info': {
                    'symbol': raw_data['symbol'],
                    'company_name': raw_data['company_name'],
                    'sector': raw_data['sector'],
                    'market_cap': raw_data['market_cap'],
                    'dividend_yield': raw_data['dividend_yield']
                },
                'key_metrics': {
                    'eps': raw_data['eps'],
                    'pe_ratio': raw_data['pe_ratio']
                },
                'financial_statements': {
                    'income_statement': raw_data.get('income_statement', []),
                    'balance_sheet': raw_data.get('balance_sheet', []),
                    'cash_flow': raw_data.get('cash_flow', [])
                }
            }
            return fundamental_data
                
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
            latest = income_data[0]  # Most recent quarter/year
            previous = income_data[1] if len(income_data) > 1 else None
            
            metrics = {
                'revenue': latest.get('revenue', 0),
                'net_income': latest.get('netIncome', 0),
                'operating_income': latest.get('operatingIncome', 0),
                'gross_profit_margin': latest.get('grossProfitMargin', 0),
                'operating_margin': latest.get('operatingMargin', 0),
                'net_profit_margin': latest.get('netProfitMargin', 0)
            }
            
            if previous:
                metrics.update({
                    'revenue_growth': (metrics['revenue'] - previous.get('revenue', 0)) / previous.get('revenue', 1),
                    'net_income_growth': (metrics['net_income'] - previous.get('netIncome', 0)) / previous.get('netIncome', 1)
                })
            
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
            latest_bs = balance_sheet[0]  # Most recent balance sheet
            latest_cf = cash_flow[0]  # Most recent cash flow
            
            total_assets = latest_bs.get('totalAssets', 0)
            total_liabilities = latest_bs.get('totalLiabilities', 0)
            current_assets = latest_bs.get('totalCurrentAssets', 0)
            current_liabilities = latest_bs.get('totalCurrentLiabilities', 0)
            
            metrics = {
                'current_ratio': current_assets / current_liabilities if current_liabilities else 0,
                'debt_to_equity': total_liabilities / (total_assets - total_liabilities) if (total_assets - total_liabilities) else 0,
                'operating_cash_flow': latest_cf.get('operatingCashFlow', 0),
                'free_cash_flow': latest_cf.get('freeCashFlow', 0),
                'cash_and_equivalents': latest_bs.get('cashAndCashEquivalents', 0)
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

    def _analyze_valuation(self, company_info: Dict, key_metrics: Dict) -> Dict:
        """Analyze valuation metrics"""
        try:
            metrics = {
                'market_cap': company_info['market_cap'],
                'pe_ratio': key_metrics['pe_ratio'],
                'eps': key_metrics['eps'],
                'dividend_yield': company_info['dividend_yield']
            }
            
            return {
                'status': 'success',
                'metrics': metrics
            }
            
        except Exception as e:
            return {
                'status': f'Error analyzing valuation metrics: {str(e)}',
                'metrics': {}
            }

    def _generate_recommendation(self, analysis_data: Dict) -> Dict:
        """Generate investment recommendation based on fundamental analysis"""
        try:
            metrics = analysis_data['fundamental_analysis']
            company_info = analysis_data['company_info']
            
            # Extract key metrics
            profitability = metrics['profitability']['metrics']
            financial_health = metrics['financial_health']['metrics']
            valuation = metrics['valuation_metrics']['metrics']
            
            # Score different aspects (simple scoring system)
            strengths = []
            concerns = []
            
            # Profitability checks
            if profitability.get('net_profit_margin', 0) > 0.15:
                strengths.append("Strong net profit margin")
            elif profitability.get('net_profit_margin', 0) < 0.05:
                concerns.append("Low net profit margin")
                
            if profitability.get('revenue_growth', 0) > 0.1:
                strengths.append("Solid revenue growth")
            elif profitability.get('revenue_growth', 0) < 0:
                concerns.append("Declining revenue")
                
            # Financial health checks
            if financial_health.get('current_ratio', 0) > 1.5:
                strengths.append("Strong liquidity position")
            elif financial_health.get('current_ratio', 0) < 1:
                concerns.append("Potential liquidity issues")
                
            if financial_health.get('debt_to_equity', 0) < 1:
                strengths.append("Conservative debt levels")
            elif financial_health.get('debt_to_equity', 0) > 2:
                concerns.append("High debt burden")
                
            # Valuation checks
            pe_ratio = valuation.get('pe_ratio', 0)
            if pe_ratio > 0:  # Ensure positive earnings
                if pe_ratio > 30:
                    concerns.append("High valuation (P/E ratio)")
                elif pe_ratio < 15:
                    strengths.append("Attractive valuation (P/E ratio)")
                    
            # Generate recommendation
            if len(strengths) > len(concerns) + 1:
                recommendation = "BUY"
                reason = "Strong fundamentals with multiple positive indicators"
            elif len(concerns) > len(strengths) + 1:
                recommendation = "SELL"
                reason = "Multiple fundamental concerns present"
            else:
                recommendation = "HOLD"
                reason = "Mixed fundamental indicators"
                
            return {
                'recommendation': recommendation,
                'reason': reason,
                'strengths': strengths,
                'concerns': concerns
            }
            
        except Exception as e:
            return {
                'recommendation': 'HOLD',
                'reason': f'Insufficient data for confident recommendation: {str(e)}',
                'strengths': [],
                'concerns': []
            }

    def get_trading_recommendation(self, analysis_data: Dict) -> Dict:
        """Get trading recommendation from LLM based on fundamental analysis"""
        try:
            # Prepare the prompt with analysis data
            prompt = f"""Based on the following fundamental analysis for {analysis_data['company_info']['company_name']} ({analysis_data['company_info']['symbol']}), provide a trading recommendation (BUY/SELL/HOLD) with detailed reasoning:

Company Information:
- Market Cap: ${analysis_data['company_info']['market_cap']:,.2f}
- Sector: {analysis_data['company_info']['sector']}
- Dividend Yield: {analysis_data['company_info']['dividend_yield']}%

Valuation Metrics:
- P/E Ratio: {analysis_data['raw_metrics']['pe_ratio']}
- EPS: ${analysis_data['raw_metrics']['eps']}

Profitability Analysis:
{json.dumps(analysis_data['fundamental_analysis']['profitability']['metrics'], indent=2)}

Financial Health:
{json.dumps(analysis_data['fundamental_analysis']['financial_health']['metrics'], indent=2)}

Please provide:
1. Clear BUY/SELL/HOLD recommendation
2. Key factors supporting this decision
3. Potential risks to consider
4. Price targets or valuation considerations
"""

            response = openai.ChatCompletion.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a professional financial analyst providing trading recommendations based on fundamental analysis."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )

            recommendation = response.choices[0].message.content

            return {
                'status': 'success',
                'recommendation': recommendation
            }

        except Exception as e:
            return {
                'status': f'Error getting recommendation: {str(e)}',
                'recommendation': None
            }

    def prepare_fundamental_analysis(self, symbol: str) -> Optional[Dict]:
        """Prepare fundamental analysis data for LLM"""
        data = self._load_stock_data(symbol)
        if not data:
            return None

        profitability = self._analyze_profitability(data['financial_statements']['income_statement'])
        financial_health = self._analyze_financial_health(
            data['financial_statements']['balance_sheet'],
            data['financial_statements']['cash_flow']
        )
        valuation = self._analyze_valuation(data['company_info'], data['key_metrics'])
        
        analysis_data = {
            'company_info': data['company_info'],
            'fundamental_analysis': {
                'profitability': profitability,
                'financial_health': financial_health,
                'valuation_metrics': valuation
            },
            'raw_metrics': {
                'eps': data['key_metrics']['eps'],
                'pe_ratio': data['key_metrics']['pe_ratio'],
                'recent_financials': {
                    'income_statement': data['financial_statements']['income_statement'][:1],
                    'balance_sheet': data['financial_statements']['balance_sheet'][:1],
                    'cash_flow': data['financial_statements']['cash_flow'][:1]
                }
            }
        }

        # Get trading recommendation
        recommendation = self.get_trading_recommendation(analysis_data)
        analysis_data['trading_recommendation'] = recommendation

        return analysis_data

    def save_analysis(self, symbol: str, analysis_data: Dict):
        """Save fundamental analysis results"""
        if not analysis_data:
            return
            
        self.data_manager.save_analysis_result(
            symbol=symbol,
            analysis_data=analysis_data,
            analysis_type='fundamental',
            output_dir=self.output_dir
        )

def main():
    """Example usage of FundamentalAgent"""
    import argparse
    
    # Ensure environment variables are loaded
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Fundamental analysis for stock valuation")
    parser.add_argument("symbol", help="Stock symbol to analyze")
    parser.add_argument("--data-dir", default=".", help="Directory containing stock data")
    parser.add_argument("--cutoff-date", help="Analyze data only before this date (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    agent = FundamentalAgent(data_dir=args.data_dir, cutoff_date=args.cutoff_date)
    analysis = agent.prepare_fundamental_analysis(args.symbol)
    
    if analysis:
        print(f"\nAnalysis completed for {args.symbol}")
        if args.cutoff_date:
            print(f"Using data before: {args.cutoff_date}")
        print(f"Company: {analysis['company_info']['company_name']}")
        print(f"Market Cap: ${analysis['company_info']['market_cap']:,.2f}")
        print(f"P/E Ratio: {analysis['raw_metrics']['pe_ratio']:.2f}")
        print(f"EPS: ${analysis['raw_metrics']['eps']:.2f}")
        print("\nTrading Recommendation:")
        print("-" * 50)
        if analysis['trading_recommendation']['status'] == 'success':
            print(analysis['trading_recommendation']['recommendation'])
        else:
            print(f"Error: {analysis['trading_recommendation']['status']}")
        agent.save_analysis(args.symbol, analysis)
    else:
        print(f"Could not analyze {args.symbol}")

if __name__ == "__main__":
    main() 