"""
Valuation Analysis Agent
=======================

Analyzes stock valuation using price data and financial metrics.
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import google.generativeai as genai
from dotenv import load_dotenv
import numpy as np
import glob

# Load environment variables from .env in the same directory as this script
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(dotenv_path=env_path)

class ValuationAgent:
    def __init__(self, data_dir: str = ".", api_key_override: str = None):
        """Initialize the Valuation Agent
        
        Args:
            data_dir: Directory for data storage
            api_key_override: Optional API key to use instead of default from .env
        """
        # .env already loaded at module level
        self.data_dir = data_dir
        self.output_dir = os.path.join(data_dir, "valuation_reports")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Set data range
        self.start_date = datetime.strptime("2024-09-20", "%Y-%m-%d")  # Full year
        self.cutoff_date = datetime.strptime("2025-09-18", "%Y-%m-%d")
        
        # Initialize Gemini API - use dedicated valuation key first
        api_key = api_key_override or os.getenv("VALUATION_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            # Try numbered keys as fallback
            for i in range(1, 11):
                key = os.getenv(f"GEMINI_API_KEY_{i}")
                if key:
                    api_key = key
                    break
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set and no override provided")
        
        genai.configure(api_key=api_key)
        self.gemini_client = genai.GenerativeModel("gemini-2.5-flash-lite")
        print("✅ Gemini ValuationAgent initialized")

    def prepare_analysis_data(self, symbol: str, target_date: Optional[str] = None) -> Optional[Dict]:
        """Prepare valuation analysis data for a stock symbol on a specific date"""
        try:
            # Load stock data from raw_multidata
            stock_data_file = os.path.join(self.data_dir, "raw_multidata/stock_data_20251009_163317.json")
            if not os.path.exists(stock_data_file):
                print(f"❌ Stock data file not found: {stock_data_file}")
                return None
            
            with open(stock_data_file, 'r') as f:
                stock_data = json.load(f)
            
            if symbol not in stock_data:
                print(f"❌ No data found for {symbol}")
                return None
            
            # Get all historical data
            all_historical_data = stock_data[symbol].get('historical_prices', [])
            all_historical_data.sort(key=lambda x: x['date'])
            
            # Filter data up to target_date (like AWS version does)
            if target_date:
                # Find data for the specific target date or closest before it
                target_data = None
                filtered_data = []
                
                for price_data in all_historical_data:
                    if price_data['date'] <= target_date:
                        filtered_data.append(price_data)
                        if price_data['date'] == target_date:
                            target_data = price_data
                
                if not filtered_data:
                    print(f"❌ No price data available for {symbol} on or before {target_date}")
                    return None
                
                # Use closest date if exact match not found
                if not target_data:
                    target_data = filtered_data[-1]
                
                current_price = target_data['close']
                actual_date = target_data['date']
            else:
                # No target date - use all data
                filtered_data = all_historical_data
                if not filtered_data:
                    return None
                current_price = filtered_data[-1]['close']
                actual_date = filtered_data[-1]['date']
            
            # Calculate key metrics using data up to target_date
            metrics = self._calculate_metrics(filtered_data)
            
            # Get company info
            company_info = {
                'symbol': symbol,
                'company_name': stock_data[symbol].get('company_name', symbol),
                'sector': stock_data[symbol].get('sector', 'Unknown'),
                'current_price': current_price,
                'target_date': actual_date  # This is the key field for orchestrator matching
            }
            
            # Prepare analysis data
            analysis_data = {
                **company_info,
                'historical_data': filtered_data,
                'metrics': metrics,
                'analysis_date': datetime.now().isoformat(),
                'data_cutoff': self.cutoff_date.isoformat(),
                'data_points': len(filtered_data)
            }
            
            return analysis_data
            
        except Exception as e:
            print(f"❌ Error preparing analysis data for {symbol}: {e}")
            return None

    def _calculate_metrics(self, price_data: List[Dict]) -> Dict:
        """Calculate key valuation metrics"""
        try:
            if not price_data:
                return {}
                
            # Extract price and volume data
            prices = [float(d['close']) for d in price_data]
            volumes = [float(d['volume']) for d in price_data]
            
            # Calculate moving averages
            ma_20 = np.mean(prices[-20:]) if len(prices) >= 20 else None
            ma_50 = np.mean(prices[-50:]) if len(prices) >= 50 else None
            ma_200 = np.mean(prices[-200:]) if len(prices) >= 200 else None
            
            # Calculate price changes
            price_change_1d = (prices[-1] - prices[-2]) / prices[-2] if len(prices) >= 2 else None
            price_change_1w = (prices[-1] - prices[-5]) / prices[-5] if len(prices) >= 5 else None
            price_change_1m = (prices[-1] - prices[-20]) / prices[-20] if len(prices) >= 20 else None
            price_change_3m = (prices[-1] - prices[-60]) / prices[-60] if len(prices) >= 60 else None
            price_change_1y = (prices[-1] - prices[0]) / prices[0] if len(prices) >= 200 else None
            
            # Calculate volatility (standard deviation of returns)
            returns = [((prices[i] - prices[i-1]) / prices[i-1]) for i in range(1, len(prices))]
            volatility = np.std(returns) * np.sqrt(252) if returns else None
            
            # Calculate volume metrics
            avg_volume_10d = np.mean(volumes[-10:]) if len(volumes) >= 10 else None
            avg_volume_30d = np.mean(volumes[-30:]) if len(volumes) >= 30 else None
            volume_change = (volumes[-1] - avg_volume_30d) / avg_volume_30d if avg_volume_30d else None
            
            # Find support and resistance levels
            sorted_prices = sorted(prices)
            support = np.percentile(sorted_prices, 20) if len(sorted_prices) >= 5 else None
            resistance = np.percentile(sorted_prices, 80) if len(sorted_prices) >= 5 else None
            
            return {
                'moving_averages': {
                    'ma_20': ma_20,
                    'ma_50': ma_50,
                    'ma_200': ma_200
                },
                'price_changes': {
                    '1d': price_change_1d,
                    '1w': price_change_1w,
                    '1m': price_change_1m,
                    '3m': price_change_3m,
                    '1y': price_change_1y
                },
                'volatility': volatility,
                'volume_metrics': {
                    'avg_10d': avg_volume_10d,
                    'avg_30d': avg_volume_30d,
                    'volume_change': volume_change
                },
                'technical_levels': {
                    'support': support,
                    'resistance': resistance
                }
            }
            
        except Exception as e:
            print(f"❌ Error calculating metrics: {e}")
            return {}

    def analyze_valuation(self, symbol: str, target_date: Optional[str] = None) -> Optional[Dict]:
        """Analyze valuation for a stock symbol on a specific date"""
        try:
            analysis_data = self.prepare_analysis_data(symbol, target_date)
            if not analysis_data:
                return None
            
            # Generate valuation analysis using Gemini
            prompt = self._build_valuation_prompt(analysis_data)
            
            print(f"📊 Analyzing valuation for {symbol}...")
            response = self.gemini_client.generate_content(prompt)
            
            if response and response.text:
                # Parse the response
                valuation_result = self._parse_valuation_response(response.text, symbol)
                
                # Add calculated metrics and key data to result
                valuation_result['metrics'] = analysis_data['metrics']
                valuation_result['target_date'] = analysis_data.get('target_date')  # Key field for orchestrator
                valuation_result['current_price'] = analysis_data.get('current_price')
                valuation_result['sector'] = analysis_data.get('sector')
                valuation_result['company_name'] = analysis_data.get('company_name')
                
                # Save the analysis
                self.save_analysis(symbol, valuation_result)
                
                print(f"✅ Valuation analysis complete for {symbol}")
                return valuation_result
            else:
                print(f"❌ No response from Gemini for {symbol}")
                return None
                
        except Exception as e:
            print(f"❌ Error analyzing valuation for {symbol}: {e}")
            return None

    def _get_previous_analyses(self, symbol: str, days: int = 4) -> List[Dict]:
        """Get the previous N days of analyses for this symbol"""
        try:
            analyses = []
            pattern = os.path.join(self.output_dir, f"{symbol}_valuation_analysis_*.json")
            files = glob.glob(pattern)
            
            if not files:
                return []
                
            # Sort files by creation time (newest first)
            sorted_files = sorted(files, key=os.path.getmtime, reverse=True)
            
            # Get up to 'days' previous analyses
            for i, filepath in enumerate(sorted_files):
                if i >= days:
                    break
                    
                try:
                    with open(filepath, 'r') as f:
                        analysis = json.load(f)
                        analyses.append({
                            'date': analysis.get('analysis_date', ''),
                            'recommendation': analysis.get('recommendation', 'HOLD'),
                            'confidence': analysis.get('confidence', 50),
                            'price_target': analysis.get('price_target', None),
                            'reasoning': analysis.get('analysis', '').split('\n')[0][:100]  # First line, truncated
                        })
                except Exception as e:
                    print(f"Error reading previous analysis {filepath}: {e}")
                    continue
                    
            return analyses
            
        except Exception as e:
            print(f"Error getting previous analyses: {e}")
            return []

    def _build_valuation_prompt(self, data: Dict) -> str:
        """Build the prompt for valuation analysis"""
        symbol = data['symbol']
        company_name = data['company_name']
        sector = data['sector']
        current_price = data['current_price']
        metrics = data['metrics']
        
        # Format metrics with proper handling of None values
        def fmt_price(val):
            return f"${val:.2f}" if val is not None else "N/A"
            
        def fmt_pct(val):
            return f"{val*100:.1f}%" if val is not None else "N/A"
            
        def fmt_vol(val):
            return f"{val:,.0f}" if val is not None else "N/A"
        
        # Extract recent price history for clearer trend analysis
        recent_prices = []
        if 'historical_data' in data and len(data['historical_data']) > 0:
            # Get the most recent 10 trading days
            recent_data = data['historical_data'][-10:]
            for day in recent_data:
                recent_prices.append({
                    'date': day.get('date', 'Unknown'),
                    'open': day.get('open', 0),
                    'high': day.get('high', 0),
                    'low': day.get('low', 0),
                    'close': day.get('close', 0),
                    'volume': day.get('volume', 0)
                })
        
        # Format recent price history for the prompt
        price_history_text = "Recent Price History (10 trading days):\n"
        if recent_prices:
            price_history_text += "Date       | Open   | High   | Low    | Close  | Volume\n"
            price_history_text += "-----------|--------|--------|--------|--------|------------\n"
            for day in recent_prices:
                price_history_text += f"{day['date']} | ${day['open']:.2f} | ${day['high']:.2f} | ${day['low']:.2f} | ${day['close']:.2f} | {day['volume']:,.0f}\n"
        else:
            price_history_text += "No recent price history available.\n"
        
        # Get previous analyses
        previous_analyses = self._get_previous_analyses(symbol)
        previous_analyses_text = ""
        
        if previous_analyses:
            previous_analyses_text = "\nPREVIOUS VALUATION ANALYSES:\n"
            previous_analyses_text += "Date                     | Recommendation | Confidence | Summary\n"
            previous_analyses_text += "-------------------------|----------------|------------|--------\n"
            
            for analysis in previous_analyses:
                date = analysis.get('date', '').split('T')[0] if 'T' in analysis.get('date', '') else analysis.get('date', '')[:10]
                recommendation = analysis.get('recommendation', 'HOLD')
                confidence = analysis.get('confidence', 50)
                reasoning = analysis.get('reasoning', '')[:50] + "..." if analysis.get('reasoning', '') else "N/A"
                
                previous_analyses_text += f"{date} | {recommendation:14s} | {confidence:10d} | {reasoning}\n"
        
        prompt = f"""
