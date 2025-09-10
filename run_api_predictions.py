#!/usr/bin/env python3
"""
Run API-Based LLM Stock Predictions
===================================

This script uses comprehensive stock data from the FMP API and runs LLM-based
stock price predictions using multiple providers.
"""

import os
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
import argparse

from earnings_api_client import StockData
from llm_predictor import deploy_prediction, PredictionResult
from llm_results import PredictionMetrics
from prompt_engineering import generate_earnings_prompt

def load_stock_data(filename: str) -> Dict[str, StockData]:
    """Load comprehensive stock data from a JSON file"""
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
        
        stock_data = {}
        for symbol, item in data.items():
            stock_data[symbol] = StockData(
                symbol=item['symbol'],
                company_name=item['company_name'],
                sector=item['sector'],
                current_price=item['current_price'],
                volume=item['volume'],
                change_percent=item['change_percent'],
                latest_quarter=item['latest_quarter'],
                revenue=item['revenue'],
                revenue_growth=item['revenue_growth'],
                eps=item['eps'],
                eps_growth=item['eps_growth'],
                operating_profit=item['operating_profit'],
                operating_margin=item['operating_margin'],
                price_history=item['price_history'],
                commitment_data=item['commitment_data'],
                analyst_ratings=item['analyst_ratings'],
                news_data=item['news_data'],
                historical_quarters=item['historical_quarters']
            )
        
        return stock_data
    
    except Exception as e:
        print(f"Error loading stock data: {e}")
        return {}

def generate_enhanced_prompt(stock_data: StockData) -> str:
    """Generate an enhanced prompt using comprehensive stock data"""
    # Use the built-in formatter from StockData class
    base_prompt = stock_data.to_prompt_format()
    
    # Add additional context for prediction
    prompt = f"""
{base_prompt}

PREDICTION TASK:
Based on the above data for {stock_data.symbol}, please predict:

1. The stock price movement over the next 1 day (tomorrow)
2. The stock price movement over the next 5 days
3. The stock price movement over the next 30 days

For each prediction, provide:
- Target price
- Percentage change from current price
- Confidence level (0-100%)
- Key factors influencing your prediction

Format your response as follows:
CURRENT PRICE: ${stock_data.current_price:.2f}

1-DAY PREDICTION:
TARGET PRICE: $XXX.XX
CHANGE: +/-X.X%
CONFIDENCE: XX%

5-DAY PREDICTION:
TARGET PRICE: $XXX.XX
CHANGE: +/-X.X%
CONFIDENCE: XX%

30-DAY PREDICTION:
TARGET PRICE: $XXX.XX
CHANGE: +/-X.X%
CONFIDENCE: XX%

REASONING:
[Your detailed analysis explaining the predictions and key factors considered]
"""
    return prompt

def run_api_predictions(symbols: List[str], providers: List[str] = None, 
                       input_file: str = "comprehensive_stock_data.json", 
                       output_dir: str = "llm_results"):
    """
    Run LLM predictions using comprehensive stock data
    
    Args:
        symbols: List of stock symbols to analyze
        providers: List of LLM providers to use (default: all available)
        input_file: Input file with comprehensive stock data
        output_dir: Directory to save prediction results
    """
    if providers is None:
        providers = ['anthropic', 'openai', 'deepseek', 'gemini']
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Load stock data
    print(f"📂 Loading stock data from {input_file}")
    stock_data = load_stock_data(input_file)
    
    if not stock_data:
        print("❌ No stock data available, exiting...")
        return
    
    # Filter symbols if specified
    if symbols:
        filtered_data = {s: data for s, data in stock_data.items() if s in symbols}
        if not filtered_data:
            print(f"❌ None of the specified symbols {symbols} found in stock data")
            return
        stock_data = filtered_data
    
    print(f"✅ Loaded stock data for {len(stock_data)} stocks")
    
    # Group by sector
    sectors = {}
    for symbol, data in stock_data.items():
        sector = data.sector
        if sector not in sectors:
            sectors[sector] = []
        sectors[sector].append(symbol)
    
    # Process each stock
    total_predictions = 0
    successful_predictions = 0
    
    for sector, sector_symbols in sectors.items():
        print(f"\n🔍 Processing {sector} sector ({len(sector_symbols)} stocks)...")
        
        for symbol in sector_symbols:
            data = stock_data[symbol]
            print(f"\n📊 Processing {symbol}: {data.company_name}")
            print(f"  Current Price: ${data.current_price:.2f} ({data.change_percent:+.2f}%)")
            
            # Generate enhanced prompt
            prompt_text = generate_enhanced_prompt(data)
            
            # Run predictions with each provider
            symbol_results = []
            for provider in providers:
                print(f"🤖 Running {provider} prediction for {symbol}...")
                total_predictions += 1
                
                try:
                    prediction, error = deploy_prediction(provider, symbol, prompt_text)
                    
                    if prediction and not error:
                        symbol_results.append(prediction)
                        successful_predictions += 1
                        print(f"✅ {provider} prediction completed for {symbol}")
                        
                        # Save individual prediction
                        save_prediction(prediction, f"{output_dir}/{symbol}_{provider}_{datetime.now().strftime('%Y%m%d')}.json")
                    else:
                        print(f"❌ {provider} prediction failed: {error}")
                
                except Exception as e:
                    print(f"❌ Error with {provider} prediction: {e}")
                
                # Rate limiting between providers
                time.sleep(1)
            
            # Save combined results
            if symbol_results:
                save_combined_predictions(symbol_results, f"{output_dir}/{symbol}_combined_{datetime.now().strftime('%Y%m%d')}.json")
                print(f"📊 Completed {len(symbol_results)} predictions for {symbol}")
            else:
                print(f"⚠️ No successful predictions for {symbol}")
    
    # Print summary
    print(f"\n📊 Prediction Summary:")
    print(f"Total stocks processed: {len(stock_data)}")
    print(f"Total predictions attempted: {total_predictions}")
    print(f"Successful predictions: {successful_predictions}")
    print(f"Success rate: {successful_predictions/total_predictions*100:.1f}%")
    print(f"Results saved to: {output_dir}")

