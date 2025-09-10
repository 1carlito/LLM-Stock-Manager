#!/usr/bin/env python3
"""
LLM News Searcher for 50 Stocks
Uses GPT-3.5 Turbo to search for news and press releases for multiple stocks
Divides stocks into 4 chunks to optimize API calls and reduce prompt size
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any
from openai import OpenAI

class LLMNewsSearcher:
    def __init__(self, api_key: str):
        """Initialize the LLM news searcher"""
        self.client = OpenAI(api_key=api_key)
        self.results_dir = "llm_news_results"
        self.chunks_dir = os.path.join(self.results_dir, "chunks")
        self.summaries_dir = os.path.join(self.results_dir, "summaries")
        
        # Create directories if they don't exist
        os.makedirs(self.results_dir, exist_ok=True)
        os.makedirs(self.chunks_dir, exist_ok=True)
        os.makedirs(self.summaries_dir, exist_ok=True)
        
        # Define stock chunks (49 new stocks, excluding MSFT, PLTR, NVO, BP)
        self.stock_chunks = {
            "Chunk 1 - Tech & Healthcare": [
                "AAPL", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX", "ADBE", "CRM",
                "JNJ", "PFE", "UNH"
            ],
            "Chunk 2 - Healthcare & Financial": [
                "ABBV", "TMO", "ABT", "LLY", "DHR", "BMY", "AMGN",
                "JPM", "BAC", "WFC", "GS", "MS"
            ],
            "Chunk 3 - Financial & Consumer": [
                "C", "BLK", "AXP", "CB", "SPGI",
                "PG", "KO", "PEP", "WMT", "HD", "MCD", "DIS"
            ],  
            "Chunk 4 - Consumer & Energy": [
                "NKE", "SBUX", "TGT",
                "XOM", "CVX", "COP", "EOG", "SLB", "PSX", "MPC", "VLO", "KMI", "OKE"
            ]
        }
        
        # Base prompt template
        self.base_prompt_template = """
You are a financial news researcher. For each stock symbol provided, find the most relevant and impactful news headlines, press releases, analyst actions, and market impact from the past 6 months (February 2025 - July 2025).

For each stock, provide
1. NEWS: major news headlines with dates and sources
2. PRESS RELEASES: 2-3 significant company press releases with dates
3. ANALYST ACTIONS: 1-2 key analyst upgrades/downgrades or price target changes
4. MARKET IMPACT: Brief summary of how these events affected the stock price

Format each stock section as:
**STOCK: SYMBOL**
NEWS:
- Date: Headline - Source
PRESS RELEASES:
- Date: Headline - Source
ANALYST ACTIONS:
- Date: Action - Source
MARKET IMPACT:
- Summary of price impact

