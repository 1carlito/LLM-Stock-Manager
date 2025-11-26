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
from dotenv import load_dotenv
import numpy as np
import pandas as pd
import glob

# Load environment variables from .env in the same directory as this script
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(dotenv_path=env_path)

# DeepSeek API configuration
MODEL_NAME = 'deepseek-ai/DeepSeek-V3.1'
CHUTES_API_URL = os.getenv("CHUTES_API_URL", "https://llm.chutes.ai/v1/chat/completions")

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
        
        # Initialize DeepSeek API - use override if provided, otherwise use DEEPSEEK_API_KEY_1
        self.api_key = api_key_override or os.getenv("DEEPSEEK_API_KEY_1")
        
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY_1 environment variable not set and no override provided")
        
        self.model = MODEL_NAME
        print(f"✅ DeepSeek ValuationAgent initialized with {self.model}")
    
    def _find_stock_data(self, symbol: str) -> Dict:
        """Find the latest stock data for a symbol"""
        try:
            # Note: Removed AVAV restriction - now supports all symbols in data file
            
            # Primary file: quant_data/mid_cap_stock_data_*.json
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
            
            # Fallback: Try other patterns
            patterns = [
                os.path.join(self.data_dir, f"stock_data_*.json"),
                os.path.join(self.data_dir, f"**/stock_data_*.json"),
                os.path.join(self.data_dir, f"**/{symbol.lower()}_*.json"),
                os.path.join(self.data_dir, f"**/{symbol.upper()}_*.json")
            ]
            
            all_files = []
            for pattern in patterns:
                all_files.extend(glob.glob(pattern, recursive=True))
                
            if all_files:
                # Sort by modification time (newest first)
                all_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                
                # Try each file until we find data for our symbol
                for file_path in all_files:
                    try:
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                        
                        # Check if symbol exists in this file
                        if isinstance(data, dict):
                            if symbol in data:
                                print(f"✅ Found {symbol} in {file_path}")
                                return data[symbol]
                            elif len(data) == 1:
                                # Single stock file
                                return list(data.values())[0]
                    except Exception:
                        continue
            
            raise ValueError(f"Could not find stock data for {symbol} in any file. Checked primary file: {primary_file}")
            
        except Exception as e:
            raise ValueError(f"Error finding stock data: {str(e)}")
    
    def _calculate_metrics(self, price_data: List[Dict]) -> Dict:
        """Calculate key valuation metrics including RSI and MACD"""
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
            
            # Calculate RSI (14-period)
            rsi_14 = self._calculate_rsi(prices, 14) if len(prices) >= 15 else None
            
            # Calculate MACD (12, 26, 9)
            macd_data = self._calculate_macd(prices) if len(prices) >= 27 else None
            
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
                },
                'technical_indicators': {
                    'rsi_14': rsi_14,
                    'macd': macd_data
                }
            }
            
        except Exception as e:
            print(f"❌ Error calculating metrics: {e}")
            return {}
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate the Relative Strength Index (RSI)"""
        try:
            if len(prices) <= period:
                return None
                
            # Convert to pandas Series for easier calculation
            price_series = pd.Series(prices)
            
            # Calculate daily price changes
            delta = price_series.diff().dropna()
            
            # Separate gains and losses
            gains = delta.copy()
            losses = delta.copy()
            gains[gains < 0] = 0
            losses[losses > 0] = 0
            losses = abs(losses)
            
            # Calculate average gains and losses
            avg_gain = gains.rolling(window=period).mean().dropna()
            avg_loss = losses.rolling(window=period).mean().dropna()
            
            if len(avg_gain) == 0 or len(avg_loss) == 0:
                return None
                
            # Calculate RS and RSI
            rs = avg_gain.iloc[-1] / avg_loss.iloc[-1] if avg_loss.iloc[-1] != 0 else 100
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception as e:
            print(f"❌ Error calculating RSI: {e}")
            return None
    
    def _calculate_macd(self, prices: List[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Dict:
        """Calculate the Moving Average Convergence Divergence (MACD)"""
        try:
            if len(prices) <= slow_period + signal_period:
                return None
                
            # Convert to pandas Series for easier calculation
            price_series = pd.Series(prices)
            
            # Calculate EMAs
            ema_fast = price_series.ewm(span=fast_period, adjust=False).mean()
            ema_slow = price_series.ewm(span=slow_period, adjust=False).mean()
            
            # Calculate MACD line
            macd_line = ema_fast - ema_slow
            
            # Calculate signal line
            signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
            
            # Calculate histogram
            histogram = macd_line - signal_line
            
            return {
                'macd_line': macd_line.iloc[-1],
                'signal_line': signal_line.iloc[-1],
                'histogram': histogram.iloc[-1],
                'is_bullish': macd_line.iloc[-1] > signal_line.iloc[-1],
                'is_above_zero': macd_line.iloc[-1] > 0
            }
            
        except Exception as e:
            print(f"❌ Error calculating MACD: {e}")
            return None
    
    def _get_previous_analyses(self, symbol: str, current_date: str = None, max_analyses: int = 3) -> List[Dict]:
        """Get previous analyses for this symbol"""
        try:
            # Get previous technical analysis files
            files = glob.glob(os.path.join(self.output_dir, f"{symbol}_technical_analysis_*.json"))
            
            if not files:
                return []
                
            # Parse dates from filenames
            previous_analyses = []
            target_date = datetime.strptime(current_date, "%Y-%m-%d") if current_date else datetime.now()
            
            for file_path in files:
                try:
                    # Extract date from filename
                    file_parts = os.path.basename(file_path).split('_')
                    if len(file_parts) < 4:
                        continue
                        
                    date_str = file_parts[-1].replace('.json', '')
                    file_date = datetime.strptime(date_str, "%Y%m%d_%H%M%S")
                    
                    # Only include analyses before current date
                    if file_date.date() < target_date.date():
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                            previous_analyses.append(data)
                except Exception:
                    continue
            
            # Sort by date
            previous_analyses.sort(key=lambda x: x.get('analysis_date', '2000-01-01'))
            
            # Return most recent N
            return previous_analyses[-max_analyses:] if previous_analyses else []
            
        except Exception:
            return []

    def analyze_valuation(self, symbol: str, current_date: str = None) -> Dict:
        """
        Analyze stock valuation for the given symbol
        
        Args:
            symbol: Stock ticker symbol
            current_date: Current analysis date (YYYY-MM-DD format)
            
        Returns:
            Dictionary with valuation analysis
        """
        print(f"\n📊 Analyzing valuation for {symbol}...")
        
        try:
            # Normalize date
            if current_date:
                target_date = datetime.strptime(current_date, "%Y-%m-%d") 
            else:
                target_date = datetime.now()
                current_date = target_date.strftime("%Y-%m-%d")
            
            # Get stock data
            try:
                stock_data = self._find_stock_data(symbol)
            except ValueError as e:
                print(f"❌ {str(e)}")
                return {
                    'symbol': symbol,
                    'analysis_date': current_date,
                    'recommendation': 'HOLD',
                    'confidence': 0.5,
                    'summary': 'No data available',
                    'error': str(e)
                }
            
            # Extract relevant data for valuation
            # Handle both old format (with profile/metrics/ratios) and new format (direct fields)
            price_data = stock_data.get('price_data', {})
            profile = stock_data.get('profile', {})
            metrics = stock_data.get('metrics', {})
            ratios = stock_data.get('ratios', {})
            historical_prices = stock_data.get('historical_prices', [])
            
            # Get company name - check new format first (company_name), then old format (profile.companyName)
            company_name = stock_data.get('company_name') or profile.get('companyName') or symbol
            
            # If profile is empty but we have direct fields, create a minimal profile
            if not profile and stock_data.get('sector'):
                profile = {
                    'sector': stock_data.get('sector', 'Unknown'),
                    'industry': stock_data.get('industry', 'Unknown'),
                    'companyName': company_name
                }
            
            # Extract current price from historical prices for the target date
            current_price = 0
            if historical_prices and current_date:
                # Find price for the target date or closest previous date
                target_date_obj = datetime.strptime(current_date, "%Y-%m-%d")
                sorted_prices = sorted(historical_prices, key=lambda x: x.get('date', ''), reverse=True)
                
                for price_entry in sorted_prices:
                    price_date_str = price_entry.get('date', '')
                    if price_date_str:
                        try:
                            price_date = datetime.strptime(price_date_str, '%Y-%m-%d')
                            if price_date <= target_date_obj:
                                current_price = price_entry.get('close', 0)
                                if current_price:
                                    break
                        except ValueError:
                            continue
                
                # If no exact date found, use most recent price
                if not current_price and sorted_prices:
                    current_price = sorted_prices[0].get('close', 0)
            
            # Create prompt
            prompt = self._create_valuation_prompt(symbol, company_name, current_price, stock_data, current_date)
            
            # Get previous analyses
            previous_analyses = self._get_previous_analyses(symbol, current_date)
            if previous_analyses:
                prompt += "\n\nPREVIOUS ANALYSES:\n"
                prompt += json.dumps([{'date': a.get('analysis_date'), 
                                      'recommendation': a.get('recommendation'), 
                                      'target_price': a.get('target_price'),
                                      'confidence': a.get('confidence')} 
                                     for a in previous_analyses], indent=2)
                prompt += "\n\nConsider these previous analyses for consistency, but update based on new data."
            
            # Call LLM API
            print(f"Calling Anthropic API for {symbol} valuation analysis...")
            analysis_result = self._call_llm_api(prompt)
            
            # Parse the response
            result = self._parse_valuation_response(analysis_result, symbol, current_date, current_price)
            return result
            
        except Exception as e:
            print(f"❌ Error in valuation analysis: {e}")
            return {
                'symbol': symbol,
                'analysis_date': current_date,
                'recommendation': 'HOLD',
                'confidence': 0.5,
                'summary': f'Error: {str(e)}',
                'model_used': self.model,
                'error': str(e)
            }

    def _call_llm_api(self, prompt: str) -> str:
        """Call DeepSeek API via Chutes with the given prompt"""
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a professional stock analyst specializing in valuation analysis."},
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

    def _create_valuation_prompt(self, symbol: str, company_name: str, current_price: float, stock_data: Dict, current_date: str = None) -> str:
        """Create a prompt for valuation analysis"""
        # Extract basic metrics - handle both nested and flat data structures
        price_data = stock_data.get('price_data', {})
        profile = stock_data.get('profile', {})
        metrics = stock_data.get('metrics', {})
        ratios = stock_data.get('ratios', {})
        
        # Fallback to direct fields if nested structures are empty (new data format)
        if not profile:
            profile = {
                'sector': stock_data.get('sector', 'Unknown'),
                'industry': stock_data.get('industry', 'Unknown'),
                'companyName': stock_data.get('company_name', company_name)
            }
        
        if not metrics:
            metrics = {}  # ValuationAgent focuses on technical indicators only
        
        sector = profile.get('sector', 'Unknown')
        industry = profile.get('industry', 'Unknown')
        
        # Note: P/E, EPS, and Market Cap are fundamental metrics handled by FundamentalAgent
        # ValuationAgent focuses on technical indicators only
        
        # Calculate technical indicators if historical prices are available
        technical_indicators = {}
        historical_prices = stock_data.get('historical_prices', [])
        
        if historical_prices and current_date:
            # Filter historical prices to prevent look-ahead bias
            target_date_obj = datetime.strptime(current_date, "%Y-%m-%d")
            filtered_prices = []
            
            for price_entry in historical_prices:
                price_date_str = price_entry.get('date', '')
                if price_date_str:
                    try:
                        price_date = datetime.strptime(price_date_str, '%Y-%m-%d')
                        if price_date <= target_date_obj:
                            filtered_prices.append(price_entry)
                    except ValueError:
                        continue
            
            # Sort filtered prices by date (oldest to newest) for correct calculations
            filtered_prices.sort(key=lambda x: x.get('date', ''))
            
            # Calculate metrics using only historical data available on current_date
            calculated_metrics = self._calculate_metrics(filtered_prices)
            
            # Extract technical indicators
            ma_data = calculated_metrics.get('moving_averages', {})
            price_changes = calculated_metrics.get('price_changes', {})
            tech_indicators = calculated_metrics.get('technical_indicators', {})
            tech_levels = calculated_metrics.get('technical_levels', {})
            volume_metrics = calculated_metrics.get('volume_metrics', {})
            
            # Extract VWAP from current day's price entry
            current_vwap = None
            current_volume = None
            for price_entry in filtered_prices:
                price_date_str = price_entry.get('date', '')
                if price_date_str == current_date:
                    current_vwap = price_entry.get('vwap')
                    current_volume = price_entry.get('volume')
                    break
            
            # If exact date not found, use most recent entry
            if current_vwap is None and filtered_prices:
                latest_entry = filtered_prices[-1]
                current_vwap = latest_entry.get('vwap')
                current_volume = latest_entry.get('volume')
            
            # Format for prompt
            rsi_14 = tech_indicators.get('rsi_14')
            rsi_status = "N/A"
            if rsi_14 is not None:
                if rsi_14 > 70:
                    rsi_status = f"{rsi_14:.2f} (Overbought)"
                elif rsi_14 < 30:
                    rsi_status = f"{rsi_14:.2f} (Oversold)"
                else:
                    rsi_status = f"{rsi_14:.2f} (Neutral)"
            
            macd_data = tech_indicators.get('macd', {})
            macd_status = "N/A"
            if macd_data:
                macd_line = macd_data.get('macd_line')
                signal_line = macd_data.get('signal_line')
                histogram = macd_data.get('histogram')
                is_bullish = macd_data.get('is_bullish')
                
                if is_bullish:
                    macd_status = f"Bullish (MACD: {macd_line:.4f}, Signal: {signal_line:.4f}, Hist: {histogram:.4f})"
                else:
                    macd_status = f"Bearish (MACD: {macd_line:.4f}, Signal: {signal_line:.4f}, Hist: {histogram:.4f})"
            
            # Format volume metrics
            avg_vol_10d = volume_metrics.get('avg_10d')
            avg_vol_30d = volume_metrics.get('avg_30d')
            vol_change = volume_metrics.get('volume_change')
            
            volume_status = "N/A"
            if current_volume and avg_vol_30d:
                vol_ratio = current_volume / avg_vol_30d if avg_vol_30d > 0 else 1.0
                if vol_ratio > 1.5:
                    volume_status = f"High ({current_volume:,.0f} vs {avg_vol_30d:,.0f} avg, {vol_ratio:.1f}x)"
                elif vol_ratio < 0.5:
                    volume_status = f"Low ({current_volume:,.0f} vs {avg_vol_30d:,.0f} avg, {vol_ratio:.1f}x)"
                else:
                    volume_status = f"Normal ({current_volume:,.0f} vs {avg_vol_30d:,.0f} avg, {vol_ratio:.1f}x)"
            
            # Format VWAP comparison
            vwap_status = "N/A"
            if current_vwap and current_price:
                vwap_diff = ((current_price - current_vwap) / current_vwap * 100) if current_vwap > 0 else 0
                if vwap_diff > 1:
                    vwap_status = f"${current_vwap:.2f} (Price {vwap_diff:+.2f}% above VWAP, bullish)"
                elif vwap_diff < -1:
                    vwap_status = f"${current_vwap:.2f} (Price {vwap_diff:+.2f}% below VWAP, bearish)"
                else:
                    vwap_status = f"${current_vwap:.2f} (Price {vwap_diff:+.2f}% vs VWAP, neutral)"
            
            technical_indicators = {
                'RSI (14)': rsi_status,
                'MACD': macd_status,
                'MA 20': f"${ma_data.get('ma_20'):.2f}" if ma_data.get('ma_20') else "N/A",
                'MA 50': f"${ma_data.get('ma_50'):.2f}" if ma_data.get('ma_50') else "N/A",
                'MA 200': f"${ma_data.get('ma_200'):.2f}" if ma_data.get('ma_200') else "N/A",
                'Support': f"${tech_levels.get('support'):.2f}" if tech_levels.get('support') else "N/A",
                'Resistance': f"${tech_levels.get('resistance'):.2f}" if tech_levels.get('resistance') else "N/A",
                'Price Change (1d)': f"{price_changes.get('1d')*100:.2f}%" if price_changes.get('1d') else "N/A",
                'Price Change (1w)': f"{price_changes.get('1w')*100:.2f}%" if price_changes.get('1w') else "N/A",
                'Price Change (1m)': f"{price_changes.get('1m')*100:.2f}%" if price_changes.get('1m') else "N/A",
                'Volume': volume_status,
                'Volume Change': f"{vol_change*100:.2f}%" if vol_change is not None else "N/A",
                'Avg Volume (10d)': f"{avg_vol_10d:,.0f}" if avg_vol_10d else "N/A",
                'Avg Volume (30d)': f"{avg_vol_30d:,.0f}" if avg_vol_30d else "N/A",
                'VWAP': vwap_status
            }
        
        # Create the prompt
        analysis_date = current_date if current_date else datetime.now().strftime('%Y-%m-%d')
        prompt = f"""