def save_prediction(prediction: PredictionResult, filename: str):
    """Save a single prediction to a file"""
    # Create a proper PredictionMetrics object
    metrics = PredictionMetrics(
        revenue=getattr(prediction.predicted_metrics, 'revenue', 0.0),
        eps=getattr(prediction.predicted_metrics, 'eps', 0.0),
        operating_margin=getattr(prediction.predicted_metrics, 'operating_margin', 0.0),
        net_income=0.0  # Default value since we don't have this
    )
    
    data = {
        'stock_ticker': prediction.stock_ticker,
        'prediction_date': prediction.prediction_date,
        'target_quarter': prediction.target_quarter,
        'llm_provider': prediction.llm_provider,
        'model_used': prediction.model_used,
        'model_training_cutoff': prediction.model_training_cutoff,
        'predicted_metrics': {
            'revenue': metrics.revenue,
            'eps': metrics.eps,
            'operating_margin': metrics.operating_margin,
            'net_income': metrics.net_income
        },
        'pre_earnings_price': prediction.pre_earnings_price,
        'price_target_1d': prediction.price_target_1d,
        'price_target_5d': prediction.price_target_5d,
        'confidence_level_1d': prediction.confidence_level_1d,
        'confidence_level_5d': prediction.confidence_level_5d,
        'reasoning': prediction.reasoning
    }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def save_combined_predictions(predictions: List[PredictionResult], filename: str):
    """Save combined predictions to a file"""
    data = {
        'stock_ticker': predictions[0].stock_ticker,
        'prediction_date': datetime.now().strftime('%Y-%m-%d'),
        'predictions': []
    }
    
    for pred in predictions:
        data['predictions'].append({
            'llm_provider': pred.llm_provider,
            'model_used': pred.model_used,
            'price_target_1d': pred.price_target_1d,
            'price_target_5d': pred.price_target_5d,
            'confidence_level_1d': pred.confidence_level_1d,
            'reasoning': pred.reasoning
        })
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Run API-based LLM stock predictions")
    parser.add_argument("--symbols", nargs="+", default=None,
                        help="Stock symbols to analyze (default: all stocks in input file)")
    parser.add_argument("--providers", nargs="+", default=["anthropic"],
                        help="LLM providers to use (default: anthropic)")
    parser.add_argument("--input", default="comprehensive_stock_data.json",
                        help="Input file with stock data (default: comprehensive_stock_data.json)")
    parser.add_argument("--output-dir", default="llm_results",
                        help="Directory to save prediction results (default: llm_results)")
    parser.add_argument("--sector", help="Filter by sector (Technology, Healthcare, Financial, Consumer, Energy)")
    parser.add_argument("--limit", type=int, default=None, 
                        help="Limit the number of stocks to process")
    
    args = parser.parse_args()
    
    print("🚀 Starting API-based LLM stock predictions")
    print(f"🤖 Providers: {args.providers}")
    print(f"📂 Input file: {args.input}")
    print(f"💾 Output directory: {args.output_dir}")
    
    # Load stock data to get symbols
    if args.sector or args.limit:
        stock_data = load_stock_data(args.input)
        
        if args.sector:
            sector_symbols = [s for s, data in stock_data.items() if data.sector == args.sector]
            print(f"🔍 Filtering by {args.sector} sector: {len(sector_symbols)} stocks")
            symbols = sector_symbols
        else:
            symbols = list(stock_data.keys())
        
        if args.limit and args.limit < len(symbols):
            symbols = symbols[:args.limit]
            print(f"🔢 Limiting to {args.limit} stocks")
    else:
        symbols = args.symbols
    
    run_api_predictions(
        symbols=symbols,
        providers=args.providers,
        input_file=args.input,
        output_dir=args.output_dir
    )
    
    print("\n✅ Predictions completed!")

if __name__ == "__main__":
    main() 