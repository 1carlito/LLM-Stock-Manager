#!/bin/bash

# Create deployment directory structure
mkdir -p aws/deployment/{valuation_reports,fundamental_reports,sentiment_data,news_data,backtest_data_90days}

# Copy Python files
cp aws/*.py aws/deployment/

# Copy data directories
cp -r aws/valuation_reports/* aws/deployment/valuation_reports/
cp -r aws/fundamental_reports/* aws/deployment/fundamental_reports/
cp -r aws/sentiment_data/* aws/deployment/sentiment_data/
cp -r aws/news_data/* aws/deployment/news_data/
cp -r backtest_data_90days/* aws/deployment/backtest_data_90days/

# Make sure requirements.txt is up to date
cp aws/requirements.txt aws/deployment/

echo "Deployment files prepared successfully!" 