You are a professional stock analyst specializing in valuation analysis for {symbol} ({company_name}) on {analysis_date}.

COMPANY INFORMATION:
- Symbol: {symbol}
- Name: {company_name}
- Sector: {sector}
- Industry: {industry}
- Current Price: ${current_price}

TECHNICAL INDICATORS:
- RSI (14): {technical_indicators.get('RSI (14)', 'N/A')}
- MACD: {technical_indicators.get('MACD', 'N/A')}
- 20-day MA: {technical_indicators.get('MA 20', 'N/A')}
- 50-day MA: {technical_indicators.get('MA 50', 'N/A')}
- 200-day MA: {technical_indicators.get('MA 200', 'N/A')}
- Support Level: {technical_indicators.get('Support', 'N/A')}
- Resistance Level: {technical_indicators.get('Resistance', 'N/A')}
- Price Change (1d): {technical_indicators.get('Price Change (1d)', 'N/A')}
- Price Change (1w): {technical_indicators.get('Price Change (1w)', 'N/A')}
- Price Change (1m): {technical_indicators.get('Price Change (1m)', 'N/A')}

VOLUME METRICS:
- Current Volume: {technical_indicators.get('Volume', 'N/A')}
- Volume Change vs 30d Avg: {technical_indicators.get('Volume Change', 'N/A')}
- Average Volume (10d): {technical_indicators.get('Avg Volume (10d)', 'N/A')}
- Average Volume (30d): {technical_indicators.get('Avg Volume (30d)', 'N/A')}

