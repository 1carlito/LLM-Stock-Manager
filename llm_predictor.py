"""
LLM API Handler for Stock Earnings Predictions

Supports multiple LLM providers (OpenAI, Anthropic, DeepSeek) and manages API calls
for stock earnings predictions.

IMPORTANT: Only use models trained on data before 2025 to avoid data leakage
in future earnings predictions.
"""

import os
from typing import Dict, Optional, List, Tuple
from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
from datetime import datetime
import requests
from openai import OpenAI
import google.generativeai as genai
from dotenv import load_dotenv
import re
import time

# Load environment variables from .env file
load_dotenv()

from llm_results import PredictionMetrics

@dataclass
class PredictionResult:
    """Extended prediction result with actual values for comparison"""
    # Prediction details
    stock_ticker: str
    prediction_date: str
    target_quarter: str
    llm_provider: str
    model_used: str
    model_training_cutoff: str
    
    # Predicted values
    predicted_metrics: Optional[PredictionMetrics]
    pre_earnings_price: float
    price_target_1d: float
    price_target_5d: float
    confidence_level_1d: float
    confidence_level_5d: float
    reasoning: str

def deploy_prediction(provider: str, stock: str, prompt: str) -> Tuple[PredictionResult, str]:
    """
    Deploy a prediction for a specific stock using a specific LLM provider.
    
    Args:
        provider: The LLM provider to use ("anthropic", "openai", or "deepseek")
        stock: Stock ticker symbol
        prompt: The engineered prompt for the prediction
    
    Returns:
        Tuple of (prediction_result, error_message)
        If successful, error_message will be empty string
        If failed, prediction_result will be None and error_message will contain the error
    """
    try:
        predictor = EarningsPredictorLLM(provider=provider)
        prediction = predictor.predict_earnings(stock, prompt)
        return prediction, ""
    except Exception as e:
        return None, str(e)

class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    def predict(self, prompt: str) -> str:
        """Make API call to LLM provider and return response"""
        pass
    
    @property
    @abstractmethod
    def training_cutoff(self) -> str:
        """Return the training data cutoff date for the model"""
        pass
    
    @property
    def provider_name(self) -> str:
        """Return the name of the provider"""
        pass

class AnthropicProvider(LLMProvider):
    """Anthropic Claude API implementation"""
    
    def __init__(self, api_key: str = None):
        # Hardcode the API key
        self.api_key = "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"
        self.api_url = "https://api.anthropic.com/v1/messages"
        # Using Claude 3 Sonnet
        self.model = "claude-3-5-sonnet-20241022"  # Using the model that exists in the API response
    
    def predict(self, prompt: str) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 4000
        }
        
        print(f"Making request to Anthropic API with model: {self.model}")
        try:
        response = requests.post(self.api_url, headers=headers, json=data)
            print(f"Response status code: {response.status_code}")
            
            if response.status_code != 200:
                print(f"Error response: {response.text}")
                
            response.raise_for_status()
            
            result = response.json()
            return result['content'][0]['text']
        except Exception as e:
            print(f"Detailed error in Anthropic API call: {str(e)}")
            raise
    
    @property
    def training_cutoff(self) -> str:
        return "2024-10-22"  # Updated training cutoff for Claude 3.5 Sonnet
    
    @property
    def provider_name(self) -> str:
        return "anthropic"

class OpenAIProvider(LLMProvider):
    """OpenAI API implementation"""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4-turbo"
    
    def predict(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a financial analyst expert at predicting stock prices and earnings."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4000
        )
        
        return response.choices[0].message.content
    
    @property
    def training_cutoff(self) -> str:
        return "2023-12-01"  # GPT-4 training cutoff
    
    @property
    def provider_name(self) -> str:
        return "openai"

