
<img width="618" height="90" alt="Screenshot 2025-12-09 at 14 06 35" src="https://github.com/user-attachments/assets/a2b0a55f-ba02-454e-9fa6-dc46ff25c5f3" />










<img width="1098" height="758" alt="Screenshot 2025-12-09 at 13 57 07" src="https://github.com/user-attachments/assets/a7705a65-b685-4902-bfe9-dad713f109df" />




#Overview

This framework exists to stress-test multi-agent trading (MAS) with a simple, rigid REST API based architecture. The goal was to evaluate responses and LLM noise when analyzing financial data. Since free/cheap news APIs provide poor historic coverage, I manually scraped both general and ticker-specific news for the backtest window so the Sentiment Agent’s influence is actually present in the Reasoning Agent’s analysis.

It’s tailored to this specific 20-stock run and not packaged for easy OSS reuse. The current design surfaced considerable noise between the Reasoning Agent and Portfolio Manager; despite some insightful LLM outputs, the end-to-end behavior is suboptimal. I’m now building a new MCP-based system with tool-calling and database querying—stay tuned.!


For better understanding read these summary files explaining the framework in two parts.

  aws/Mid_Cap/SYSTEM_DESIGN_Part1.md
  
  aws/Mid_Cap/SYSTEM_DESIGN_Part2.md


- **Results/updates:** X / Twitter — [@Carlos_O_B1](https://x.com/Carlos_O_B1).

## Repo Map
- `aws/Mid_Cap`: Backtest orchestrator, agents, helpers,  Design README's.
- `aws/quant_data/`: Historical Valuation and Fundamental Data.
- `aws/sentiment_files/`: Curated news sentiment dataset.
- `aws/deployment/`, `aws/scripts/`: Deployment and setup utilities.

## Run Logic
python3 -m venv venv
source venv/bin/activate
pip install -r aws/requirements.txt## Run a Backtest (example)
cd aws/Mid_cap
python process_all_stocks_all_agents.py --data_dir .. --start_date 2025-07-01 --end_date 2025-11-14
//* outputs analysis of the 3 sub agents

python ParallelOrchestrator.py --start_date 2025-07-01 --end_date 2025-11-14 Process all stocks with all three analysis agents:
//* Runs the Reasoning Agent on the sub agent analysis, Portfolio Manager takes the Reasoning Agent analysis and allocates available funds accordingly 