Analyze the valuation of {company_name} ({symbol}) in the {sector} sector.

Current Price: ${current_price:.2f}
Analysis Date: {datetime.now().strftime('%Y-%m-%d')}
Data Range: {self.start_date.strftime('%Y-%m-%d')} to {self.cutoff_date.strftime('%Y-%m-%d')}

{price_history_text}

{previous_analyses_text}

Key Metrics:
1. Moving Averages:
   - 20-day MA: {fmt_price(metrics['moving_averages']['ma_20'])}
   - 50-day MA: {fmt_price(metrics['moving_averages']['ma_50'])}
   - 200-day MA: {fmt_price(metrics['moving_averages']['ma_200'])}

2. Price Changes:
   - 1 Day: {fmt_pct(metrics['price_changes']['1d'])}
   - 1 Week: {fmt_pct(metrics['price_changes']['1w'])}
   - 1 Month: {fmt_pct(metrics['price_changes']['1m'])}
   - 3 Months: {fmt_pct(metrics['price_changes']['3m'])}
   - 1 Year: {fmt_pct(metrics['price_changes']['1y'])}

3. Volatility:
   - Annual Volatility: {fmt_pct(metrics['volatility'])}

4. Volume Analysis:
   - 10-day Avg Volume: {fmt_vol(metrics['volume_metrics']['avg_10d'])}
   - 30-day Avg Volume: {fmt_vol(metrics['volume_metrics']['avg_30d'])}
   - Volume Change: {fmt_pct(metrics['volume_metrics']['volume_change'])}