Please be thorough but concise. Focus on the most impactful news that would be relevant for stock price predictions.
"""
    
    def search_chunk(self, chunk_name: str, stocks: List[str]) -> Dict[str, Any]:
        """Search for news for a specific chunk of stocks"""
        stocks_str = ", ".join(stocks)
        prompt = f"{self.base_prompt_template}\n\nStock symbols to research: {stocks_str}"
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a financial news researcher. Provide accurate, relevant financial news information."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4000,
                temperature=0.3
            )
            
            response_text = response.choices[0].message.content
            
            # Parse the response
            parsed_results = self.parse_llm_response(response_text, stocks)
            
            # Save chunk results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            chunk_filename = f"{chunk_name.replace(' ', '_')}_{timestamp}.json"
            chunk_path = os.path.join(self.chunks_dir, chunk_filename)
            
            chunk_data = {
                "chunk_name": chunk_name,
                "stocks": stocks,
                "search_date": datetime.now().isoformat(),
                "llm_model": "gpt-3.5-turbo",
                "raw_response": response_text,
                "parsed_results": parsed_results
            }
            
            with open(chunk_path, 'w') as f:
                json.dump(chunk_data, f, indent=2)
            
            print(f"✅ {chunk_name} completed - {len(parsed_results)} stocks processed")
            
            return chunk_data
            
        except Exception as e:
            print(f"❌ Error searching {chunk_name}: {str(e)}")
            return {
                "chunk_name": chunk_name,
                "stocks": stocks,
                "error": str(e),
                "parsed_results": {}
            }
    
    def parse_llm_response(self, response_text: str, stocks: List[str]) -> Dict[str, Any]:
        """Parse the LLM response into structured data"""
        parsed_results = {}
        
        # Split response by stock sections - handle both **STOCK: SYMBOL** and STOCK: SYMBOL formats
        sections = response_text.split('**STOCK:')
        if len(sections) == 1:  # Try alternative format
            sections = response_text.split('STOCK:')
        
        for section in sections[1:]:  # Skip first empty section
            lines = section.strip().split('\n')
            if not lines:
                continue
            
            # Extract stock symbol - handle both **SYMBOL** and SYMBOL formats
            stock_symbol = lines[0].strip()
            # Remove asterisks and clean up
            stock_symbol = stock_symbol.replace('*', '').strip()
            
            if stock_symbol not in stocks:
                continue
            
            stock_data = {
                'news': [],
                'press_releases': [],
                'analyst_actions': [],
                'market_impact': '',
                'raw_section': section.strip()
            }
            
            current_section = None
            
            for line in lines[1:]:
                line = line.strip()
                if not line:
                    continue
                
                # Detect section headers
                if line.startswith('NEWS:'):
                    current_section = 'news'
                elif line.startswith('PRESS RELEASES:'):
                    current_section = 'press_releases'
                elif line.startswith('ANALYST ACTIONS:'):
                    current_section = 'analyst_actions'
                elif line.startswith('MARKET IMPACT:'):
                    current_section = 'market_impact'
                elif line.startswith('-') and current_section:
                    # Parse bullet point
                    if current_section in ['news', 'press_releases', 'analyst_actions']:
                        item = self.parse_bullet_point(line)
                        if item:
                            stock_data[current_section].append(item)
                    elif current_section == 'market_impact':
                        stock_data['market_impact'] = line.replace('-', '').strip()
            
            parsed_results[stock_symbol] = stock_data
        
        return parsed_results
    
    def parse_bullet_point(self, line: str) -> Dict[str, str]:
        """Parse a bullet point line into structured data"""
        try:
            # Remove the bullet point
            content = line.replace('-', '').strip()
            
            # Try to extract date and other components
            # Handle different separator patterns: " - ", ":", and just spaces
            if ' - ' in content:
                parts = content.split(' - ')
            elif ':' in content and len(content.split(':')) >= 2:
                # Handle format like "Date: Headline - Source"
                colon_parts = content.split(':', 1)
                if ' - ' in colon_parts[1]:
                    parts = [colon_parts[0]] + colon_parts[1].split(' - ')
                else:
                    parts = colon_parts
            else:
                parts = [content]
            
            if len(parts) >= 2:
                date_part = parts[0].strip()
                headline_part = parts[1].strip()
                source_part = parts[2].strip() if len(parts) > 2 else ""
                
                # Clean up date part (remove common prefixes)
                date_part = date_part.replace('Date:', '').strip()
                
                return {
                    'date': date_part,
                    'headline': headline_part,
                    'source': source_part,
                    'raw_text': content
                }
            else:
                return {
                    'date': '',
                    'headline': content,
                    'source': '',
                    'raw_text': content
                }
        except Exception as e:
            return {
                'date': '',
                'headline': line,
                'source': '',
                'raw_text': line
            }
    
    def search_all_chunks(self) -> Dict[str, Any]:
        """Search for news across all chunks"""
        print("🚀 Starting LLM news search for all 50 stocks...")
        print("📊 Using GPT-3.5 Turbo with 4 focused searches")
        print()
        
        all_results = {}
        
        for chunk_name, stocks in self.stock_chunks.items():
            print("=" * 60)
            print(f"🔍 Searching {chunk_name}...")
            
            chunk_result = self.search_chunk(chunk_name, stocks)
            all_results[chunk_name] = chunk_result
            
            # Wait between chunks to avoid rate limiting
            if chunk_name != list(self.stock_chunks.keys())[-1]:  # Not the last chunk
                print("⏳ Waiting 10 seconds between chunks...")
                time.sleep(10)
                print()
        
        # Generate summary and save comprehensive results
        self.generate_summary(all_results)
        self.save_comprehensive_results(all_results)
        
        return all_results
    
    def generate_summary(self, all_results: Dict[str, Any]) -> None:
        """Generate a summary of all search results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_filename = f"search_summary_{timestamp}.json"
        summary_path = os.path.join(self.summaries_dir, summary_filename)
        
        summary = {
            "search_date": datetime.now().isoformat(),
            "total_chunks": len(all_results),
            "total_stocks": sum(len(chunk.get("stocks", [])) for chunk in all_results.values()),
            "chunk_summaries": {}
        }
        
        for chunk_name, chunk_data in all_results.items():
            stocks = chunk_data.get("stocks", [])
            parsed_count = len(chunk_data.get("parsed_results", {}))
            error = chunk_data.get("error", None)
            
            summary["chunk_summaries"][chunk_name] = {
                "stocks_count": len(stocks),
                "parsed_count": parsed_count,
                "success_rate": f"{(parsed_count/len(stocks)*100):.1f}%" if stocks else "0%",
                "error": error
            }
        
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"📊 Summary: {summary_path}")
    
    def save_comprehensive_results(self, all_results: Dict[str, Any]) -> None:
        """Save comprehensive results to a single file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        comprehensive_filename = f"comprehensive_results_{timestamp}.json"
        comprehensive_path = os.path.join(self.results_dir, comprehensive_filename)
        
        with open(comprehensive_path, 'w') as f:
            json.dump(all_results, f, indent=2)
        
        print(f"📁 Comprehensive: {comprehensive_path}")
    
    def get_stock_summary(self, symbol: str) -> Dict[str, Any]:
        """Get parsed news data for a specific stock from saved chunk files"""
        for filename in os.listdir(self.chunks_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.chunks_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        chunk_data = json.load(f)
                    
                    parsed_results = chunk_data.get("parsed_results", {})
                    if symbol in parsed_results:
                        return parsed_results[symbol]
                except Exception as e:
                    continue
        
        return {}

if __name__ == "__main__":
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key:")
        print("export OPENAI_API_KEY='your_key_here'")
        exit(1)
    
    # Create searcher and run search
    searcher = LLMNewsSearcher(api_key)
    searcher.search_all_chunks() 