VWAP (Volume Weighted Average Price):
- {technical_indicators.get('VWAP', 'N/A')}

NOTE: This is a technical analysis focused on price action, momentum, and volume patterns. Fundamental metrics (P/E, EPS, Market Cap) are handled by the FundamentalAgent and are not included in this analysis.

TASK: Perform a comprehensive technical analysis of {symbol}. Analyze the stock's price action, technical indicators, volume patterns, and momentum.

Consider:
1. Recent price action and momentum
2. Key technical indicators (RSI, MACD, moving averages)
3. Volume patterns and VWAP analysis
4. Support and resistance levels
5. Price targets based on technical analysis (bull, base, bear scenarios)

Based on your analysis, provide:
1. A RECOMMENDATION: BUY, HOLD, or SELL
2. A CONFIDENCE level from 0.5 (low) to 1.0 (high)
3. A TARGET PRICE (12-month)
4. A STOP LOSS price if applicable
5. Key support and resistance levels

FORMAT YOUR RESPONSE AS:
RECOMMENDATION: [BUY/HOLD/SELL]
CONFIDENCE: [0.0-1.0]
TARGET_PRICE: [price]
STOP_LOSS: [price or N/A]
SUMMARY: [One-sentence summary]

TECHNICAL ANALYSIS:
[Detailed technical analysis including price action, momentum, indicators, and volume patterns]