5. Technical Levels:
   - Support: {fmt_price(metrics['technical_levels']['support'])}
   - Resistance: {fmt_price(metrics['technical_levels']['resistance'])}

Please provide a comprehensive valuation analysis including:

1. PRICE TREND ANALYSIS:
   - Short-term trend (1-2 weeks)
   - Medium-term trend (1-3 months)
   - Long-term trend (6-12 months)
   - Overall price momentum
   - Moving average analysis
   - Support/resistance analysis
   - IMPORTANT: Analyze the recent daily price movements shown above
   - IMPORTANT: Consider how your analysis compares to previous recommendations

2. VOLUME ANALYSIS:
   - Volume trends
   - Volume-price relationship
   - Unusual volume patterns

3. VOLATILITY ASSESSMENT:
   - Current volatility level
   - Historical comparison
   - Risk implications

4. MARKET CONTEXT:
   - Sector performance impact
   - Market conditions
   - Technical positioning

5. INVESTMENT RECOMMENDATION:
   - BUY/SELL/HOLD recommendation
   - Confidence level (1-100)
   - Price target (if applicable)
   - Risk assessment
   - Time horizon

Format your response as:
RECOMMENDATION: [BUY/SELL/HOLD]
CONFIDENCE: [1-100]
PRICE_TARGET: $[target price]
TIME_HORIZON: [SHORT/MEDIUM/LONG]
RISK_LEVEL: [LOW/MEDIUM/HIGH]
ANALYSIS: [Detailed analysis]
"""
        
        return prompt

    def _parse_valuation_response(self, response_text: str, symbol: str) -> Dict:
        """Parse the Gemini response for valuation analysis"""
        try:
            # Extract key information from response
            recommendation = "HOLD"
            confidence = 50
            price_target = None
            time_horizon = "MEDIUM"
            risk_level = "MEDIUM"
            analysis = response_text
            
            # Parse recommendation
            if "RECOMMENDATION:" in response_text:
                rec_match = response_text.split("RECOMMENDATION:")[1].split("\n")[0].strip()
                if rec_match in ["BUY", "SELL", "HOLD"]:
                    recommendation = rec_match
            
            # Parse confidence
            if "CONFIDENCE:" in response_text:
                conf_match = response_text.split("CONFIDENCE:")[1].split("\n")[0].strip()
                try:
                    confidence = int(conf_match)
                except ValueError:
                    pass
            
            # Parse price target
            if "PRICE_TARGET:" in response_text:
                target_match = response_text.split("PRICE_TARGET:")[1].split("\n")[0].strip()
                try:
                    price_target = float(target_match.replace("$", "").replace(",", ""))
                except ValueError:
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
                'symbol': symbol,
                'analysis_date': datetime.now().isoformat(),
                'recommendation': recommendation,
                'confidence': confidence,
                'price_target': price_target,
                'time_horizon': time_horizon,
                'risk_level': risk_level,
                'analysis': analysis,
                'model_used': 'gemini-2.5-flash-lite'
            }
            
        except Exception as e:
            print(f"❌ Error parsing valuation response for {symbol}: {e}")
            return {
                'symbol': symbol,
                'analysis_date': datetime.now().isoformat(),
                'recommendation': 'HOLD',
                'confidence': 50,
                'price_target': None,
                'time_horizon': 'MEDIUM',
                'risk_level': 'MEDIUM',
                'analysis': response_text,
                'model_used': 'gemini-2.5-flash-lite',
                'parse_error': str(e)
            }

    def save_analysis(self, symbol: str, analysis_data: Dict):
        """Save valuation analysis to file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{symbol}_valuation_analysis_{timestamp}.json"
            filepath = os.path.join(self.output_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(analysis_data, f, indent=2)
            
            print(f"💾 Valuation analysis saved: {filename}")
            
        except Exception as e:
            print(f"❌ Error saving valuation analysis for {symbol}: {e}")

if __name__ == "__main__":
    # Test the agent
    agent = ValuationAgent()
    result = agent.analyze_valuation("GOOGL")
    if result:
        print("✅ Valuation analysis test successful")
    else:
        print("❌ Valuation analysis test failed")
