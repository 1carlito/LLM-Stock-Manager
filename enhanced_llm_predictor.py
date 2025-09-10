"""
Enhanced LLM Predictor with FMP Analyst Data
============================================

This script enhances LLM predictions by incorporating real analyst ratings
and consensus data from Financial Modeling Prep API to improve accuracy.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any
from llm_predictor import EarningsPredictorLLM, deploy_prediction
from prompt_engineering import (
    PLTR_ENHANCED_PREDICTION_PROMPT,
    NVO_ENHANCED_PREDICTION_PROMPT,
    BP_ENHANCED_PREDICTION_PROMPT
)

class EnhancedLLMPredictor:
    """Enhanced LLM predictor with analyst data integration"""
    
    def __init__(self):
        self.analyst_data = self.load_analyst_data()
        self.llm_providers = ['deepseek', 'anthropic', 'gemini', 'openai']
    
    def load_analyst_data(self) -> Dict[str, Any]:
        """Load analyst data from FMP API results"""
        try:
            with open('analyst_ratings/all_analyst_ratings.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("⚠️  No analyst data found. Run fmp_analyst_ratings.py first.")
            return {}
    
    def format_analyst_consensus(self, symbol: str) -> str:
        """Format analyst consensus data for prompts"""
        if symbol not in self.analyst_data:
            return "No analyst consensus data available"
        
        data = self.analyst_data[symbol]
        consensus_data = data.get('price_target_consensus', [])
        
        if not consensus_data:
            return "No price target consensus available"
        
        consensus = consensus_data[0]
        formatted = f"""
ANALYST CONSENSUS DATA (Latest from FMP API):
- High Price Target: ${consensus.get('targetHigh', 0):.2f}
- Low Price Target: ${consensus.get('targetLow', 0):.2f}
- Average Consensus: ${consensus.get('targetConsensus', 0):.2f}
- Median Target: ${consensus.get('targetMedian', 0):.2f}
"""
        
        # Add recent analyst actions
        grades = data.get('current_grades', [])
        if grades:
            formatted += "\nRECENT ANALYST ACTIONS:\n"
            for grade in grades[:5]:  # Show last 5 actions
                formatted += f"- {grade.get('gradingCompany', 'Unknown')}: {grade.get('action', 'unknown')} ({grade.get('newGrade', 'Unknown')})\n"
        
        return formatted
    
    def create_enhanced_prompt(self, symbol: str, base_prompt: str) -> str:
        """Create enhanced prompt with analyst data"""
        
        analyst_consensus = self.format_analyst_consensus(symbol)
        
        enhanced_prompt = f"""
{base_prompt}

{analyst_consensus}

ENHANCED ANALYSIS INSTRUCTIONS:
Based on the above historical data, recent news, AND the current analyst consensus data, provide your most accurate prediction. Consider:

1. How analyst consensus compares to historical patterns
2. Whether recent analyst actions suggest changing sentiment
3. The range of analyst price targets and their implications
4. How your prediction aligns with or differs from analyst consensus

