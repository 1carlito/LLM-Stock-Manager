System Design Summary: Sub-Agents → Reasoning
Overview

# Sentiment Agent
Model: Deepseek V3.1.
Data: Your manually collected historic news (sentiment_files/stock_news + sentiment_files/general_market_news); ensures coverage where public endpoints were weak.
Process: Gathers stock-specific and general market news for the date; builds a sentiment prompt; returns sentiment summary and confidence (0–100).
Output: Sentiment JSON per symbol/date used directly in the Reasoning prompt. No portfolio context.


# Fundamental Agent
Model: DeepSeek V3.1 (via Chutes).
Lookback & refresh: Regenerates every day; caches but refreshes PE/PB daily. Pulls up to 4 prior fundamental analyses (latest before current date) for context.
Data & ratios:
Current price: From dedicated historical price file if provided; otherwise stock_data historical_prices, using the closest price on/before the target date.
P/E: current_price / TTM EPS; TTM EPS = sum of last 4 quarterly EPS (or annual EPS if present).
P/B: current_price / latest book value per share from the most recent balance sheet.
Output: Recommendation (BUY/HOLD/SELL), confidence (0.0–1.0), summary, PE, PB, analysis_date/target_date, plus raw LLM response.


# Valuation Agent (technical/price context)
Model: DeepSeek (via Chutes).
Lookback & history: Includes up to 3 prior valuation analyses (most recent before current date).
Price/technical calculations (from historical_prices):
Moving averages: 20/50/200 day.
Price changes: 1d, 1w, 1m, 3m, 1y (uses available history; 1y when ≥200 points).
Volatility: Std dev of daily returns, annualized (×√252).
Volume: Avg 10d, avg 30d, volume change vs. 30d avg.
Levels: Support/resistance as 20th/80th percentile of prices.
Indicators: RSI(14), MACD(12,26,9).
Current price: nearest on/before target date.
Output: Recommendation (BUY/HOLD/SELL), confidence, target_price, summary, technical indicators, analysis_date.


- All of these analyses are provided to the Reasoning agent for each stock during the backtest.
