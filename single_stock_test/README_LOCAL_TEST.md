# Local Testing for Stock Agent System

This README provides instructions for running a test of the stock agent system on your local machine before deploying changes to AWS. This allows you to verify that your updated ReasoningAgent works correctly with the existing orchestrator and other components.

## Overview

The local test runs the stock agent system on PLTR data for 3 days to verify that all components are working correctly. The test uses the following components:

1. **ReasoningAgent** - Makes final trading decisions based on analyses from other agents
2. **WorkingOrchestrator** - Coordinates the workflow and manages the portfolio

## Prerequisites

1. Python 3.8+ with the following packages installed:
   - pandas==2.1.0
   - pandas-market-calendars==4.3.1
   - python-dotenv==1.0.0
   - openai>=1.0.0
   - requests==2.31.0
   - numpy==1.24.3

## Setup

1. Create a `.env` file with the required API keys:
   ```bash
   echo "DEEPSEEK_API_KEY=sk-c895e21f2dbd410c933b7f018910906f" > .env
   ```

## Step 1: Prepare PLTR Test Data

1. Connect to your AWS instance and copy the necessary files:
   - Copy `stock_data_90days.json` from the AWS instance to your local directory
   - Copy 3 days worth of PLTR analysis files from AWS to your local directories:
     - `valuation_reports/PLTR_valuation_analysis_*.json` (3 files)
     - `fundamental_reports/PLTR_fundamental_analysis_*.json` (3 files)
     - `sentiment_data/PLTR_sentiment_analysis_*.json` (3 files)

2. Make sure your local directory structure matches:
   ```
   single_stock_test/
   ├── stock_data_90days.json
   ├── valuation_reports/
   │   └── PLTR_valuation_analysis_*.json
   ├── fundamental_reports/
   │   └── PLTR_fundamental_analysis_*.json
   └── sentiment_data/
       └── PLTR_sentiment_analysis_*.json
   ```

## Step 2: Run the Local Test

Use the `run_local_test.py` script to run the local test:

```bash
./run_local_test.py --data-dir .
```

The script will:
1. Determine the earliest date in the downloaded data
2. Run the orchestrator for 3 days starting from that date
3. Save the results to `local_test_results.json`
4. Print a summary of the results

## Troubleshooting

If you encounter any issues:

1. **Missing data files**: Make sure the data files were downloaded correctly from the AWS instance.
2. **API errors**: Check that the API keys in the `.env` file are correct.
3. **Import errors**: Verify that all required packages are installed.
4. **Date range errors**: Make sure the date range is valid and data is available for those dates.

## Next Steps

After successfully running the local test:

1. Review the results in `local_test_results.json`
2. Check the trading decisions and portfolio performance
3. If everything looks good, deploy the updated system to AWS

## AWS Deployment Notes

When deploying to AWS, make sure to:

1. Use the same package versions as in the local environment
2. Copy the updated ReasoningAgent.py file to the AWS instance
3. Verify that the API keys are set correctly on the AWS instance
