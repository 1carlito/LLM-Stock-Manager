"""
Batch Stock Price Predictor for 50 Stocks
=========================================

This script automates stock price predictions for 50 stocks using comprehensive
FMP API data and multiple LLM providers. It uses pre-fetched comprehensive data
for better reliability and performance.
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

from earnings_api_client import StockData
from llm_predictor import deploy_prediction

@dataclass
class StockConfig:
    """Configuration for a single stock"""
    symbol: str
    name: str
    sector: str
    fmp_data_enabled: bool = True
    llm_providers: List[str] = None
    custom_prompt_template: str = None
    
    def __post_init__(self):
        if self.llm_providers is None:
            self.llm_providers = ['openai', 'gemini']

@dataclass
class PricePrediction:
    """Price prediction result"""
    symbol: str
    prediction_date: str
    llm_provider: str
    model_used: str
    current_price: float
    predicted_price_1d: float
    predicted_price_5d: float
    predicted_price_30d: float
    confidence_level: float
    reasoning: str
    fmp_data_used: bool
    timestamp: str

class BatchStockPredictor:
    """Automated batch processor for 50 stocks using comprehensive FMP data"""
    
    def __init__(self, comprehensive_data_file: str = "comprehensive_stock_data.json", max_concurrent: int = 3):
        self.comprehensive_data_file = comprehensive_data_file
        self.max_concurrent = max_concurrent
        self.results_dir = "batch_predictions"
        self.comprehensive_data = self.load_comprehensive_data()
        self.stocks_config = self.load_stocks_config()
        
        # Create results directory
        os.makedirs(self.results_dir, exist_ok=True)
        os.makedirs(f"{self.results_dir}/individual", exist_ok=True)
        os.makedirs(f"{self.results_dir}/summary", exist_ok=True)
    
    def load_comprehensive_data(self) -> Dict[str, StockData]:
        """Load comprehensive stock data from file"""
        try:
            with open(self.comprehensive_data_file, 'r') as f:
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
            
            print(f"✅ Loaded comprehensive data for {len(stock_data)} stocks")
            return stock_data
        
        except Exception as e:
            print(f"❌ Error loading comprehensive data: {e}")
            return {}
    
    def load_stocks_config(self) -> List[StockConfig]:
        """Load stock configuration from comprehensive data"""
        if not self.comprehensive_data:
            print("❌ No comprehensive data available")
            return []
        
        stocks_config = []
        for symbol, stock_data in self.comprehensive_data.items():
            config = StockConfig(
                symbol=symbol,
                name=stock_data.company_name,
                sector=stock_data.sector,
                fmp_data_enabled=True,
                llm_providers=['deepseek', 'anthropic', 'gemini', 'openai']
            )
            stocks_config.append(config)
        
        return stocks_config
    
    def create_price_prediction_prompt(self, stock_data: StockData) -> str:
        """Create a comprehensive price prediction prompt using StockData"""
        # Use the built-in formatter from StockData class
        base_prompt = stock_data.to_prompt_format()
        
        # Add prediction-specific instructions
        prediction_prompt = f"""
{base_prompt}

PREDICTION TASK:
Based on the comprehensive data above for {stock_data.symbol}, please predict:

1. The stock price movement over the next 1 day (tomorrow)
2. The stock price movement over the next 5 days
3. The stock price movement over the next 30 days

For each prediction, provide:
- Target price
- Percentage change from current price
- Confidence level (0-100%)
- Key factors influencing your prediction