class DeepSeekProvider(LLMProvider):
    """DeepSeek API implementation"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.model = "deepseek-chat"
    
    def predict(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a financial analyst expert at predicting stock prices and earnings."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 4000
        }
        
        response = requests.post(self.api_url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        return result['choices'][0]['message']['content']
    
    @property
    def training_cutoff(self) -> str:
        return "2023-11-01"  # DeepSeek training cutoff
    
    @property
    def provider_name(self) -> str:
        return "deepseek"

class GeminiProvider(LLMProvider):
    """Google Gemini API implementation using Gemini 2.5 Flash-Lite"""
    
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')  # Using Flash-Lite model
    
    def predict(self, prompt: str) -> str:
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "max_output_tokens": 2048
        }
        
        safety_settings = {
            "harassment": "block_none",
            "hate_speech": "block_none",
            "sexually_explicit": "block_none",
            "dangerous_content": "block_none"
        }
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            if response.prompt_feedback:
                print(f"Prompt feedback: {response.prompt_feedback}")
            
            return response.text
        except Exception as e:
            print(f"Gemini API error: {str(e)}")
            time.sleep(2)  # Retry after delay
            try:
                response = self.model.generate_content(prompt)
                return response.text
            except Exception as retry_error:
                print(f"Gemini API retry error: {str(retry_error)}")
                raise
    
    @property
    def training_cutoff(self) -> str:
        return "2025-01-01"  # Updated training cutoff for Gemini 2.5 Flash-Lite
    
    @property
    def provider_name(self) -> str:
        return "gemini"

class EarningsPredictorLLM:
    """LLM-based earnings predictor using multiple providers"""
    
    def __init__(self, provider: str = "anthropic"):
        """
        Initialize the LLM earnings predictor
        
        Args:
            provider: LLM provider to use ("anthropic", "openai", "deepseek", or "gemini")
        """
        # Check if provider is available
        available, message = self.check_provider_availability(provider)
        if not available:
            raise ValueError(f"Provider {provider} is not available: {message}")
        
        self.provider_name = provider
        self.llm = self._initialize_provider(provider)
    
    def _initialize_provider(self, provider: str) -> LLMProvider:
        """Initialize the specified LLM provider"""
        if provider == "anthropic":
            # No need to check for API key since it's hardcoded
            return AnthropicProvider()
        
        elif provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set in environment variables")
            return OpenAIProvider(api_key)
        
        elif provider == "deepseek":
            api_key = os.getenv("DEEPSEEK_API_KEY")
            if not api_key:
                raise ValueError("DEEPSEEK_API_KEY not set in environment variables")
            return DeepSeekProvider(api_key)
        
        elif provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not set in environment variables")
            return GeminiProvider(api_key)
        
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    @staticmethod
    def check_provider_availability(provider: str) -> Tuple[bool, str]:
        """Check if a provider is available based on API keys"""
        if provider == "anthropic":
            # Anthropic API key is hardcoded
            return True, "Provider available"
        
        elif provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return False, "OPENAI_API_KEY not set in environment variables"
        
        elif provider == "deepseek":
            api_key = os.getenv("DEEPSEEK_API_KEY")
            if not api_key:
                return False, "DEEPSEEK_API_KEY not set in environment variables"
        
        elif provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                return False, "GEMINI_API_KEY not set in environment variables"
        
        else:
            return False, f"Unsupported provider: {provider}"
        
        return True, "Provider available"
    
    def predict_earnings(self, stock_ticker: str, prompt: str) -> PredictionResult:
        """
        Predict earnings and stock price reactions using the LLM
        
        Args:
            stock_ticker: Stock ticker symbol
            prompt: Engineered prompt with stock data
            
        Returns:
            PredictionResult object with predictions
        """
        # Generate LLM prediction
        try:
        response = self.llm.predict(prompt)
        
            # Parse the response to extract predictions
            parsed = self._parse_prediction_response(response, stock_ticker)
            
            # Create prediction metrics
            metrics = PredictionMetrics(
                revenue=parsed.get('revenue', 0.0),
                eps=parsed.get('eps', 0.0),
                operating_margin=parsed.get('operating_margin', 0.0),
                net_income=parsed.get('net_income', 0.0)
            )
            
            # Create prediction result
            result = PredictionResult(
                stock_ticker=stock_ticker,
                prediction_date=datetime.now().strftime('%Y-%m-%d'),
                target_quarter="Q2 2025",  # Default target quarter
                llm_provider=self.provider_name,
            model_used=self.llm.model,
            model_training_cutoff=self.llm.training_cutoff,
            predicted_metrics=metrics,
                pre_earnings_price=parsed.get('pre_earnings_price', 0.0),
                price_target_1d=parsed.get('price_target_1d', 0.0),
                price_target_5d=parsed.get('price_target_5d', 0.0),
                confidence_level_1d=parsed.get('confidence_1d', 0.0),
                confidence_level_5d=parsed.get('confidence_5d', 0.0),
                reasoning=parsed.get('reasoning', response)
            )
            
            return result
            
        except Exception as e:
            # If there's an error, create a minimal result with the error message
            empty_metrics = PredictionMetrics(
                revenue=0.0,
                eps=0.0,
                operating_margin=0.0,
                net_income=0.0
            )
            
            return PredictionResult(
                stock_ticker=stock_ticker,
                prediction_date=datetime.now().strftime('%Y-%m-%d'),
                target_quarter="Q2 2025",
                llm_provider=self.provider_name,
                model_used=getattr(self.llm, 'model', 'unknown'),
                model_training_cutoff=getattr(self.llm, 'training_cutoff', 'unknown'),
                predicted_metrics=empty_metrics,
                pre_earnings_price=0.0,
                price_target_1d=0.0,
                price_target_5d=0.0,
                confidence_level_1d=0.0,
                confidence_level_5d=0.0,
                reasoning=str(e)
            )
    
    def _parse_prediction_response(self, response: str, stock_ticker: str) -> Dict:
        """Parse the LLM response to extract structured predictions"""
        result = {
            'revenue': 0.0,
            'eps': 0.0,
            'operating_margin': 0.0,
            'net_income': 0.0,
            'pre_earnings_price': 0.0,
            'price_target_1d': 0.0,
            'price_target_5d': 0.0,
            'confidence_1d': 0.0,
            'confidence_5d': 0.0,
            'reasoning': response
        }
        
        try:
            # Extract current price
            current_price_match = re.search(r'CURRENT PRICE: \$(\d+\.\d+)', response)
            if current_price_match:
                result['pre_earnings_price'] = float(current_price_match.group(1))
            
            # Extract 1-day prediction
            target_1d_match = re.search(r'TARGET PRICE: \$(\d+\.\d+)', response)
            if target_1d_match:
                result['price_target_1d'] = float(target_1d_match.group(1))
            
            # Extract 1-day confidence
            confidence_1d_match = re.search(r'CONFIDENCE: (\d+)%', response)
            if confidence_1d_match:
                result['confidence_1d'] = float(confidence_1d_match.group(1))
            
            # Extract 5-day prediction
            sections = response.split('5-DAY PREDICTION:')
            if len(sections) > 1:
                target_5d_match = re.search(r'TARGET PRICE: \$(\d+\.\d+)', sections[1])
                if target_5d_match:
                    result['price_target_5d'] = float(target_5d_match.group(1))
                
                confidence_5d_match = re.search(r'CONFIDENCE: (\d+)%', sections[1])
                if confidence_5d_match:
                    result['confidence_5d'] = float(confidence_5d_match.group(1))
            
            # Extract reasoning
            reasoning_sections = response.split('REASONING:')
            if len(reasoning_sections) > 1:
                result['reasoning'] = reasoning_sections[1].strip()
            
            return result
            
        except Exception as e:
            print(f"Error parsing prediction response: {e}")
            return result

def main():
    """Test the LLM predictor with a sample prompt"""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python llm_predictor.py <provider> <stock_ticker>")
        return
    
    provider = sys.argv[1]
    stock = sys.argv[2]
    
    # Check if provider is available
            available, message = EarningsPredictorLLM.check_provider_availability(provider)
            if not available:
        print(f"Provider {provider} is not available: {message}")
        return
    
    # Create sample prompt
    prompt = f"""
    Please predict the stock price for {stock} based on the following information:
    
    COMPANY: {stock}
    SECTOR: Technology
    CURRENT PRICE: $200.00
    
    Provide your prediction in this format:
    
    CURRENT PRICE: $200.00
    
    1-DAY PREDICTION:
    TARGET PRICE: $205.00
    CHANGE: +2.5%
    CONFIDENCE: 70%
    
    5-DAY PREDICTION:
    TARGET PRICE: $210.00
    CHANGE: +5.0%
    CONFIDENCE: 60%
    
    REASONING:
    [Your detailed analysis]
    """
    
    # Deploy prediction
    predictor = EarningsPredictorLLM(provider=provider)
    prediction = predictor.predict_earnings(stock, prompt)
    
    # Print results
    print(f"\nPrediction for {stock} using {provider}:")
    print(f"Current Price: ${prediction.pre_earnings_price:.2f}")
    print(f"1-Day Target: ${prediction.price_target_1d:.2f} (Confidence: {prediction.confidence_level_1d:.0f}%)")
    print(f"5-Day Target: ${prediction.price_target_5d:.2f} (Confidence: {prediction.confidence_level_5d:.0f}%)")
    print(f"\nReasoning:\n{prediction.reasoning[:500]}...")

if __name__ == "__main__":
    main() 