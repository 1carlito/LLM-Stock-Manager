# Stock Agent Evaluation Project

A comprehensive framework for evaluating stock price prediction agents using large language models (LLMs) for earnings-based predictions.

## 🎯 Project Overview

This project evaluates the accuracy of stock price predictions around earnings events using:
- **Large Language Models**: Claude, GPT, DeepSeek, and Gemini for earnings predictions
- **Multi-Sector Analysis**: Tech, Pharmaceutical, and Oil & Energy sectors
- **Enhanced Predictions**: Incorporating analyst ratings and recent company news
- **Real-time API Data**: Integration with Financial Modeling Prep API for earnings data

## 📊 Supported Stocks

### Tech Sector
- **Microsoft (MSFT)**: Q2 2025 predictions with enhanced news data
- **Palantir (PLTR)**: Q1 2025 predictions with government contracts and AI partnerships

### Pharmaceutical Sector  
- **Novo Nordisk (NVO)**: Q1 2025 predictions with clinical trial results and regulatory updates

### Oil & Energy Sector
- **BP (BP)**: Q1 2025 predictions with strategic divestments and production expansion

## 🏗️ Project Structure

```
stock_agent_eval/
├── data_loader.py              # Parses earnings data for LLM predictions
├── earnings_data.txt           # Historical earnings data and analyst ratings
├── earnings_api_client.py      # API client for fetching real-time earnings data
├── llm_predictor.py            # LLM API integration and prediction management
├── llm_results.py              # Results storage and analysis framework
├── prompt_engineering.py       # LLM prompt templates with news data
├── enhanced_llm_predictor.py   # Enhanced LLM predictions with news context
├── run_api_predictions.py      # Script to run predictions with API data
├── batch_stock_predictor.py    # Batch processor for multiple stocks
├── llm_results/                # LLM prediction results (JSON files)
├── tech_stocks_predictions.txt # Tech sector analysis results
├── pharma_stocks_predictions.txt # Pharmaceutical sector analysis results
├── oil_stocks_predictions.txt  # Oil & energy sector analysis results
└── stock_price_accuracy.txt    # Overall accuracy analysis
```

## 🚀 Features

### LLM-Based Agent
- **Multi-Provider Support**: Claude, GPT, DeepSeek, Gemini
- **Training Cutoff Validation**: Ensures no data leakage for predictions
- **Enhanced Prompts**: Include analyst ratings and recent company news
- **Structured Output**: Parses numerical predictions from LLM responses

### API Integration
- **Financial Modeling Prep API**: Fetches real-time earnings data, analyst ratings, and price targets
- **Caching Support**: Stores API data locally to reduce API calls
- **Batch Processing**: Handles multiple stocks efficiently

### Evaluation Framework
- **Directional Accuracy**: Whether stock moves up/down as predicted
- **Magnitude Accuracy**: How close predicted vs actual price movements
- **Financial Metric Accuracy**: Revenue, EPS prediction accuracy
- **Sector-Specific Analysis**: Organized by industry sectors

## 📈 Key Results

### LLM Performance Comparison (Q1 2025)
| Model | Revenue Accuracy | EPS Accuracy | Stock Direction | Best Performer |
|-------|-----------------|--------------|-----------------|----------------|
| DeepSeek | 98.4% | 94.2% | 67% | Financial Metrics |
| Claude | 96.0% | 92.1% | 67% | Balanced |
| Gemini | 97.8% | 94.7% | 100% | Stock Direction |
| GPT-3.5 | 93.1% | 85.1% | 100% | Stock Direction |

### Sector Performance
- **Tech Sector**: Mixed results, challenging to predict due to high volatility
- **Pharma Sector**: Strong performance, predictable patterns with clinical news
- **Oil & Energy**: Consistent performance, influenced by commodity prices

## 🛠️ Setup Instructions

### Prerequisites
```bash
python 3.8+
pip install pandas numpy requests openai google-generativeai
```

### Environment Variables
Create a `.env` file with your API keys:
```bash
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key
DEEPSEEK_API_KEY=your_deepseek_key
GEMINI_API_KEY=your_gemini_key
FMP_API_KEY=your_fmp_api_key
```

### Installation
```bash
git clone <repository-url>
cd stock_agent_eval
pip install -r requirements.txt
```

## 📖 Usage

### Parse Earnings Data
```bash
python data_loader.py
```

### Fetch Real-time API Data
```bash
python earnings_api_client.py
```

### Run LLM-Based Predictions with API Data
```bash
python run_api_predictions.py --symbols MSFT PLTR NVO BP --providers anthropic openai
```

### Run Batch Predictions for Multiple Stocks
```bash
python batch_stock_predictor.py
```

### Analyze Results
```bash
python llm_results.py
```

## 🔍 Key Insights

### LLM Performance Patterns
1. **Financial Metrics**: All LLMs excel at predicting revenue and EPS (85-98% accuracy)
2. **Stock Direction**: More challenging, Gemini and GPT-3.5 performed best (100% accuracy)
3. **Enhanced Prompts**: News data improved predictions for NVO and BP, but made PLTR predictions overly optimistic
4. **Analyst Ratings**: Provided context but didn't significantly improve accuracy

### Model Selection Strategy
- **DeepSeek**: Best for financial metric accuracy
- **Gemini**: Best for stock direction prediction
- **Claude**: Most balanced performance
- **GPT-3.5**: Cost-effective with good direction accuracy

## 📊 Data Sources

### Earnings Data
- Historical quarterly earnings (revenue, EPS, operating profit/margin)
- Stock price reactions (pre-earnings, 1-day, 5-day after)
- Analyst ratings from major banks (Goldman Sachs, JP Morgan, Morgan Stanley)
- **Financial Modeling Prep API**: Real-time financial data and analyst ratings

### News Data
- Recent company announcements (6-month prior to predictions)
- Strategic partnerships and contracts
- Regulatory updates and clinical trial results
- Executive changes and business developments

## 🔮 Future Enhancements

1. **Additional Sectors**: Expand to more industries
2. **Real-time Data**: Integrate live market data feeds
3. **Sentiment Analysis**: Incorporate social media sentiment
4. **Ensemble Methods**: Combine multiple LLM predictions
5. **Risk Assessment**: Add confidence intervals and risk metrics

# Data on Q2 results for PLTR Novo Nordisk and BP will be added shortly.