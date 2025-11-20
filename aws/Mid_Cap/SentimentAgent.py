#!/usr/bin/env python3
"""
Sentiment Analysis Agent
=======================

Analyzes news sentiment for stocks using Gemini API.
"""

import os
import json
import glob
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv
from anthropic import Anthropic

# Load environment variables, prefer global ~/.env then local .env
home_env_path = os.path.expanduser('~/.env')
if os.path.exists(home_env_path):
    load_dotenv(dotenv_path=home_env_path)

MODEL_NAME = "claude-3-5-haiku-20241022"

class SentimentAgent:
    def __init__(
        self,
        data_dir: str = ".",
        api_key_override: str = None,
        stock_data_path: str = None
    ):
        """Initialize the Sentiment Agent
        
        Args:
            data_dir: Directory for data storage
            api_key_override: Optional API key to use instead of default from .env
            stock_data_path: Optional explicit path to stock data JSON
        """
        self.data_dir = os.path.abspath(data_dir)
        self.output_dir = os.path.join(self.data_dir, "sentiment_data")
        os.makedirs(self.output_dir, exist_ok=True)
        self.stock_data_path = os.path.abspath(stock_data_path) if stock_data_path else None
        self.news_dirs = self._resolve_news_dir()
        
        # Use override API key if provided, otherwise use dedicated sentiment key
        api_key = api_key_override or os.getenv("SENTIMENT_CLAUDE_API_KEY")
        
        if not api_key:
            raise ValueError("SENTIMENT_CLAUDE_API_KEY environment variable not set and no override provided")
        
        # Initialize Claude client
        self.client = Anthropic(api_key=api_key)
        self.model = MODEL_NAME
        
        # Load stock data for current prices
        self.stock_data = self._load_stock_data()

    def _resolve_news_dir(self) -> Dict[str, str]:
        """Locate the directories that contain news data"""
        # Check for sentiment_files/stock_news and sentiment_files/general_market_news
        candidate_stock_dirs = [
            os.path.join(self.data_dir, "sentiment_files", "stock_news"),
            os.path.join(self.data_dir, "stock_news"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "sentiment_files", "stock_news"),
        ]
        
        candidate_general_dirs = [
            os.path.join(self.data_dir, "sentiment_files", "general_market_news"),
            os.path.join(self.data_dir, "general_market_news"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "sentiment_files", "general_market_news"),
        ]
        
        stock_news_dir = None
        for path in candidate_stock_dirs:
            resolved = os.path.abspath(path)
            if os.path.isdir(resolved):
                stock_news_dir = resolved
                break
        
        general_news_dir = None
        for path in candidate_general_dirs:
            resolved = os.path.abspath(path)
            if os.path.isdir(resolved):
                general_news_dir = resolved
                break
        
        # Fallback to old news_data directory if sentiment_files not found
        if not stock_news_dir:
            candidate_dirs = [
                os.path.join(self.data_dir, "news_data"),
                os.path.join(self.data_dir, "..", "news_data"),
                os.path.join(self.data_dir, "sentiment_data", "news_data"),
            ]
            for path in candidate_dirs:
                resolved = os.path.abspath(path)
                if os.path.isdir(resolved):
                    stock_news_dir = resolved
                    break
        
        return {
            'stock_news': stock_news_dir or os.path.join(self.data_dir, "sentiment_files", "stock_news"),
            'general_market_news': general_news_dir or os.path.join(self.data_dir, "sentiment_files", "general_market_news")
        }

    def _load_stock_data(self) -> Dict:
        """Load stock data from the most relevant source - uses same data source as ValuationAgent"""
        try:
            import glob
            
            if self.stock_data_path:
                if os.path.exists(self.stock_data_path):
                    try:
                        with open(self.stock_data_path, 'r') as f:
                            data = json.load(f)
                        if isinstance(data, dict) and data:
                            print(f"📄 Loaded stock data from {self.stock_data_path}")
                            return data
                    except Exception as e:
                        print(f"⚠️ Failed to load stock data from {self.stock_data_path}: {e}")
            
            # Primary file: quant_data/mid_cap_stock_data_*.json (same as ValuationAgent)
            quant_data_dir = os.path.join(self.data_dir, "quant_data")
            primary_file = os.path.join(quant_data_dir, "mid_cap_stock_data_20250701_20251101_20251116_132209.json")
            
            # Try the primary file first
            if os.path.exists(primary_file):
                try:
                    with open(primary_file, 'r') as f:
                        data = json.load(f)
                    if isinstance(data, dict) and data:
                        print(f"📄 Loaded stock data from {primary_file}")
                        return data
                except Exception as e:
                    print(f"⚠️ Error reading {primary_file}: {e}")
            
            # Fallback: Try to find any mid_cap_stock_data file in quant_data directory
            if os.path.exists(quant_data_dir):
                mid_cap_files = glob.glob(os.path.join(quant_data_dir, "mid_cap_stock_data_*.json"))
                if mid_cap_files:
                    mid_cap_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                    try:
                        with open(mid_cap_files[0], 'r') as f:
                            data = json.load(f)
                        if isinstance(data, dict) and data:
                            print(f"📄 Loaded stock data from {mid_cap_files[0]}")
                            return data
                    except Exception as e:
                        print(f"⚠️ Error reading {mid_cap_files[0]}: {e}")
            
            # Legacy fallback: stock_data.json
            candidate_files = [
                os.path.join(self.data_dir, "stock_data.json"),
                os.path.join(self.data_dir, "stock_data.json.backup"),
            ]
            
            for stock_data_file in candidate_files:
                if os.path.exists(stock_data_file):
                    try:
                        with open(stock_data_file, 'r') as f:
                            data = json.load(f)
                        if isinstance(data, dict) and data:
                            print(f"📄 Loaded stock data from {stock_data_file}")
                            return data
                    except Exception as inner_err:
                        print(f"⚠️ Failed to load stock data from {stock_data_file}: {inner_err}")
            
            print("⚠️ No valid stock_data.json file found in expected locations. Price lookups may fail.")
            return {}
        except Exception as e:
            print(f"❌ Error loading stock data: {e}")
            return {}

    def _get_current_price(self, symbol: str, target_date: str) -> Optional[float]:
        """Get the current price for a symbol on a specific date"""
        try:
            if symbol not in self.stock_data:
                print(f"Symbol {symbol} not found in stock data dictionary")
                return None
            
            historical_prices = self.stock_data[symbol].get('historical_prices', [])
            if not historical_prices:
                print(f"No historical prices found for {symbol}")
                return None
            
            target_date_obj = datetime.strptime(target_date, '%Y-%m-%d')
            sorted_prices = sorted(historical_prices, key=lambda x: x.get('date', ''))
            valid_prices = []
            for price_data in sorted_prices:
                price_date_str = price_data.get('date', '')
                if price_date_str:
                    try:
                        price_date = datetime.strptime(price_date_str, '%Y-%m-%d')
                        if price_date <= target_date_obj:
                            valid_prices.append(price_data)
                    except ValueError:
                        continue
            if valid_prices:
                latest_price = valid_prices[-1].get('close')
                if isinstance(latest_price, (int, float)):
                    return float(latest_price)
            print(f"No valid historical price for {symbol} on or before {target_date}")
            return None
        except Exception as e:
            print(f"❌ Error getting current price for {symbol} on {target_date}: {e}")
            return None

    def _standardize_date_format(self, date_str: str) -> str:
        """Standardize various date formats to YYYY-MM-DD"""
        if not date_str:
            return ""
            
        try:
            # Already in YYYY-MM-DD format
            if len(date_str) == 10 and date_str[4] == '-' and date_str[7] == '-':
                return date_str
                
            # ISO format with time component e.g. 2025-09-18T12:30:00Z
            if len(date_str) >= 10 and date_str[4] == '-' and date_str[7] == '-':
                try:
                    date_obj = datetime.strptime(date_str[:10], "%Y-%m-%d")
                    return date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    pass
                
            # Common textual date formats
            text_formats = [
                "%a, %d %b %Y %H:%M:%S %z",
                "%a, %d %b %Y %H:%M:%S",
                "%d %b %Y",
                "%d %B %Y",
                "%b %d %Y",
                "%b %d, %Y",
                "%B %d %Y",
                "%B %d, %Y",
                "%b %d %Y %H:%M",
                "%b %d, %Y %H:%M",
                "%B %d %Y %H:%M",
                "%B %d, %Y %H:%M",
            ]
            for fmt in text_formats:
                try:
                    date_obj = datetime.strptime(date_str, fmt)
                    return date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    continue
                
            # MM/DD/YYYY format
            if '/' in date_str:
                try:
                    date_obj = datetime.strptime(date_str, "%m/%d/%Y")
                    return date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    pass
            
            # Return original if we couldn't parse
            return date_str
        except Exception as e:
            print(f"Error parsing date '{date_str}': {e}")
            return date_str
    
    def _load_news_data(self, symbol: str, current_date: str = None) -> Optional[Dict]:
        """Load news data for a symbol from stock_news and general_market_news directories"""
        try:
            all_articles = []
            
            # 1. Load stock-specific news from sentiment_files/stock_news
            stock_news_dir = self.news_dirs.get('stock_news')
            if stock_news_dir and os.path.isdir(stock_news_dir):
                # Look for symbol-specific news files (e.g., AKAM_manual_news_*.json)
                pattern = os.path.join(stock_news_dir, f"{symbol}_*.json")
                files = glob.glob(pattern)
                
                if not files:
                    # Try case-insensitive
                    pattern = os.path.join(stock_news_dir, f"{symbol.upper()}_*.json")
                    files = glob.glob(pattern)
                    if not files:
                        pattern = os.path.join(stock_news_dir, f"{symbol.lower()}_*.json")
                        files = glob.glob(pattern)
                
                if files:
                    # Sort by modification time (newest first)
                    files.sort(key=os.path.getmtime, reverse=True)
                    
                    for file_path in files:
                        try:
                            with open(file_path, 'r') as f:
                                data = json.load(f)
                            
                            # Handle different formats
                            articles = self._extract_articles_from_data(data, symbol)
                            if articles:
                                all_articles.extend(articles)
                                print(f"📰 Loaded stock-specific news from {os.path.basename(file_path)}")
                                break  # Use most recent file
                        except Exception as e:
                            print(f"⚠️ Error reading stock news file {file_path}: {e}")
                            continue
            
            # 2. Load general market news from sentiment_files/general_market_news (for ALL stocks)
            general_news_dir = self.news_dirs.get('general_market_news')
            if general_news_dir and os.path.isdir(general_news_dir):
                # Look for general_market_events.json
                general_news_file = os.path.join(general_news_dir, "general_market_events.json")
                
                if not os.path.exists(general_news_file):
                    # Try any JSON file in the directory
                    general_files = glob.glob(os.path.join(general_news_dir, "*.json"))
                    if general_files:
                        general_news_file = general_files[0]
                
                if os.path.exists(general_news_file):
                    try:
                        with open(general_news_file, 'r') as f:
                            data = json.load(f)
                        
                        # Extract general market articles
                        general_articles = self._extract_articles_from_data(data, "GENERAL_MARKET")
                        
                        # Filter general market news by current_date if provided
                        if current_date and general_articles:
                            try:
                                current_date_obj = datetime.strptime(current_date, '%Y-%m-%d')
                                filtered_general_articles = []
                                for article in general_articles:
                                    article_date_str = article.get('date', '')
                                    if article_date_str:
                                        standardized = self._standardize_date_format(article_date_str)
                                        if standardized and len(standardized) == 10:
                                            try:
                                                article_date = datetime.strptime(standardized, '%Y-%m-%d')
                                                if article_date <= current_date_obj:
                                                    article['date'] = standardized
                                                    filtered_general_articles.append(article)
                                            except ValueError:
                                                continue
                                general_articles = filtered_general_articles
                            except ValueError:
                                pass  # If date parsing fails, include all articles
                        
                        if general_articles:
                            all_articles.extend(general_articles)
                            print(f"📰 Loaded {len(general_articles)} general market news articles (filtered by date: {current_date or 'N/A'})")
                    except Exception as e:
                        print(f"⚠️ Error reading general market news file {general_news_file}: {e}")
            
            if not all_articles:
                print(f"❌ No news data found for {symbol}")
                return None
            
            # Return combined articles
            return {
                'articles': all_articles,
                'date_range': {'start': '', 'end': ''}  # Dates controlled by process_all_stocks.py
            }
            
        except Exception as e:
            print(f"❌ Error loading news data: {e}")
            return None
    
    def _extract_articles_from_data(self, data: Dict, symbol: str) -> List[Dict]:
        """Extract articles from various data formats"""
        articles = []
        
        try:
            # Handle monthly news file format (e.g., {'july_2025_ticker_news': {...}})
            if len(data) == 1 and isinstance(data, dict):
                first_key = list(data.keys())[0]
                if '_ticker_news' in first_key:
                    data = data[first_key]
            
            # Format: {'parsed_results': {'SYMBOL': {'news': [...]}}}
            if 'parsed_results' in data:
                parsed = data['parsed_results']
                if isinstance(parsed, dict):
                    if symbol in parsed:
                        symbol_data = parsed[symbol]
                        for article in symbol_data.get('news', []):
                            date_str = self._standardize_date_format(article.get('date', ''))
                            articles.append({
                                'date': date_str,
                                'title': article.get('title', ''),
                                'source': article.get('source_name', article.get('source', 'Unknown')),
                                'text': article.get('text', '')[:500]
                            })
                    elif 'GENERAL_MARKET' in parsed:
                        # For general market news
                        general_data = parsed['GENERAL_MARKET']
                        for article in general_data.get('news', []):
                            date_str = self._standardize_date_format(article.get('date', ''))
                            articles.append({
                                'date': date_str,
                                'title': article.get('title', ''),
                                'source': article.get('source_name', article.get('source', 'Unknown')),
                                'text': article.get('text', '')[:500]
                            })
            
            # Format: {'news': [...]}
            elif 'news' in data:
                for article in data.get('news', []):
                    date_str = self._standardize_date_format(article.get('date', ''))
                    articles.append({
                        'date': date_str,
                        'title': article.get('title', ''),
                        'source': article.get('source_name', article.get('source', 'Unknown')),
                        'text': article.get('text', '')[:500]
                    })
            
            # Format: {'articles': [...]}
            elif 'articles' in data:
                for article in data.get('articles', []):
                    date_str = self._standardize_date_format(article.get('date', ''))
                    articles.append({
                        'date': date_str,
                        'title': article.get('title', ''),
                        'source': article.get('source', 'Unknown'),
                        'text': article.get('text', '')[:500]
                    })
            
            # Format: {symbol: {date: [articles]}} or {symbol: [articles]}
            elif symbol in data:
                symbol_data = data[symbol]
                if isinstance(symbol_data, dict):
                    # Format: {date: [articles]}
                    for date_key, date_articles in symbol_data.items():
                        for article in date_articles if isinstance(date_articles, list) else [date_articles]:
                            articles.append({
                                'date': date_key if isinstance(date_key, str) else article.get('date', ''),
                                'title': article.get('title', ''),
                                'source': article.get('source', 'Unknown'),
                                'text': article.get('text', '')[:500]
                            })
                elif isinstance(symbol_data, list):
                    # Format: [articles]
                    for article in symbol_data:
                        articles.append({
                            'date': article.get('date', ''),
                            'title': article.get('title', ''),
                            'source': article.get('source', 'Unknown'),
                            'text': article.get('text', '')[:500]
                        })
        
        except Exception as e:
            print(f"⚠️ Error extracting articles from data: {e}")
        
        return articles

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
            pattern = os.path.join(self.output_dir, f"{symbol}_sentiment_analysis_*.json")
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
                        analysis_date_str = analysis.get('date', '')
                        if analysis_date_str:
                            try:
                                file_date = datetime.strptime(analysis_date_str, '%Y-%m-%d')
                                # Skip if this analysis is from after the current date (avoid look-ahead bias)
                                if file_date >= analysis_date:
                                    continue
                            except ValueError:
                                # If date parsing fails, skip this check
                                pass
                        
                        # Handle different formats of analysis data
                        analysis_data = {}
                        if 'analysis' in analysis and isinstance(analysis['analysis'], dict):
                            analysis_data = analysis['analysis']
                        else:
                            # If analysis is a string or other type, create a dict with default values
                            analysis_data = {
                                'sentiment': 'NEUTRAL',
                                'confidence': 50,
                                'analysis': str(analysis.get('analysis', ''))
                            }
                        
                        # Extract reasoning from either the analysis text or a specific field
                        reasoning = ""
                        if isinstance(analysis_data.get('analysis'), str):
                            reasoning = analysis_data['analysis'].split('\n')[0][:100] if analysis_data['analysis'] else ""
                        
                        analyses.append({
                            'date': analysis.get('date', ''),
                            'sentiment': analysis_data.get('sentiment', 'NEUTRAL'),
                            'confidence': analysis_data.get('confidence', 50),
                            'reasoning': reasoning
                        })
                except Exception as e:
                    print(f"Error reading previous analysis {filepath}: {e}")
                    continue
                    
            return analyses
            
        except Exception as e:
            print(f"Error getting previous analyses: {e}")
            return []

    def analyze_sentiment(self, symbol: str, current_date: str = None) -> Optional[Dict]:
        """Analyze sentiment for a stock symbol"""
        try:
            # Convert current_date to datetime if provided
            analysis_date = datetime.now()
            if current_date:
                if isinstance(current_date, str):
                    analysis_date = datetime.strptime(current_date, '%Y-%m-%d')
                else:
                    analysis_date = current_date
                    
            # Load news data (includes stock-specific and general market news, both date-filtered)
            current_date_str = current_date if current_date else None
            news_data = self._load_news_data(symbol, current_date=current_date_str)
            if not news_data:
                print(f"❌ No news data found for {symbol}")
                return None
                
            # Filter all news by date to prevent look-ahead bias (additional safety check)
            filtered_news = []
            for article in news_data.get('articles', []):
                article_date_str = article.get('date', '')
                standardized_date = self._standardize_date_format(article_date_str)
                if standardized_date:
                    try:
                        article_date = datetime.strptime(standardized_date, '%Y-%m-%d')
                        if article_date <= analysis_date:
                            article['date'] = standardized_date
                            filtered_news.append(article)
                    except ValueError:
                        print(f"⚠️ Invalid standardized date: {standardized_date} for article: {article.get('title', '')}")
                else:
                    print(f"⚠️ Could not parse date format: {article_date_str} for article: {article.get('title', '')}")
                        
            if not filtered_news:
                print(f"❌ No news articles found for {symbol} before {current_date or 'current date'}")
                return None
                
            # Update news data with filtered articles
            news_data['articles'] = filtered_news
            
            # Get date range
            start_date = news_data.get('date_range', {}).get('start', '')
            end_date = current_date if current_date else news_data.get('date_range', {}).get('end', '')
            
            # Get previous analyses
            previous_analyses = self._get_previous_analyses(symbol, current_date)
            previous_analyses_text = ""
            
            if previous_analyses:
                previous_analyses_text = "\nPREVIOUS SENTIMENT ANALYSES:\n"
                previous_analyses_text += "Date       | Sentiment | Confidence | Summary\n"
                previous_analyses_text += "-----------|-----------|------------|--------\n"
                
                for analysis in previous_analyses:
                    date = analysis.get('date', '')[:10]  # Just get YYYY-MM-DD part
                    sentiment = analysis.get('sentiment', 'NEUTRAL')
                    confidence = analysis.get('confidence', 50)
                    reasoning = analysis.get('reasoning', '')[:50] + "..." if analysis.get('reasoning', '') else "N/A"
                    
                    previous_analyses_text += f"{date} | {sentiment:9s} | {confidence:10d} | {reasoning}\n"
            
            # Process news data
            print(f"Filtered news for {symbol}: {len(filtered_news)} articles between {start_date} and {end_date}")
            
            # Get current stock price for the analysis date
            current_price = None
            try:
                current_price = self._get_current_price(symbol, current_date)
                if current_price is not None:
                    print(f"Current price for {symbol} on {current_date}: ${current_price:.2f}")
                else:
                    print(f"❌ Could not find current price for {symbol} on {current_date}")
            except Exception as e:
                print(f"❌ Error getting current price for {symbol}: {e}")
                current_price = None
            
            # Group news by week for better trend analysis
            news_by_week = {}
            
            for article in filtered_news:
                article_date = datetime.strptime(article['date'], '%Y-%m-%d')
                # Get the Monday of the week
                week_start = article_date - timedelta(days=article_date.weekday())
                week_key = week_start.strftime('%Y-%m-%d')
                
                # Add article to week
                if week_key not in news_by_week:
                    news_by_week[week_key] = []
                    
                news_by_week[week_key].append(article)
            
            # Build the prompt
            price_info = f"Current stock price: ${current_price:.2f}" if current_price else "Current stock price: Not available"
            prompt = f"""
            Analyze the sentiment and market impact of news for {symbol} from {start_date} to {end_date}.
            {price_info}
            
            Recent News Articles by Week:
            """
            
            # Add the most recent 3 weeks of news
            recent_weeks = sorted(news_by_week.keys(), reverse=True)[:3]
            for week_key in recent_weeks:
                prompt += f"\n{week_key} ({len(news_by_week[week_key])} articles):\n"
                for article in news_by_week[week_key]:
                    prompt += f"- {article['date']}: {article['title']}\n"
                    if article['text']:
                        prompt += f"  Summary: {article['text'][:200]}...\n"
            
            # Add previous analyses
            prompt += f"\n{previous_analyses_text}\n"
            
            prompt += f"""
            Based on the news articles above, provide a comprehensive sentiment analysis:
            
            1. Overall sentiment (POSITIVE, NEUTRAL, or NEGATIVE)
            2. Confidence score (0-100)
            3. Key themes and topics driving sentiment
            4. Impact on stock price outlook
            5. Notable changes in sentiment over time
            
            Format your response as:
            SENTIMENT: [POSITIVE/NEUTRAL/NEGATIVE]
            CONFIDENCE: [0-100]
            
            [Detailed analysis of news sentiment, key themes, and potential market impact]
            
            - IMPORTANT: Consider how your analysis compares to previous sentiment assessments
            - IMPORTANT: Focus on objective analysis of news content, not personal opinion
            - IMPORTANT: Consider both the quantity and quality of news in your assessment
            """
            
            # Generate sentiment analysis using Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}]
            )
            
            if response and response.content and len(response.content) > 0:
                # Parse the response
                sentiment_result = self._parse_sentiment_response(response.content[0].text)
                
                # Add metadata
                sentiment_result['symbol'] = symbol
                sentiment_result['date'] = analysis_date.strftime('%Y-%m-%d')
                sentiment_result['articles_analyzed'] = len(filtered_news)
                sentiment_result['current_price'] = current_price
                sentiment_result['date_range'] = {
                    'start': start_date,
                    'end': end_date
                }
                
                # Save the analysis
                self._save_analysis(symbol, sentiment_result)
                
                print(f"✅ Sentiment analysis saved: {self.output_dir}/{symbol}_sentiment_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                return sentiment_result
            else:
                print(f"❌ No response from Claude for {symbol}")
                return None
                
        except Exception as e:
            print(f"❌ Error analyzing sentiment for {symbol}: {e}")
            return None

    def _parse_analysis_response(self, response_text: str) -> Dict:
        """Parse the sentiment analysis response"""
        try:
            # Extract key information
            sentiment = "NEUTRAL"
            confidence = 50
            volatility = "MEDIUM"
            catalyst_potential = "MEDIUM"
            analysis = response_text
            
            # Parse sentiment
            if "SENTIMENT:" in response_text:
                sent_match = response_text.split("SENTIMENT:")[1].split("\n")[0].strip()
                if sent_match in ["BULLISH", "NEUTRAL", "BEARISH"]:
                    sentiment = sent_match
            
            # Parse confidence
            if "CONFIDENCE:" in response_text:
                conf_match = response_text.split("CONFIDENCE:")[1].split("\n")[0].strip()
                try:
                    confidence = int(conf_match)
                except ValueError:
                    pass
            
            # Parse volatility
            if "VOLATILITY:" in response_text:
                vol_match = response_text.split("VOLATILITY:")[1].split("\n")[0].strip()
                if vol_match in ["LOW", "MEDIUM", "HIGH"]:
                    volatility = vol_match
            
            # Parse catalyst potential
            if "CATALYST_POTENTIAL:" in response_text:
                cat_match = response_text.split("CATALYST_POTENTIAL:")[1].split("\n")[0].strip()
                if cat_match in ["LOW", "MEDIUM", "HIGH"]:
                    catalyst_potential = cat_match
            
            return {
                'sentiment': sentiment,
                'confidence': confidence,
                'volatility': volatility,
                'catalyst_potential': catalyst_potential,
                'analysis': analysis
            }
            
        except Exception as e:
            print(f"❌ Error parsing sentiment analysis: {e}")
            return {
                'sentiment': 'NEUTRAL',
                'confidence': 50,
                'volatility': 'MEDIUM',
                'catalyst_potential': 'MEDIUM',
                'analysis': response_text,
                'parse_error': str(e)
            }

    def _parse_sentiment_response(self, text: str) -> Dict:
        """Parse the sentiment analysis response from Gemini"""
        try:
            # Extract sentiment
            sentiment = "NEUTRAL"
            if "SENTIMENT:" in text:
                sentiment_line = text.split("SENTIMENT:")[1].split("\n")[0].strip()
                if "POSITIVE" in sentiment_line:
                    sentiment = "POSITIVE"
                elif "NEGATIVE" in sentiment_line:
                    sentiment = "NEGATIVE"
                elif "NEUTRAL" in sentiment_line:
                    sentiment = "NEUTRAL"
                elif "BULLISH" in sentiment_line:
                    sentiment = "POSITIVE"
                elif "BEARISH" in sentiment_line:
                    sentiment = "NEGATIVE"
            
            # Extract confidence
            confidence = 50
            if "CONFIDENCE:" in text:
                confidence_line = text.split("CONFIDENCE:")[1].split("\n")[0].strip()
                try:
                    confidence = int(confidence_line)
                except ValueError:
                    # If we can't parse as int, try to extract numbers
                    import re
                    numbers = re.findall(r'\d+', confidence_line)
                    if numbers:
                        confidence = int(numbers[0])
            
            # Return parsed result
            return {
                'sentiment': sentiment,
                'confidence': confidence,
                'analysis': text
            }
            
        except Exception as e:
            print(f"❌ Error parsing sentiment response: {e}")
            return {
                'sentiment': "NEUTRAL",
                'confidence': 50,
                'analysis': text
            }

    def _save_analysis(self, symbol: str, analysis_result: Dict) -> None:
        """Save sentiment analysis to file"""
        try:
            # Create output directory if it doesn't exist
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{symbol}_sentiment_analysis_{timestamp}.json"
            filepath = os.path.join(self.output_dir, filename)
            
            # Save analysis to file
            with open(filepath, 'w') as f:
                json.dump(analysis_result, f, indent=2)
                
        except Exception as e:
            print(f"❌ Error saving sentiment analysis for {symbol}: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run sentiment analysis for a stock")
    parser.add_argument("--symbol", type=str, help="Stock symbol to analyze")
    parser.add_argument("--data-dir", type=str, default=".", help="Base directory for data files")
    args = parser.parse_args()
    
    agent = SentimentAgent(data_dir=args.data_dir)
    result = agent.analyze_sentiment(args.symbol, datetime.now().strftime("%Y-%m-%d"))
    if result:
        print("✅ Sentiment analysis test successful")
    else:
        print("❌ Sentiment analysis test failed")
