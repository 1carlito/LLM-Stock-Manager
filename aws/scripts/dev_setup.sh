#!/bin/bash

# Configuration
AWS_KEY_PATH="~/.ssh/stock-agent-key-new.pem"
REMOTE_USER="ubuntu"
REMOTE_HOST="" # Will be set from command line argument
LOCAL_PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REMOTE_PROJECT_ROOT="/home/ubuntu/stock_agent"
EXCLUDE_FILE="${LOCAL_PROJECT_ROOT}/aws/scripts/.syncignore"

# Check arguments
if [ -z "$1" ]; then
    echo "Usage: $0 <remote-host-ip>"
    exit 1
fi
REMOTE_HOST="$1"

# Create .syncignore if it doesn't exist
if [ ! -f "$EXCLUDE_FILE" ]; then
    cat > "$EXCLUDE_FILE" << EOL
.gita
.gitignore
*.pyc
__pycache__
.vscode
.idea
*.log
backtest_data_90days/
backtest_data_90days_claude/
backtest_results/
EOL
fi

# Function to sync files
sync_files() {
    # Only sync if there are changes
    rsync -avz --delete --checksum \
        --exclude-from="$EXCLUDE_FILE" \
        -e "ssh -i $AWS_KEY_PATH" \
        "${LOCAL_PROJECT_ROOT}/" \
        "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PROJECT_ROOT}/" 2>&1 | grep -v "^sending incremental file list$" | grep -v "^$"
}

# Function to watch for changes and sync
watch_and_sync() {
    echo "Watching for changes and syncing to remote..."
    while true; do
        if [ -n "$(find "${LOCAL_PROJECT_ROOT}" -type f -newer "${LOCAL_PROJECT_ROOT}/.last_sync" 2>/dev/null)" ]; then
            sync_files
            touch "${LOCAL_PROJECT_ROOT}/.last_sync"
        fi
        sleep 2
    done
}

# Setup remote directory structure
echo "Setting up remote directory structure..."
ssh -i "$AWS_KEY_PATH" "${REMOTE_USER}@${REMOTE_HOST}" "mkdir -p ${REMOTE_PROJECT_ROOT}/{valuation_reports,fundamental_reports,sentiment_data,news_data,logs}"

# Initial sync
echo "Performing initial sync..."
sync_files

# Start watching for changes
watch_and_sync 