ANALYSIS FACTORS TO CONSIDER:
- Current price momentum and technical indicators
- Trading volume and market interest
- Analyst ratings and sentiment
- Historical earnings performance and trends
- Sector performance and market conditions
- News sentiment and market events
- Financial health and fundamental metrics

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
        return prediction_prompt
    
    async def process_single_stock(self, stock_config: StockConfig) -> List[PricePrediction]:
        """Process a single stock with all LLM providers"""
        print(f"🔄 Processing {stock_config.symbol}...")
        
        predictions = []
        
        # Get comprehensive stock data
        if stock_config.symbol not in self.comprehensive_data:
            print(f"❌ No comprehensive data available for {stock_config.symbol}")
            return predictions
        
        stock_data = self.comprehensive_data[stock_config.symbol]
        
        # Create comprehensive prompt
        prompt = self.create_price_prediction_prompt(stock_data)
        
        # Process with each LLM provider
        for provider in stock_config.llm_providers:
            try:
                print(f"  📊 Running {provider} prediction for {stock_config.symbol}...")
                
                # Use ThreadPoolExecutor for synchronous LLM calls
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(deploy_prediction, provider, stock_config.symbol, prompt)
                    result, error = future.result(timeout=180)  # 3 minute timeout
                
                if result and not error:
                    # Parse the prediction result
                    prediction = self.parse_prediction_result(result, stock_config.symbol, provider, stock_data)
                    if prediction:
                        predictions.append(prediction)
                        print(f"  ✅ {provider} prediction completed for {stock_config.symbol}")
                    else:
                        print(f"  ⚠️  Failed to parse {provider} prediction for {stock_config.symbol}")
                else:
                    print(f"  ❌ {provider} prediction failed for {stock_config.symbol}: {error}")
                
                time.sleep(2)  # Rate limiting between providers
                
            except Exception as e:
                print(f"  ❌ Error with {provider} for {stock_config.symbol}: {e}")
                continue
        
        return predictions
    
    def parse_prediction_result(self, result, symbol: str, provider: str, stock_data: StockData) -> Optional[PricePrediction]:
        """Parse LLM prediction result into structured format"""
        try:
            # Extract current price
            current_price = getattr(result, 'pre_earnings_price', stock_data.current_price)
            
            # Extract predicted prices
            predicted_price_1d = getattr(result, 'price_target_1d', 0.0)
            predicted_price_5d = getattr(result, 'price_target_5d', 0.0)
            predicted_price_30d = 0.0  # Will need to parse from reasoning if available
            
            # Extract confidence and reasoning
            confidence_level = getattr(result, 'confidence_level_1d', 50.0)
            reasoning = getattr(result, 'reasoning', 'No reasoning provided')
            
            return PricePrediction(
                symbol=symbol,
                prediction_date=datetime.now().strftime('%Y-%m-%d'),
                llm_provider=provider,
                model_used=getattr(result, 'model_used', 'Unknown'),
                current_price=current_price,
                predicted_price_1d=predicted_price_1d,
                predicted_price_5d=predicted_price_5d,
                predicted_price_30d=predicted_price_30d,
                confidence_level=confidence_level,
                reasoning=reasoning,
                fmp_data_used=True,  # Always true since we're using comprehensive data
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            print(f"Error parsing prediction result: {e}")
            return None
    
    async def run_batch_predictions(self, symbols: List[str] = None, providers: List[str] = None) -> Dict[str, List[PricePrediction]]:
        """Run batch predictions for specified stocks or all configured stocks"""
        
        if symbols:
            stocks_to_process = [s for s in self.stocks_config if s.symbol in symbols]
        else:
            stocks_to_process = self.stocks_config
        
        # Filter providers if specified
        if providers:
            for stock in stocks_to_process:
                stock.llm_providers = [p for p in stock.llm_providers if p in providers]
        
        print(f"🚀 Starting batch predictions for {len(stocks_to_process)} stocks...")
        print(f"📊 Max concurrent processing: {self.max_concurrent}")
        print(f"🤖 LLM providers: {providers if providers else 'all available'}")
        
        all_predictions = {}
        
        # Process stocks in batches to control concurrency
        for i in range(0, len(stocks_to_process), self.max_concurrent):
            batch = stocks_to_process[i:i + self.max_concurrent]
            
            print(f"\n📦 Processing batch {i//self.max_concurrent + 1}/{(len(stocks_to_process) + self.max_concurrent - 1)//self.max_concurrent}")
            
            # Process batch concurrently
            tasks = [self.process_single_stock(stock) for stock in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect results
            for stock, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    print(f"❌ Error processing {stock.symbol}: {result}")
                    all_predictions[stock.symbol] = []
                else:
                    all_predictions[stock.symbol] = result
                    print(f"✅ Completed {stock.symbol}: {len(result)} predictions")
            
            # Save batch results
            self.save_batch_results(batch, all_predictions)
            
            # Rate limiting between batches
            if i + self.max_concurrent < len(stocks_to_process):
                print("⏳ Waiting between batches...")
                await asyncio.sleep(10)
        
        # Generate summary report
        self.generate_summary_report(all_predictions)
        
        return all_predictions
    
    def save_batch_results(self, batch: List[StockConfig], all_predictions: Dict[str, List[PricePrediction]]):
        """Save results for a batch of stocks"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for stock in batch:
            symbol = stock.symbol
            if symbol in all_predictions and all_predictions[symbol]:
                # Save individual stock results
                individual_file = f"{self.results_dir}/individual/{symbol}_{timestamp}.json"
                predictions_data = []
                
                for pred in all_predictions[symbol]:
                    # Convert prediction to serializable dict
                    pred_dict = {
                        'symbol': pred.symbol,
                        'prediction_date': pred.prediction_date,
                        'llm_provider': pred.llm_provider,
                        'model_used': str(pred.model_used),  # Convert model to string
                        'current_price': float(pred.current_price),
                        'predicted_price_1d': float(pred.predicted_price_1d),
                        'predicted_price_5d': float(pred.predicted_price_5d),
                        'predicted_price_30d': float(pred.predicted_price_30d),
                        'confidence_level': float(pred.confidence_level),
                        'reasoning': str(pred.reasoning),
                        'fmp_data_used': bool(pred.fmp_data_used),
                        'timestamp': pred.timestamp
                    }
                    predictions_data.append(pred_dict)
                
                with open(individual_file, 'w') as f:
                    json.dump(predictions_data, f, indent=2)
                
                print(f"💾 Saved individual results for {symbol}")
    
    def generate_summary_report(self, all_predictions: Dict[str, List[PricePrediction]]):
        """Generate a comprehensive summary report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        summary_file = f"{self.results_dir}/summary/batch_summary_{timestamp}.json"
        
        summary = {
            'batch_date': datetime.now().isoformat(),
            'total_stocks': len(all_predictions),
            'total_predictions': sum(len(preds) for preds in all_predictions.values()),
            'stocks_processed': list(all_predictions.keys()),
            'predictions_by_provider': {},
            'stocks_with_fmp_data': [],
            'stocks_without_fmp_data': [],
            'detailed_results': {}
        }
        
        # Analyze predictions by provider
        for symbol, predictions in all_predictions.items():
            summary['detailed_results'][symbol] = {
                'total_predictions': len(predictions),
                'providers_used': [p.llm_provider for p in predictions],
                'fmp_data_used': any(p.fmp_data_used for p in predictions),
                'average_confidence': sum(p.confidence_level for p in predictions) / len(predictions) if predictions else 0
            }
            
            # Track FMP data usage
            if any(p.fmp_data_used for p in predictions):
                summary['stocks_with_fmp_data'].append(symbol)
            else:
                summary['stocks_without_fmp_data'].append(symbol)
            
            # Count by provider
            for pred in predictions:
                provider = pred.llm_provider
                if provider not in summary['predictions_by_provider']:
                    summary['predictions_by_provider'][provider] = 0
                summary['predictions_by_provider'][provider] += 1
        
        # Save summary
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Generate CSV summary
        csv_file = f"{self.results_dir}/summary/batch_summary_{timestamp}.csv"
        self.generate_csv_summary(all_predictions, csv_file)
        
        print(f"\n📊 Summary Report Generated:")
        print(f"   📁 JSON: {summary_file}")
        print(f"   📊 CSV: {csv_file}")
        print(f"   📈 Total Stocks: {summary['total_stocks']}")
        print(f"   🔢 Total Predictions: {summary['total_predictions']}")
        print(f"   📊 Predictions by Provider: {summary['predictions_by_provider']}")
    
    def generate_csv_summary(self, all_predictions: Dict[str, List[PricePrediction]], csv_file: str):
        """Generate CSV summary of all predictions"""
        rows = []
        
        for symbol, predictions in all_predictions.items():
            for pred in predictions:
                rows.append({
                    'Symbol': pred.symbol,
                    'Prediction_Date': pred.prediction_date,
                    'LLM_Provider': pred.llm_provider,
                    'Model_Used': pred.model_used,
                    'Current_Price': pred.current_price,
                    'Predicted_Price_1D': pred.predicted_price_1d,
                    'Predicted_Price_5D': pred.predicted_price_5d,
                    'Predicted_Price_30D': pred.predicted_price_30d,
                    'Confidence_Level': pred.confidence_level,
                    'FMP_Data_Used': pred.fmp_data_used,
                    'Timestamp': pred.timestamp
                })
        
        if rows:
            df = pd.DataFrame(rows)
            df.to_csv(csv_file, index=False)
            print(f"📊 CSV summary saved: {csv_file}")

def main():
    """Main function to run batch predictions"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run batch stock predictions using comprehensive FMP data")
    parser.add_argument("--input", default="comprehensive_stock_data.json",
                        help="Input file with comprehensive stock data (default: comprehensive_stock_data.json)")
    parser.add_argument("--symbols", nargs="+", default=None,
                        help="Stock symbols to analyze (default: all stocks in input file)")
    parser.add_argument("--providers", nargs="+", default=['deepseek', 'anthropic'],
                        help="LLM providers to use (default: deepseek, anthropic)")
    parser.add_argument("--max-concurrent", type=int, default=3,
                        help="Maximum concurrent stock processing (default: 3)")
    parser.add_argument("--sector", help="Filter by sector (Technology, Healthcare, Financial, Consumer, Energy)")
    parser.add_argument("--limit", type=int, default=None, 
                        help="Limit the number of stocks to process")
    
    args = parser.parse_args()
    
    print("🚀 Starting comprehensive batch stock predictions")
    print(f"📂 Input file: {args.input}")
    print(f"🤖 LLM providers: {args.providers}")
    print(f"⚡ Max concurrent: {args.max_concurrent}")
    
    # Initialize batch predictor
    predictor = BatchStockPredictor(
        comprehensive_data_file=args.input,
        max_concurrent=args.max_concurrent
    )
    
    # Determine symbols to process
    symbols_to_process = args.symbols
    
    if args.sector or args.limit:
        # Filter by sector or limit if specified
        all_stocks = list(predictor.comprehensive_data.keys())
        
        if args.sector:
            sector_stocks = [s for s, data in predictor.comprehensive_data.items() if data.sector == args.sector]
            print(f"🔍 Filtering by {args.sector} sector: {len(sector_stocks)} stocks")
            symbols_to_process = sector_stocks
        else:
            symbols_to_process = all_stocks
        
        if args.limit and args.limit < len(symbols_to_process):
            symbols_to_process = symbols_to_process[:args.limit]
            print(f"🔢 Limiting to {args.limit} stocks")
    
    # Run predictions
    asyncio.run(predictor.run_batch_predictions(
        symbols=symbols_to_process,
        providers=args.providers
    ))
    
    print("\n🎉 Batch predictions completed!")

if __name__ == "__main__":
    main() 