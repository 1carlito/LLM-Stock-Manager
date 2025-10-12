"""
Valuation Analysis Agent
=======================

Analyzes stock valuation using price data and financial metrics.
"""

import os
import json
import openai
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import numpy as np
import glob

# Load environment variables
load_dotenv()

class ValuationAgent:
    def __init__(self, data_dir: str = "."):
        """Initialize the Valuation Agent"""
        load_dotenv()
        self.data_dir = data_dir
        self.output_dir = os.path.join(data_dir, "valuation_reports")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Set data range
        self.start_date = datetime.strptime("2024-12-27", "%Y-%m-%d")  # Start data collection from Dec 27
        self.cutoff_date = datetime.strptime("2025-09-18", "%Y-%m-%d")  # Keep end date the same
        
        # Initialize DeepSeek API
        openai.api_key = 'sk-ab635d865fec40c3a12648ae18cc82a4'  # Dedicated key for NVO valuation analysis
        if not openai.api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable not set")
        openai.api_base = "https://api.deepseek.com/v1"
        
        self.model = "deepseek-reasoner"  # Using the V3 reasoning model (released Dec 26, 2024)
        print("✅ DeepSeek ValuationAgent initialized")

    def prepare_analysis_data(self, symbol: str, current_date: str = None) -> Optional[Dict]:
        """Prepare valuation analysis data for a stock symbol"""
        try:
            # Convert current_date to datetime if provided
            analysis_date = self.cutoff_date  # Use cutoff_date as default
            if current_date:
                if isinstance(current_date, str):
                    analysis_date = datetime.strptime(current_date, '%Y-%m-%d')
                else:
                    analysis_date = current_date
            
            # Load stock data from novo_data.json file
            stock_data_file = os.path.join(self.data_dir, "novo_data.json")
            if not os.path.exists(stock_data_file):
                print(f"❌ Stock data file not found: {stock_data_file}")
                return None
            
            with open(stock_data_file, 'r') as f:
                data = json.load(f)
            
            # For novo_data.json, the data is directly in the file, not keyed by symbol
            
            # Get historical data and filter by date range
            historical_data = data.get('historical_prices', [])
            filtered_data = []
            
            for day_data in historical_data:
                try:
                    date_str = day_data.get('date', '')
                    if date_str:
                        data_date = datetime.strptime(date_str, '%Y-%m-%d')
                        # Only include data up to the current analysis date
                        if self.start_date <= data_date <= analysis_date:
                            filtered_data.append(day_data)
                except ValueError:
                    continue
            
            # Sort data by date
            filtered_data.sort(key=lambda x: x['date'])
            
            # Get current price from the latest available data point (not hardcoded)
            current_price = 0
            if filtered_data:
                current_price = float(filtered_data[-1]['close'])
            
            # Calculate key metrics
            metrics = self._calculate_metrics(filtered_data)
            
            # Get company info
            company_info = {
                'symbol': symbol,
                'company_name': data.get('company_name', symbol),
                'sector': data.get('sector', 'Unknown'),
                'current_price': current_price  # Use calculated current price
            }
            
            # Prepare analysis data
            analysis_data = {
                **company_info,
                'historical_data': filtered_data,
                'metrics': metrics,
                'analysis_date': analysis_date.isoformat(),
                'data_cutoff': analysis_date.isoformat(),
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

    def _call_deepseek_api(self, prompt: str) -> str:
        """Call DeepSeek API with the given prompt"""
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.7,
                max_tokens=2000
            )
            
            return response['choices'][0]['message']['content']
                
        except Exception as e:
            print(f"❌ Error calling DeepSeek API: {e}")
            return None
                
        except Exception as e:
            print(f"❌ Error calling DeepSeek API: {e}")
            return None

    def analyze_valuation(self, symbol: str, current_date: str = None) -> Optional[Dict]:
        """Analyze valuation for a stock symbol"""
        try:
            analysis_data = self.prepare_analysis_data(symbol, current_date)
            if not analysis_data:
                return None
            
            # Ensure metrics exist
            if 'metrics' not in analysis_data:
                analysis_data['metrics'] = {
                    'moving_averages': {'ma_20': None, 'ma_50': None, 'ma_200': None},
                    'price_changes': {'1d': None, '1w': None, '1m': None, '3m': None, '1y': None},
                    'volatility': None,
                    'volume_metrics': {'avg_10d': None, 'avg_30d': None, 'volume_change': None},
                    'technical_levels': {'support': None, 'resistance': None}
                }
            
            # Get previous analyses
            previous_analyses = self._get_previous_analyses(symbol, current_date)
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
            
            # Generate valuation analysis using DeepSeek
            prompt = self._build_valuation_prompt(analysis_data, previous_analyses_text)
            
            print(f"📊 Analyzing valuation for {symbol}...")
            response = self._call_deepseek_api(prompt)
            
            if response:
                # Parse the response
                valuation_result = self._parse_valuation_response(response, symbol, current_date)
                
                # Add calculated metrics to result
                valuation_result['metrics'] = analysis_data['metrics']
                
                # Save the analysis
                self.save_analysis(symbol, valuation_result)
                
                print(f"✅ Valuation analysis complete for {symbol}")
                return valuation_result
            else:
                print(f"❌ No response from DeepSeek for {symbol}")
                # Return basic valuation analysis instead of None to avoid retries
                return {
                    'symbol': symbol,
                    'analysis_date': datetime.now().isoformat(),
                    'target_date': current_date if current_date else datetime.now().isoformat(),
                    'recommendation': 'HOLD',
                    'confidence': 50,
                    'price_target': None,
                    'time_horizon': 'MEDIUM',
                    'risk_level': 'MEDIUM',
                    'analysis': 'API call failed - using default neutral analysis',
                    'model_used': self.model,
                    'metrics': analysis_data.get('metrics', {})
                }
                
        except Exception as e:
            print(f"❌ Error analyzing valuation for {symbol}: {e}")
            return None

    def _get_previous_analyses(self, symbol: str, current_date: str = None, days: int = 4) -> List[Dict]:
        """Get the previous N days of analyses for this symbol"""
        try:
            # Convert current_date to datetime if provided
            analysis_date = self.cutoff_date
            if current_date:
                if isinstance(current_date, str):
                    analysis_date = datetime.strptime(current_date, '%Y-%m-%d')
                else:
                    analysis_date = current_date
                    
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
                        
                        # Check if this analysis is from before the current date
                        # Use target_date if available, otherwise fall back to analysis_date
                        target_date_str = analysis.get('target_date', analysis.get('analysis_date', ''))
                        if target_date_str:
                            if isinstance(target_date_str, str) and 'T' in target_date_str:
                                file_date = datetime.fromisoformat(target_date_str.split('T')[0])
                            else:
                                file_date = datetime.fromisoformat(target_date_str[:10])
                                
                            # Skip if this analysis is from after the current date (avoid look-ahead bias)
                            if file_date >= analysis_date:
                                continue
                        
                        # Extract reasoning safely
                        reasoning = ""
                        if 'analysis' in analysis:
                            if isinstance(analysis['analysis'], str):
                                reasoning = analysis['analysis'].split('\n')[0][:100] if analysis['analysis'] else ""
                        
                        analyses.append({
                            'date': target_date_str,
                            'recommendation': analysis.get('recommendation', 'HOLD'),
                            'confidence': analysis.get('confidence', 50),
                            'price_target': analysis.get('price_target', None),
                            'reasoning': reasoning
                        })
                except Exception as e:
                    print(f"Error reading previous analysis {filepath}: {e}")
                    continue
                    
            return analyses
            
        except Exception as e:
            print(f"Error getting previous analyses: {e}")
            return []

    def _build_valuation_prompt(self, data: Dict, previous_analyses_text: str) -> str:
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
   - Price target
   - Time horizon (SHORT/MEDIUM/LONG)
   - Risk level (LOW/MEDIUM/HIGH)

