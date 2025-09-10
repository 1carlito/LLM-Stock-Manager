"""
LLM Results Manager

This module handles storing, comparing, and analyzing predictions from different LLM providers.
It tracks predictions and their accuracy over time, and provides tools for comparing
performance between different models.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import pandas as pd
import matplotlib.pyplot as plt

@dataclass
class PredictionMetrics:
    """Stores the actual vs predicted metrics for a stock"""
    revenue: float
    eps: float
    operating_margin: float
    net_income: float

@dataclass
class LLMPredictionResult:
    """Extended prediction result with actual values for comparison"""
    # Prediction details
    stock_ticker: str
    prediction_date: str
    target_quarter: str
    llm_provider: str
    model_used: str
    model_training_cutoff: str
    
    # Predicted values
    predicted_metrics: PredictionMetrics
    predicted_price_reaction: float
    confidence_level: float
    reasoning: str
    
    # Actual values (to be filled after earnings)
    actual_metrics: Optional[PredictionMetrics] = None
    actual_price_reaction: Optional[float] = None
    
    # Accuracy metrics (calculated when actuals are available)
    revenue_accuracy: Optional[float] = None
    eps_accuracy: Optional[float] = None
    price_reaction_accuracy: Optional[float] = None
    overall_accuracy: Optional[float] = None

class LLMResultsManager:
    """Manages storage and analysis of LLM predictions"""
    
    def __init__(self, results_dir: str = "llm_results"):
        """Initialize with directory for storing results"""
        self.results_dir = results_dir
        self.predictions: Dict[str, List[LLMPredictionResult]] = {}
        self._load_existing_results()
    
    def _load_existing_results(self):
        """Load existing prediction results from disk"""
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Load all JSON files in the results directory
        for filename in os.listdir(self.results_dir):
            if filename.endswith('.json'):
                with open(os.path.join(self.results_dir, filename), 'r') as f:
                    data = json.load(f)
                    ticker = data['stock_ticker']
                    if ticker not in self.predictions:
                        self.predictions[ticker] = []
                    self.predictions[ticker].append(
                        LLMPredictionResult(**data)
                    )
    
    def add_prediction(self, prediction: LLMPredictionResult):
        """Add a new prediction result"""
        ticker = prediction.stock_ticker
        if ticker not in self.predictions:
            self.predictions[ticker] = []
        
        self.predictions[ticker].append(prediction)
        self._save_prediction(prediction)
    
    def _save_prediction(self, prediction: LLMPredictionResult):
        """Save prediction to JSON file"""
        filename = f"{prediction.stock_ticker}_{prediction.llm_provider}_{prediction.prediction_date}.json"
        filepath = os.path.join(self.results_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(asdict(prediction), f, indent=2)
    
    def update_with_actuals(self, 
                          ticker: str,
                          target_quarter: str,
                          actual_metrics: PredictionMetrics,
                          actual_price_reaction: float):
        """Update predictions with actual results and calculate accuracy"""
        if ticker not in self.predictions:
            return
        
        for pred in self.predictions[ticker]:
            if pred.target_quarter == target_quarter and pred.actual_metrics is None:
                # Update actual values
                pred.actual_metrics = actual_metrics
                pred.actual_price_reaction = actual_price_reaction
                
                # Calculate accuracy metrics
                pred.revenue_accuracy = self._calculate_accuracy(
                    pred.predicted_metrics.revenue,
                    actual_metrics.revenue
                )
                pred.eps_accuracy = self._calculate_accuracy(
                    pred.predicted_metrics.eps,
                    actual_metrics.eps
                )
                pred.price_reaction_accuracy = self._calculate_accuracy(
                    pred.predicted_price_reaction,
                    actual_price_reaction
                )
                
                # Calculate overall accuracy
                pred.overall_accuracy = (
                    pred.revenue_accuracy +
                    pred.eps_accuracy +
                    pred.price_reaction_accuracy
                ) / 3
                
                # Save updated prediction
                self._save_prediction(pred)
    
    def _calculate_accuracy(self, predicted: float, actual: float) -> float:
        """Calculate accuracy percentage between predicted and actual values"""
        if actual == 0:
            return 100 if predicted == 0 else 0
        return 100 * (1 - abs(predicted - actual) / abs(actual))
    
    def get_provider_performance(self, provider: str = None) -> pd.DataFrame:
        """Get performance metrics for a specific provider or all providers"""
        data = []
        
        for ticker, predictions in self.predictions.items():
            for pred in predictions:
                if provider and pred.llm_provider != provider:
                    continue
                    
                if pred.actual_metrics:  # Only include predictions with actuals
                    data.append({
                        'Stock': ticker,
                        'Provider': pred.llm_provider,
                        'Model': pred.model_used,
                        'Quarter': pred.target_quarter,
                        'Revenue Accuracy': pred.revenue_accuracy,
                        'EPS Accuracy': pred.eps_accuracy,
                        'Price Reaction Accuracy': pred.price_reaction_accuracy,
                        'Overall Accuracy': pred.overall_accuracy,
                        'Confidence Level': pred.confidence_level
                    })
        
        return pd.DataFrame(data)
    
    def plot_provider_comparison(self):
        """Plot accuracy comparison between providers"""
        df = self.get_provider_performance()
        if df.empty:
            print("No predictions with actual results available yet.")
            return
        
        metrics = ['Revenue Accuracy', 'EPS Accuracy', 'Price Reaction Accuracy', 'Overall Accuracy']
        
        plt.figure(figsize=(12, 6))
        df.groupby('Provider')[metrics].mean().plot(kind='bar')
        plt.title('LLM Provider Accuracy Comparison')
        plt.xlabel('Provider')
        plt.ylabel('Accuracy (%)')
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Save plot
        os.makedirs('plots', exist_ok=True)
        plt.savefig('plots/provider_comparison.png')
        plt.close()
    
    def get_prediction_history(self, ticker: str) -> List[LLMPredictionResult]:
        """Get prediction history for a specific stock"""
        return self.predictions.get(ticker, [])
    
    def export_results(self, output_file: str = "llm_prediction_results.csv"):
        """Export all prediction results to CSV"""
        df = pd.DataFrame([
            {
                'Stock': pred.stock_ticker,
                'Date': pred.prediction_date,
                'Quarter': pred.target_quarter,
                'Provider': pred.llm_provider,
                'Model': pred.model_used,
                'Predicted Revenue': pred.predicted_metrics.revenue,
                'Actual Revenue': pred.actual_metrics.revenue if pred.actual_metrics else None,
                'Revenue Accuracy': pred.revenue_accuracy,
                'Predicted EPS': pred.predicted_metrics.eps,
                'Actual EPS': pred.actual_metrics.eps if pred.actual_metrics else None,
                'EPS Accuracy': pred.eps_accuracy,
                'Predicted Price Reaction': pred.predicted_price_reaction,
                'Actual Price Reaction': pred.actual_price_reaction,
                'Price Reaction Accuracy': pred.price_reaction_accuracy,
                'Overall Accuracy': pred.overall_accuracy,
                'Confidence Level': pred.confidence_level,
                'Reasoning': pred.reasoning
            }
            for ticker_preds in self.predictions.values()
            for pred in ticker_preds
        ])
        
        df.to_csv(output_file, index=False)

def main():
    """Example usage of LLMResultsManager"""
    # Initialize results manager
    results_manager = LLMResultsManager()
    
    # Example of adding a new prediction
    example_prediction = LLMPredictionResult(
        stock_ticker="MSFT",
        prediction_date=datetime.now().strftime("%Y-%m-%d"),
        target_quarter="Q2 2025",
        llm_provider="anthropic",
        model_used="claude-2.1",
        model_training_cutoff="2023-08-01",
        predicted_metrics=PredictionMetrics(
            revenue=65.5,  # billions
            eps=2.85,
            operating_margin=0.45,
            net_income=22.3  # billions
        ),
        predicted_price_reaction=2.5,  # percentage
        confidence_level=85.0,
        reasoning="Strong cloud growth and AI adoption likely to drive revenue..."
    )
    
    results_manager.add_prediction(example_prediction)
    
    # Example of updating with actual results
    results_manager.update_with_actuals(
        ticker="MSFT",
        target_quarter="Q2 2025",
        actual_metrics=PredictionMetrics(
            revenue=66.2,
            eps=2.90,
            operating_margin=0.44,
            net_income=22.8
        ),
        actual_price_reaction=2.8
    )
    
    # Generate performance analysis
    print("\nProvider Performance:")
    print(results_manager.get_provider_performance())
    
    # Plot comparison
    results_manager.plot_provider_comparison()
    
    # Export results
    results_manager.export_results()

if __name__ == "__main__":
    main() 