Please provide your enhanced prediction with specific reasoning about how the analyst data influenced your analysis.
"""
        
        return enhanced_prompt
    
    def get_stock_prompts(self) -> Dict[str, str]:
        """Get base prompts for each stock"""
        return {
            'PLTR': PLTR_ENHANCED_PREDICTION_PROMPT,
            'NVO': NVO_ENHANCED_PREDICTION_PROMPT,
            'BP': BP_ENHANCED_PREDICTION_PROMPT
        }
    
    def run_enhanced_predictions(self, symbol: str, provider: str = None) -> Dict[str, Any]:
        """Run enhanced predictions for a specific stock"""
        
        print(f"\n{'='*80}")
        print(f"🚀 ENHANCED PREDICTIONS FOR {symbol}")
        print(f"{'='*80}")
        
        # Get base prompt
        stock_prompts = self.get_stock_prompts()
        if symbol not in stock_prompts:
            print(f"❌ No prompt available for {symbol}")
            return {}
        
        base_prompt = stock_prompts[symbol]
        
        # Create enhanced prompt
        enhanced_prompt = self.create_enhanced_prompt(symbol, base_prompt)
        
        results = {}
        
        # Run predictions with all providers or specific provider
        providers_to_test = [provider] if provider else self.llm_providers
        
        for llm_provider in providers_to_test:
            print(f"\n🔍 Testing {llm_provider.upper()} with enhanced analyst data...")
            
            try:
                prediction, error = deploy_prediction(llm_provider, symbol, enhanced_prompt)
                
                if error:
                    print(f"❌ {llm_provider.upper()} Error: {error}")
                    results[llm_provider] = {'error': error}
                else:
                    print(f"✅ {llm_provider.upper()} Enhanced Prediction Complete")
                    results[llm_provider] = {
                        'prediction': prediction,
                        'model_used': prediction.model_used,
                        'training_cutoff': prediction.model_training_cutoff,
                        'response': prediction.response
                    }
                    
                    # Print key metrics
                    if hasattr(prediction, 'revenue_prediction') and prediction.revenue_prediction:
                        print(f"   📊 Revenue: {prediction.revenue_prediction}")
                    if hasattr(prediction, 'eps_prediction') and prediction.eps_prediction:
                        print(f"   💰 EPS: {prediction.eps_prediction}")
                    if hasattr(prediction, 'price_target_1d') and prediction.price_target_1d:
                        print(f"   📈 1-Day Target: ${prediction.price_target_1d}")
                    if hasattr(prediction, 'price_target_5d') and prediction.price_target_5d:
                        print(f"   📈 5-Day Target: ${prediction.price_target_5d}")
                
            except Exception as e:
                print(f"❌ {llm_provider.upper()} Exception: {e}")
                results[llm_provider] = {'error': str(e)}
        
        return results
    
    def run_all_enhanced_predictions(self) -> Dict[str, Dict[str, Any]]:
        """Run enhanced predictions for all stocks"""
        
        all_results = {}
        stocks = ['PLTR', 'NVO', 'BP']
        
        for stock in stocks:
            print(f"\n{'='*80}")
            print(f"📊 ENHANCED PREDICTIONS FOR {stock}")
            print(f"{'='*80}")
            
            results = self.run_enhanced_predictions(stock)
            all_results[stock] = results
        
        return all_results
    
    def save_enhanced_results(self, results: Dict[str, Dict[str, Any]]):
        """Save enhanced prediction results"""
        
        # Create output directory
        os.makedirs('enhanced_predictions', exist_ok=True)
        
        # Save comprehensive JSON
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        json_path = f'enhanced_predictions/enhanced_predictions_{timestamp}.json'
        
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n✅ Enhanced predictions saved: {json_path}")
        
        # Create summary CSV
        summary_data = []
        for stock, stock_results in results.items():
            for provider, provider_result in stock_results.items():
                if 'error' not in provider_result:
                    prediction = provider_result.get('prediction')
                    if prediction:
                        summary_data.append({
                            'stock': stock,
                            'provider': provider,
                            'model': provider_result.get('model_used', 'Unknown'),
                            'training_cutoff': provider_result.get('training_cutoff', 'Unknown'),
                            'revenue_prediction': getattr(prediction, 'revenue_prediction', 'N/A'),
                            'eps_prediction': getattr(prediction, 'eps_prediction', 'N/A'),
                            'price_target_1d': getattr(prediction, 'price_target_1d', 'N/A'),
                            'price_target_5d': getattr(prediction, 'price_target_5d', 'N/A'),
                            'confidence': getattr(prediction, 'confidence', 'N/A')
                        })
                else:
                    summary_data.append({
                        'stock': stock,
                        'provider': provider,
                        'model': 'Error',
                        'training_cutoff': 'Error',
                        'revenue_prediction': 'Error',
                        'eps_prediction': 'Error',
                        'price_target_1d': 'Error',
                        'price_target_5d': 'Error',
                        'confidence': provider_result.get('error', 'Unknown Error')
                    })
        
        if summary_data:
            import pandas as pd
            df = pd.DataFrame(summary_data)
            csv_path = f'enhanced_predictions/enhanced_predictions_summary_{timestamp}.csv'
            df.to_csv(csv_path, index=False)
            print(f"✅ Enhanced predictions summary saved: {csv_path}")
        
        return json_path
    
    def compare_with_analyst_consensus(self, results: Dict[str, Dict[str, Any]]):
        """Compare LLM predictions with analyst consensus"""
        
        print(f"\n{'='*80}")
        print("📊 COMPARISON WITH ANALYST CONSENSUS")
        print(f"{'='*80}")
        
        for stock, stock_results in results.items():
            if stock not in self.analyst_data:
                continue
            
            consensus_data = self.analyst_data[stock].get('price_target_consensus', [])
            if not consensus_data:
                continue
            
            consensus = consensus_data[0]
            consensus_avg = consensus.get('targetConsensus', 0)
            consensus_high = consensus.get('targetHigh', 0)
            consensus_low = consensus.get('targetLow', 0)
            
            print(f"\n🏢 {stock} - Analyst Consensus: ${consensus_avg:.2f} (${consensus_low:.2f} - ${consensus_high:.2f})")
            
            for provider, provider_result in stock_results.items():
                if 'error' not in provider_result:
                    prediction = provider_result.get('prediction')
                    if prediction and hasattr(prediction, 'price_target_5d'):
                        llm_target = prediction.price_target_5d
                        if llm_target and llm_target != 'N/A':
                            try:
                                llm_target = float(llm_target)
                                diff = llm_target - consensus_avg
                                diff_pct = (diff / consensus_avg) * 100 if consensus_avg > 0 else 0
                                
                                print(f"   {provider.upper()}: ${llm_target:.2f} (Diff: {diff:+.2f}, {diff_pct:+.1f}%)")
                            except (ValueError, TypeError):
                                print(f"   {provider.upper()}: {llm_target} (Cannot compare)")
                        else:
                            print(f"   {provider.upper()}: No price target")
                else:
                    print(f"   {provider.upper()}: Error - {provider_result.get('error', 'Unknown')}")

def main():
    """Main function for enhanced predictions"""
    
    print("🚀 Enhanced LLM Predictor with FMP Analyst Data")
    print("=" * 60)
    
    # Initialize enhanced predictor
    enhanced_predictor = EnhancedLLMPredictor()
    
    # Check if analyst data is available
    if not enhanced_predictor.analyst_data:
        print("❌ No analyst data found. Please run fmp_analyst_ratings.py first.")
        return
    
    print("✅ Analyst data loaded successfully")
    
    # Show available analyst data
    for stock in ['PLTR', 'NVO', 'BP']:
        if stock in enhanced_predictor.analyst_data:
            data = enhanced_predictor.analyst_data[stock]
            consensus = data.get('price_target_consensus', [])
            grades = data.get('current_grades', [])
            
            print(f"\n📊 {stock} Analyst Data:")
            if consensus:
                c = consensus[0]
                print(f"   Consensus: ${c.get('targetConsensus', 0):.2f} (${c.get('targetLow', 0):.2f} - ${c.get('targetHigh', 0):.2f})")
            print(f"   Recent Grades: {len(grades)} analyst actions")
    
    # Run enhanced predictions
    print(f"\n🎯 Starting enhanced predictions...")
    results = enhanced_predictor.run_all_enhanced_predictions()
    
    # Save results
    enhanced_predictor.save_enhanced_results(results)
    
    # Compare with analyst consensus
    enhanced_predictor.compare_with_analyst_consensus(results)
    
    print(f"\n🎉 Enhanced predictions complete!")
    print(f"📁 Results saved to: enhanced_predictions/")

if __name__ == "__main__":
    main() 