Format your response as:
RECOMMENDATION: [BUY/HOLD/SELL]
CONFIDENCE: [1-100]
PRICE_TARGET: $[target price]
TIME_HORIZON: [SHORT/MEDIUM/LONG]
RISK_LEVEL: [LOW/MEDIUM/HIGH]
ANALYSIS:
[Detailed analysis]
"""
        return prompt

    def _parse_valuation_response(self, text: str, symbol: str, current_date: str = None) -> Dict:
        """Parse the response from DeepSeek"""
        try:
            # Determine the analysis date
            if current_date:
                if isinstance(current_date, str):
                    analysis_date = datetime.strptime(current_date, '%Y-%m-%d').isoformat()
                else:
                    analysis_date = current_date.isoformat()
            else:
                analysis_date = datetime.now().isoformat()
            
            # Extract recommendation
            recommendation = "HOLD"
            if "RECOMMENDATION:" in text:
                rec_line = text.split("RECOMMENDATION:")[1].split("\n")[0].strip()
                if "BUY" in rec_line:
                    recommendation = "BUY"
                elif "SELL" in rec_line:
                    recommendation = "SELL"
                elif "HOLD" in rec_line:
                    recommendation = "HOLD"
                    
                # Check for strong recommendations
                if "STRONG" in rec_line:
                    if recommendation == "BUY":
                        recommendation = "STRONG_BUY"
                    elif recommendation == "SELL":
                        recommendation = "STRONG_SELL"
            
            # Extract confidence
            confidence = 50
            if "CONFIDENCE:" in text:
                conf_line = text.split("CONFIDENCE:")[1].split("\n")[0].strip()
                try:
                    confidence = int(conf_line)
                except ValueError:
                    # Try to extract numbers
                    import re
                    numbers = re.findall(r'\d+', conf_line)
                    if numbers:
                        confidence = int(numbers[0])
            
            # Extract price target
            price_target = None
            if "PRICE_TARGET:" in text:
                pt_line = text.split("PRICE_TARGET:")[1].split("\n")[0].strip()
                try:
                    # Remove $ and any other non-numeric characters except decimal point
                    pt_line = pt_line.replace('$', '').strip()
                    price_target = float(pt_line)
                except ValueError:
                    # Try to extract numbers
                    import re
                    numbers = re.findall(r'\d+\.\d+|\d+', pt_line)
                    if numbers:
                        price_target = float(numbers[0])
            
            # Extract time horizon
            time_horizon = "MEDIUM"
            if "TIME_HORIZON:" in text:
                th_line = text.split("TIME_HORIZON:")[1].split("\n")[0].strip()
                if "SHORT" in th_line:
                    time_horizon = "SHORT"
                elif "MEDIUM" in th_line:
                    time_horizon = "MEDIUM"
                elif "LONG" in th_line:
                    time_horizon = "LONG"
            
            # Extract risk level
            risk_level = "MEDIUM"
            if "RISK_LEVEL:" in text:
                rl_line = text.split("RISK_LEVEL:")[1].split("\n")[0].strip()
                if "LOW" in rl_line:
                    risk_level = "LOW"
                elif "MEDIUM" in rl_line:
                    risk_level = "MEDIUM"
                elif "HIGH" in rl_line:
                    risk_level = "HIGH"
            
            return {
                'symbol': symbol,
                'analysis_date': datetime.now().isoformat(),  # Creation timestamp
                'target_date': analysis_date,  # The date being analyzed
                'recommendation': recommendation,
                'confidence': confidence,
                'price_target': price_target,
                'time_horizon': time_horizon,
                'risk_level': risk_level,
                'analysis': text,
                'model_used': self.model
            }
            
        except Exception as e:
            print(f"❌ Error parsing valuation response: {e}")
            return {
                'symbol': symbol,
                'analysis_date': datetime.now().isoformat(),
                'target_date': analysis_date if 'analysis_date' in locals() else datetime.now().isoformat(),
                'recommendation': 'HOLD',
                'confidence': 50,
                'price_target': None,
                'time_horizon': 'MEDIUM',
                'risk_level': 'MEDIUM',
                'analysis': text,
                'model_used': self.model
            }

    def save_analysis(self, symbol: str, analysis: Dict) -> None:
        """Save valuation analysis to file"""
        try:
            # Create output directory if it doesn't exist
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{symbol}_valuation_analysis_{timestamp}.json"
            filepath = os.path.join(self.output_dir, filename)
            
            # Save analysis to file
            with open(filepath, 'w') as f:
                json.dump(analysis, f, indent=2)
                
            print(f"💾 Valuation analysis saved: {filename}")
            
        except Exception as e:
            print(f"❌ Error saving valuation analysis: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze stock valuation")
    parser.add_argument("symbol", help="Stock symbol to analyze")
    parser.add_argument("--data-dir", default=".", help="Data directory")
    
    args = parser.parse_args()
    
    agent = ValuationAgent(data_dir=args.data_dir)
    result = agent.analyze_valuation(args.symbol)
    
    if result:
        print(f"\nRecommendation: {result['recommendation']}")
        print(f"Confidence: {result['confidence']}/100")
        if result['price_target']:
            print(f"Price Target: ${result['price_target']:.2f}")
        print(f"Time Horizon: {result['time_horizon']}")
        print(f"Risk Level: {result['risk_level']}")
