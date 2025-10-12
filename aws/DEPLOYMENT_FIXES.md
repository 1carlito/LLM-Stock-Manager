# AWS Backtest Deployment Fixes

## Issues Fixed

### 1. Data Directory Path Issues
**Problem**: The backtest was looking for data files in the wrong location (current directory "." instead of AWS instance paths).

**Fix**: 
- Updated all agents to use configurable `data_dir` parameter (defaults to `/home/ubuntu` for AWS)
- Modified `BacktestOrchestrator` to pass data directory to all agents
- Updated output directories to use absolute paths

### 2. Date Range Configuration Issues
**Problem**: The `DateRangeIterator` had hardcoded dates and wasn't using the input parameters.

**Fix**:
- Updated `DateRangeIterator` to properly use `start_date` and `end_date` parameters
- Added command-line arguments for date range configuration
- Made the date range configurable at runtime

### 3. Date Filtering and Look-Ahead Bias
**Problem**: The backtest was using future data (look-ahead bias) and not properly filtering analysis files by date.

**Fix**:
- Implemented `_get_latest_analysis_before_date()` method that reads the `date` field from JSON files
- Only uses analysis files with dates on or before the current trading date
- Prevents look-ahead bias by ensuring historical simulation accuracy

### 4. File Pattern Matching Issues
**Problem**: Analysis file patterns weren't matching correctly and date parsing was inconsistent.

**Fix**:
- Updated file patterns to match actual analysis file naming convention
- Improved date parsing to read from JSON `date` field instead of filename
- Added better error handling for missing files

### 5. Agent Initialization Issues
**Problem**: Agents weren't receiving the data directory parameter correctly.

**Fix**:
- Updated all agent constructors to properly handle `data_dir` parameter
- Fixed output directory paths to use absolute paths
- Ensured consistent directory structure across all agents

## Files Modified

1. **backtest_orchestrator.py**
   - Fixed date range handling
   - Implemented proper data filtering
   - Added data directory support
   - Improved error handling

2. **data_utils.py**
   - Updated directory search patterns
   - Added date filtering support
   - Fixed file path handling

3. **Agent Files (ValuationAgent.py, FundamentalAgent.py, SentimentAgent.py, ReasoningAgent.py)**
   - Added data directory parameter support
   - Fixed output directory paths
   - Updated logging paths

4. **test_backtest_deployment.py**
   - Added comprehensive test script for AWS deployment
   - Tests directory structure, file loading, date filtering, and backtest execution

## Deployment Instructions

### 1. Upload Files to AWS Instance
```bash
# Copy all fixed files to AWS instance
scp -i ~/.ssh/stock-agent-key-new.pem aws/* ubuntu@YOUR_INSTANCE_IP:/home/ubuntu/
```

### 2. Test the Deployment
```bash
# SSH into instance
ssh -i ~/.ssh/stock-agent-key-new.pem ubuntu@YOUR_INSTANCE_IP

# Run the test script
cd /home/ubuntu
python3 test_backtest_deployment.py
```

### 3. Run the Backtest
```bash
# Run backtest with custom parameters
python3 backtest_orchestrator.py --data-dir /home/ubuntu --start-date 2025-06-12 --end-date 2025-06-15

# Or run with default parameters
python3 backtest_orchestrator.py
```

## Key Improvements

1. **No Look-Ahead Bias**: Only uses data available before the trading date
2. **Configurable Paths**: Works with any data directory structure
3. **Proper Date Filtering**: Uses actual dates from analysis files
4. **Better Error Handling**: Comprehensive logging and error reporting
5. **Comprehensive Testing**: Test script validates all components

## Expected Data Structure

The backtest expects the following directory structure on AWS:
```
/home/ubuntu/
├── valuation_reports/
│   ├── GOOGL_technical_analysis_20250911_204015.json
│   ├── NVDA_technical_analysis_20250911_204028.json
│   └── ...
├── fundamental_reports/
│   ├── GOOGL_fundamental_analysis_20250911_204020.json
│   ├── NVDA_fundamental_analysis_20250911_204033.json
│   └── ...
├── sentiment_data/
│   ├── GOOGL_sentiment_analysis_20250911_204023.json
│   ├── NVDA_sentiment_analysis_20250911_204037.json
│   └── ...
├── news_data/
│   └── (news files)
└── logs/
    └── (log files)
```

## Running Commands

```bash
# Test deployment
python3 test_backtest_deployment.py

# Run full backtest
python3 backtest_orchestrator.py

# Run with custom date range
python3 backtest_orchestrator.py --start-date 2025-06-12 --end-date 2025-06-20

# Monitor progress
tail -f logs/backtest_orchestrator.log
``` 