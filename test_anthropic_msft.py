#!/usr/bin/env python3

from llm_predictor import EarningsPredictorLLM
from prompt_engineering import MSFT_PREDICTION_PROMPT

def main():
    print("Testing Anthropic prediction for Microsoft Q2 2025...")
    
    try:
        predictor = EarningsPredictorLLM('anthropic')
        result = predictor.predict_earnings('MSFT', MSFT_PREDICTION_PROMPT)
        
        print("\n" + "="*50)
        print("ANTHROPIC PREDICTION RESULT")
        print("="*50)
        print(f"Stock: {result.stock_ticker}")
        print(f"Provider: {result.llm_provider}")
        print(f"Model: {result.model_used}")
        print(f"Training Cutoff: {result.model_training_cutoff}")
        print(f"Pre-earnings price: ${result.pre_earnings_price:.2f}")
        print(f"1-day target: ${result.price_target_1d:.2f}")
        print(f"5-day target: ${result.price_target_5d:.2f}")
        print(f"1-day confidence: {result.confidence_level_1d:.1f}%")
        print(f"5-day confidence: {result.confidence_level_5d:.1f}%")
        
        print("\n" + "="*50)
        print("REASONING (first 500 chars):")
        print("="*50)
        print(result.reasoning[:500] + "..." if len(result.reasoning) > 500 else result.reasoning)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 