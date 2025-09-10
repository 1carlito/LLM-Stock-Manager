#!/usr/bin/env python3
"""
Simple CLI Runner for LLM News Searcher
=======================================

Easy-to-use interface for the LLM-powered news searcher.
"""

import os
import sys
from llm_news_searcher import LLMNewsSearcher

def main():
    print("🚀 LLM News Searcher for 50 Stocks")
    print("=" * 50)
    print("📊 Using GPT-3.5 Turbo with 4 focused searches")
    
    # Check if OpenAI API key is set
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        print("❌ OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key:")
        print("export OPENAI_API_KEY='your_key_here'")
        return
    
    print("✅ OpenAI API key found")
    
    # Show chunk breakdown
    print("\n📋 Stock Distribution (4 chunks):")
    print("Chunk 1: Tech (9) + Healthcare (3) = 12 stocks")
    print("Chunk 2: Healthcare (7) + Financial (5) = 12 stocks") 
    print("Chunk 3: Financial (5) + Consumer (7) = 12 stocks")
    print("Chunk 4: Consumer (3) + Energy (10) = 13 stocks")
    print("Total: 49 stocks (MSFT, PLTR, NVO, BP already covered)")
    
    # Confirm before starting
    print("\n⚠️  This will make 4 API calls to GPT-3.5 Turbo")
    print("💰 Estimated cost: $0.02-0.08 (depending on response length)")
    
    confirm = input("\nProceed with news search? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("Search cancelled.")
        return
    
    try:
        # Initialize searcher
        searcher = LLMNewsSearcher(openai_api_key)
        
        # Start searching
        print("\n🚀 Starting LLM news search...")
        results = searcher.search_all_chunks()
        
        print(f"\n🎉 Search completed successfully!")
        print(f"📊 Total chunks processed: {len(results)}")
        
        # Show results summary
        total_stocks = sum(len(chunk['stocks']) for chunk in results.values() if 'stocks' in chunk)
        print(f"📈 Total stocks covered: {total_stocks}")
        
        # Show any errors
        errors = [chunk for chunk in results.values() if 'error' in chunk]
        if errors:
            print(f"⚠️  {len(errors)} chunks had errors:")
            for error_chunk in errors:
                print(f"   - {error_chunk['chunk_name']}: {error_chunk['error']}")
        
        print(f"\n📁 Results saved in: llm_news_results/")
        
    except KeyboardInterrupt:
        print("\n⚠️  Search interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during search: {e}")
        print("Please check your OpenAI API key and internet connection")

if __name__ == "__main__":
    main() 