FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Python files
COPY backtest_orchestrator.py .
COPY FundamentalAgent.py .
COPY ReasoningAgent.py .
COPY SentimentAgent.py .
COPY ValuationAgent.py .
COPY StockData_FmpApi.py .
COPY data_utils.py .
COPY llm_news_search.py .

# Copy data directories
COPY valuation_reports/ ./valuation_reports/
COPY fundamental_reports/ ./fundamental_reports/
COPY sentiment_data/ ./sentiment_data/
COPY backtest_data_90days/ ./backtest_data_90days/

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Command to run the backtest
CMD ["python", "backtest_orchestrator.py"]
