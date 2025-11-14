#!/bin/bash
# Deploy updated agents to remote server
# Usage: ./deploy_agents.sh [remote_host_ip]

# Configuration
AWS_KEY_PATH="${AWS_KEY_PATH:-~/.ssh/stock-agent-key-new.pem}"
REMOTE_USER="${REMOTE_USER:-ubuntu}"
REMOTE_HOST="${1:-}"
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../multistock_port_2.0" && pwd)"
REMOTE_DIR="${REMOTE_DIR:-/home/ubuntu/multistock_port_2.0}"

# Check if remote host is provided
if [ -z "$REMOTE_HOST" ]; then
    echo "Usage: $0 <remote-host-ip>"
    echo "Or set REMOTE_HOST environment variable"
    exit 1
fi

# Check if SSH key exists
if [ ! -f "${AWS_KEY_PATH/#\~/$HOME}" ]; then
    echo "❌ SSH key not found at $AWS_KEY_PATH"
    echo "Please set AWS_KEY_PATH environment variable or update the script"
    exit 1
fi

echo "🚀 Deploying agents to ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}"
echo ""

# Function to deploy a file
deploy_file() {
    local file_path="$1"
    local file_name=$(basename "$file_path")
    
    if [ ! -f "$file_path" ]; then
        echo "⚠️  File not found: $file_path, skipping..."
        return 1
    fi
    
    echo "📤 Deploying $file_name..."
    rsync -avz -e "ssh -i ${AWS_KEY_PATH/#\~/$HOME}" \
        "$file_path" \
        "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo "   ✅ Successfully deployed $file_name"
    else
        echo "   ❌ Failed to deploy $file_name"
        return 1
    fi
}

# Deploy PortfolioManagerAgent.py
deploy_file "${LOCAL_DIR}/PortfolioManagerAgent.py"

# Deploy ReasoningAgent.py
deploy_file "${LOCAL_DIR}/ReasoningAgent.py"

# Deploy SentimentAgent.py
deploy_file "${LOCAL_DIR}/SentimentAgent.py"

# Deploy FundamentalAgent.py
deploy_file "${LOCAL_DIR}/FundamentalAgent.py"

# Deploy ValuationAgent.py
deploy_file "${LOCAL_DIR}/ValuationAgent.py"

# Deploy process_all_stocks.py
deploy_file "${LOCAL_DIR}/process_all_stocks.py"

# Deploy StockData_FmpApi.py (needed for data fetching)
deploy_file "${LOCAL_DIR}/StockData_FmpApi.py"

# Deploy stock_data.json (fundamental data)
deploy_file "${LOCAL_DIR}/stock_data.json"

# Deploy requirements.txt (in case dependencies changed)
if [ -f "${LOCAL_DIR}/requirements.txt" ]; then
    deploy_file "${LOCAL_DIR}/requirements.txt"
fi

# Ensure remote directories exist
echo ""
echo "📁 Creating remote directories..."
ssh -i "${AWS_KEY_PATH/#\~/$HOME}" "${REMOTE_USER}@${REMOTE_HOST}" \
    "mkdir -p ${REMOTE_DIR}/{valuation_reports,fundamental_reports,sentiment_data,news_data,logs,reasoning_decisions,portfolio_decisions}" 2>/dev/null

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Deployed agents:"
echo "   - PortfolioManagerAgent.py"
echo "   - ReasoningAgent.py"
echo "   - SentimentAgent.py"
echo "   - FundamentalAgent.py"
echo "   - ValuationAgent.py"
echo "   - process_all_stocks.py"
echo "   - StockData_FmpApi.py"
echo "   - stock_data.json"
echo ""
echo "🔗 Remote location: ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}"

