# Data Points and Metrics Documentation

This document outlines all data categories analyzed and metrics calculated by the three sub-agents: FundamentalAgent, ValuationAgent, and SentimentAgent.

---

## FundamentalAgent

### Data Categories Analyzed

#### 1. Earnings Data
- **EPS (Earnings Per Share)**: Quarterly and annual earnings per share
- **TTM EPS (Trailing Twelve Months)**: Sum of last 4 quarters of EPS
- **Revenue**: Total revenue from income statements
- **Net Income**: Net profit/loss after all expenses

#### 2. Balance Sheet Data
- **Total Equity**: Shareholders' equity
- **Book Value Per Share**: Total equity divided by outstanding shares
- **Total Assets**: Company's total assets
- **Total Liabilities**: Company's total liabilities

#### 3. Cash Flow Data
- **Operating Cash Flow**: Cash from operations
- **Investing Cash Flow**: Cash from investments
- **Financing Cash Flow**: Cash from financing activities
- **Free Cash Flow**: Operating cash flow minus capital expenditures

#### 4. Company Profile
- **Company Name**: Official company name
- **Sector**: Business sector classification
- **Industry**: Industry classification
- **Description**: Company business description

### Metrics Calculated

#### 1. Valuation Ratios
- **P/E Ratio (Price-to-Earnings)**: `Current Price / EPS`
  - Calculated daily using latest price and TTM EPS
  - Indicates how expensive a stock is relative to earnings
  
- **P/B Ratio (Price-to-Book)**: `Current Price / Book Value Per Share`
  - Calculated daily using latest price and latest book value
  - Indicates market value relative to book value

#### 2. Financial Health Indicators
- **Profitability Metrics**: Derived from income statements
- **Growth Metrics**: Revenue and earnings growth rates
- **Liquidity Metrics**: Cash flow analysis

### Data Sources
- Income statements (quarterly/annual)
- Balance sheets (quarterly/annual)
- Cash flow statements (quarterly/annual)
- Historical price data (for P/E and P/B calculations)

---

## ValuationAgent

### Data Categories Analyzed

#### 1. Price Data
- **Close Price**: Daily closing price
- **VWAP (Volume Weighted Average Price)**: Volume-weighted average price
- **Historical Prices**: Time series of closing prices (up to 200 days)

#### 2. Volume Data
- **Daily Volume**: Trading volume per day
- **Average Volume (10-day)**: 10-day moving average of volume
- **Average Volume (30-day)**: 30-day moving average of volume

### Metrics Calculated

#### 1. Moving Averages
- **MA 20**: 20-day simple moving average
- **MA 50**: 50-day simple moving average
- **MA 200**: 200-day simple moving average

#### 2. Technical Indicators
- **RSI (14)**: Relative Strength Index (14-period)
  - Values: 0-100
  - >70: Overbought
  - <30: Oversold
  - 30-70: Neutral
  
- **MACD (12, 26, 9)**: Moving Average Convergence Divergence
  - **MACD Line**: Fast EMA (12) - Slow EMA (26)
  - **Signal Line**: 9-period EMA of MACD line
  - **Histogram**: MACD line - Signal line
  - **Is Bullish**: MACD > Signal
  - **Is Above Zero**: MACD > 0

#### 3. Price Changes
- **1-Day Change**: Percentage change from previous day
- **1-Week Change**: Percentage change from 5 days ago
- **1-Month Change**: Percentage change from 20 days ago
- **3-Month Change**: Percentage change from 60 days ago
- **1-Year Change**: Percentage change from 200 days ago (if available)

#### 4. Volume Metrics
- **Average Volume (10d)**: 10-day average trading volume
- **Average Volume (30d)**: 30-day average trading volume
- **Volume Change**: Current volume vs 30-day average (percentage)

#### 5. Technical Levels
- **Support Level**: 20th percentile of price range
- **Resistance Level**: 80th percentile of price range

#### 6. Volatility
- **Annualized Volatility**: Standard deviation of daily returns × √252
  - Measures price volatility over the analysis period

### Data Sources
- Historical price data (close, volume)
- Calculated from price time series

---

## SentimentAgent

### Data Categories Analyzed

#### 1. News Articles
- **Stock-Specific News**: News articles directly related to the stock symbol
  - Source: `sentiment_files/stock_news/{SYMBOL}_*.json`
  - Format: Articles with date, title, source, text
  
- **General Market News**: Broader market news that may affect all stocks
  - Source: `sentiment_files/general_market_news/*.json`
  - Format: Articles with date, title, source, text

#### 2. Article Metadata
- **Date**: Publication date (standardized to YYYY-MM-DD)
- **Title**: Article headline
- **Source**: News source/publication
- **Text**: Full article content

#### 3. News Trends
- **Weekly Grouping**: Articles grouped by week for trend analysis
- **Date Ranges**: Start and end dates for news periods analyzed

#### 4. Historical Sentiment
- **Previous Analyses**: Cached sentiment analyses from previous dates
- **Analysis Date**: Date when sentiment was analyzed

### Metrics Calculated

#### 1. Sentiment Scores
- **Overall Sentiment**: 
  - `POSITIVE`: Bullish sentiment
  - `NEGATIVE`: Bearish sentiment
  - `NEUTRAL`: Mixed or neutral sentiment
  
- **Confidence**: 0-100 scale
  - Higher values indicate stronger confidence in sentiment assessment
  - Based on consistency and strength of sentiment signals

#### 2. Sentiment Analysis Output
- **Summary**: Text summary of sentiment analysis
- **Key Themes**: Main topics/themes identified in news
- **Impact Assessment**: Potential impact on stock price
- **Confidence Level**: Numerical confidence score (0-100)

### Data Sources
- Stock-specific news files (JSON format)
- General market news files (JSON format)
- Historical sentiment analysis cache

---

## Summary by Agent

### FundamentalAgent
**Focus**: Financial health and valuation ratios
- **Data**: Financial statements (income, balance sheet, cash flow)
- **Metrics**: P/E ratio, P/B ratio, EPS, Book Value
- **Output**: Fundamental analysis with valuation assessment

### ValuationAgent
**Focus**: Technical analysis and price action
- **Data**: Historical price and volume data
- **Metrics**: RSI, MACD, Moving Averages, Volatility, Support/Resistance
- **Output**: Technical analysis with momentum indicators

### SentimentAgent
**Focus**: News sentiment and market psychology
- **Data**: News articles (stock-specific and general market)
- **Metrics**: Sentiment score (POSITIVE/NEGATIVE/NEUTRAL), Confidence (0-100)
- **Output**: Sentiment analysis with confidence assessment

---

## Notes

1. **Data Filtering**: All agents filter data to respect the analysis date (no look-ahead bias)
2. **Caching**: Agents cache previous analyses to avoid redundant calculations
3. **Date Standardization**: All dates are standardized to YYYY-MM-DD format
4. **Price Updates**: FundamentalAgent recalculates P/E and P/B ratios daily using current prices
5. **News Grouping**: SentimentAgent groups news by week for trend analysis
