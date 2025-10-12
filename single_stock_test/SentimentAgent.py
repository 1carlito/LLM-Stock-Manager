#!/usr/bin/env python3
"""
Sentiment Analysis Agent
=======================

Analyzes news sentiment for stocks using DeepSeek API.
"""

import os
import json
import glob
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv
import openai

# Initialize DeepSeek
load_dotenv()
openai.api_key = 'sk-dd5a31380d5645c9818403b98d4d8563'  # Dedicated key for NVO sentiment analysis
if not openai.api_key:
    raise ValueError("DEEPSEEK_API_KEY environment variable not set")
openai.api_base = "https://api.deepseek.com/v1"

MODEL_NAME = "deepseek-reasoner"  # Using the V3 reasoning model (released Dec 26, 2024)

class SentimentAgent:
    def __init__(self, data_dir: str = "."):
        """Initialize the Sentiment Agent"""
        self.data_dir = data_dir
        self.output_dir = os.path.join(data_dir, "sentiment_data")
        self.news_dir = os.path.join(data_dir, "news_data")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize DeepSeek client
        self.model = MODEL_NAME

    def _load_news_data(self, symbol: str) -> Optional[Dict]:
        """Load news data for a symbol"""
        try:
            # Look for novo_news_data.json in the news_data directory
            news_file = os.path.join(self.news_dir, "novo_news_data.json")
            if os.path.exists(news_file):
                files = [news_file]
            else:
                files = []
                
            if not files:
                print(f"❌ No news data files found for {symbol}")
                return None
                
            # Get the most recent file
            latest_file = max(files, key=os.path.getmtime)
            print(f"Loading news data from {latest_file}")
            
            # Load the file
            with open(latest_file, 'r') as f:
                news_data = json.load(f)
                
            # Handle different news data formats
            if 'parsed_results' in news_data and symbol in news_data['parsed_results']:
                # Format: {'parsed_results': {'PLTR': {'news': [...]}}}
                symbol_data = news_data['parsed_results'][symbol]
                
                articles = []
                for article in symbol_data.get('news', []):
                    # Convert to standard format
                    date_str = article.get('date', '')
                    # Try to standardize date format
                    try:
                        if ',' in date_str:  # "Wed, 17 Sep 2025 18:46:05 -0400"
                            date_obj = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
                            date_str = date_obj.strftime("%Y-%m-%d")
                        # Otherwise assume it's already YYYY-MM-DD
                    except ValueError:
                        # If parsing fails, keep original
                        pass
                        
                    articles.append({
                        'date': date_str,
                        'title': article.get('title', ''),
                        'source': article.get('source_name', article.get('source', 'Unknown')),
                        'sentiment': article.get('sentiment', 'neutral'),
                        'text': article.get('text', '')[:500]  # Truncate long articles
                    })
                
                return {
                    'articles': articles,
                    'date_range': news_data.get('date_range', {
                        'start': '2024-12-27',  # Start from Dec 27
                        'end': '2025-09-18'     # Keep end date the same
                    })
                }
            elif 'news' in news_data:
                # Format: {'news': [...], 'date_range': {...}}
                articles = []
                for article in news_data.get('news', []):
                    # Convert to standard format
                    date_str = article.get('date', '')
                    # Try to standardize date format
                    try:
                        if ',' in date_str:  # "Wed, 17 Sep 2025 18:46:05 -0400"
                            date_obj = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
                            date_str = date_obj.strftime("%Y-%m-%d")
                        # Otherwise assume it's already YYYY-MM-DD
                    except ValueError:
                        # If parsing fails, keep original
                        pass
                        
                    articles.append({
                        'date': date_str,
                        'title': article.get('title', ''),
                        'source': article.get('source_name', article.get('source', 'Unknown')),
                        'sentiment': article.get('sentiment', 'neutral'),
                        'text': article.get('text', '')[:500]  # Truncate long articles
                    })
                
                return {
                    'articles': articles,
                    'date_range': news_data.get('date_range', {
                        'start': '2024-12-27',  # Default start date
                        'end': '2025-09-18'     # Default end date
                    })
                }
            elif 'articles' in news_data:
                # Already in the format we want
                return news_data
            else:
                print(f"❌ Unrecognized news data format in {latest_file}")
                return None
                
        except Exception as e:
            print(f"❌ Error loading news data: {e}")
            return None

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
                            'target_date': analysis.get('target_date', ''),
                            'analysis_date': analysis.get('analysis_date', ''),
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
                    
            # Load news data
            news_data = self._load_news_data(symbol)
            if not news_data:
                print(f"❌ No news data found for {symbol}")
                return None
                
            # Filter news by date to prevent look-ahead bias
            filtered_news = []
            for article in news_data.get('articles', []):
                article_date_str = article.get('date', '')
                if article_date_str:
                    try:
                        article_date = datetime.strptime(article_date_str, '%Y-%m-%d')
                        # Only include articles up to the current analysis date
                        if article_date <= analysis_date:
                            filtered_news.append(article)
                    except ValueError:
                        # If date parsing fails, skip this article
                        continue
                        
            if not filtered_news:
                print(f"❌ No news articles found for {symbol} before {current_date}")
                # Return empty sentiment analysis instead of None to avoid retries
                return {
                    'symbol': symbol,
                    'target_date': current_date,
                    'analysis_date': datetime.now().isoformat(),
                    'sentiment': 'NEUTRAL',
                    'confidence': 0,
                    'analysis': f'No news articles found for {symbol} before {current_date}'
                }
                
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
            
            # Group news by week for better trend analysis
            news_by_week = {}
            weekly_sentiment_counts = {}
            
            for article in filtered_news:
                article_date = datetime.strptime(article['date'], '%Y-%m-%d')
                # Get the Monday of the week
                week_start = article_date - timedelta(days=article_date.weekday())
                week_key = week_start.strftime('%Y-%m-%d')
                
                # Add article to week
                if week_key not in news_by_week:
                    news_by_week[week_key] = []
                    weekly_sentiment_counts[week_key] = {"positive": 0, "neutral": 0, "negative": 0}
                    
                news_by_week[week_key].append(article)
                
                # Count sentiment
                sentiment = article.get('sentiment', '').lower()
                if sentiment in ['positive', 'neutral', 'negative']:
                    weekly_sentiment_counts[week_key][sentiment] += 1
            
            # Build sentiment summary
            sentiment_summary = "\nSENTIMENT TRENDS BY WEEK:\n"
            sentiment_summary += "Week       | Articles | Positive | Neutral | Negative | Sentiment Score\n"
            sentiment_summary += "-----------|----------|----------|---------|----------|--------------\n"
            
            for week_key in sorted(weekly_sentiment_counts.keys(), reverse=True):
                counts = weekly_sentiment_counts[week_key]
                total = counts["positive"] + counts["neutral"] + counts["negative"]
                if total == 0:
                    score = 0
                else:
                    score = (counts["positive"] - counts["negative"]) / total
                
                sentiment_summary += f"{week_key} | {total:8d} | {counts['positive']:8d} | {counts['neutral']:7d} | {counts['negative']:8d} | {score:+.2f}\n"
            
            # Build the prompt
            prompt = f"""
            Analyze the sentiment and market impact of news for {symbol} from {start_date} to {end_date}.
            
            {sentiment_summary}
            
            Recent News Articles by Week:
            """
            
            # Add the most recent 3 weeks of news
            recent_weeks = sorted(news_by_week.keys(), reverse=True)[:3]
            for week_key in recent_weeks:
                prompt += f"\n{week_key} ({len(news_by_week[week_key])} articles):\n"
                for article in news_by_week[week_key]:
                    prompt += f"- {article['date']}: {article['title']} ({article['sentiment']})\n"
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
            
            # Generate sentiment analysis using DeepSeek
            response = self._call_deepseek_api(prompt)
            
            if response:
                # Parse the response
                sentiment_result = self._parse_sentiment_response(response)
                
                # Add metadata
                sentiment_result['symbol'] = symbol
                sentiment_result['target_date'] = analysis_date.strftime('%Y-%m-%d')
                sentiment_result['analysis_date'] = datetime.now().isoformat()
                sentiment_result['articles_analyzed'] = len(filtered_news)
                sentiment_result['date_range'] = {
                    'start': start_date,
                    'end': end_date
                }
                
                # Save the analysis
                self._save_analysis(symbol, sentiment_result)
                
                print(f"✅ Sentiment analysis saved: {self.output_dir}/{symbol}_sentiment_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                return sentiment_result
            else:
                print(f"❌ No response from DeepSeek for {symbol}")
                return None
                
        except Exception as e:
            print(f"❌ Error analyzing sentiment for {symbol}: {e}")
            return None

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