KEY LEVELS:
- Support: [level 1], [level 2]
- Resistance: [level 1], [level 2]

RISK ASSESSMENT:
[Assessment of risk factors]

CONCLUSION:
[Concluding paragraph with final recommendation justification]
"""
        return prompt

    def _parse_valuation_response(self, response: str, symbol: str, current_date: str, current_price: float) -> Dict:
        """Parse the LLM response into a structured valuation analysis"""
        import re
        
        try:
            result = {
                'symbol': symbol,
                'analysis_date': current_date,
                'current_price': current_price,
                'raw_response': response,
                'model_used': self.model
            }
            
            # Extract recommendation
            recommendation_match = re.search(r'RECOMMENDATION:\s*(BUY|HOLD|SELL)', response, re.IGNORECASE)
            result['recommendation'] = recommendation_match.group(1).upper() if recommendation_match else 'HOLD'
            
            # Extract confidence
            confidence_match = re.search(r'CONFIDENCE:\s*(0\.\d+|1\.0)', response)
            result['confidence'] = float(confidence_match.group(1)) if confidence_match else 0.5
            
            # Extract target price
            target_match = re.search(r'TARGET_PRICE:\s*\$?(\d+\.?\d*)', response)
            result['target_price'] = float(target_match.group(1)) if target_match else current_price
            
            # Extract stop loss
            stop_loss_match = re.search(r'STOP_LOSS:\s*\$?(\d+\.?\d*)', response)
            result['stop_loss'] = float(stop_loss_match.group(1)) if stop_loss_match and stop_loss_match.group(1).lower() != 'n/a' else None
            
            # Extract summary
            summary_match = re.search(r'SUMMARY:\s*(.+?)(?:\n|$)', response)
            result['summary'] = summary_match.group(1).strip() if summary_match else 'No summary provided'
            
            # Extract support levels
            support_match = re.search(r'Support:\s*(.+?)(?:\n|$)', response)
            if support_match:
                support_text = support_match.group(1)
                support_levels = re.findall(r'\$?(\d+\.?\d*)', support_text)
                result['support_levels'] = [float(level) for level in support_levels] if support_levels else []
            else:
                result['support_levels'] = []
            
            # Extract resistance levels
            resistance_match = re.search(r'Resistance:\s*(.+?)(?:\n|$)', response)
            if resistance_match:
                resistance_text = resistance_match.group(1)
                resistance_levels = re.findall(r'\$?(\d+\.?\d*)', resistance_text)
                result['resistance_levels'] = [float(level) for level in resistance_levels] if resistance_levels else []
            else:
                result['resistance_levels'] = []
            
            # Extract conclusion
            conclusion_match = re.search(r'CONCLUSION:(.*?)(?:$)', response, re.DOTALL)
            result['conclusion'] = conclusion_match.group(1).strip() if conclusion_match else 'No conclusion provided'
            
            # Save to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{symbol}_technical_analysis_{timestamp}.json"
            filepath = os.path.join(self.output_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(result, f, indent=2)
            
            print(f"✅ Valuation analysis saved to {filepath}")
            
            return result
            
        except Exception as e:
            print(f"❌ Error parsing valuation response: {e}")
            return {
                'symbol': symbol,
                'analysis_date': current_date,
                'recommendation': 'HOLD',
                'confidence': 0.5,
                'summary': f'Error parsing analysis: {str(e)}',
                'model_used': self.model
            }