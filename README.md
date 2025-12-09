# Stock Agent Eval








<img width="1139" height="770" alt="Screenshot 2025-11-14 at 14 47 57" src="https://github.com/user-attachments/assets/c60d6b6d-88d9-406d-ab7e-ad7232d62794" />














Multi-agent trading research sandbox: Sentiment, Fundamental, and Valuation feed a Reasoning Agent; a Portfolio Manager allocates with risk/execution plugins; an orchestrator runs day-by-day backtests.

- **Agents:** Sentiment (curated historic news), Fundamental, Valuation → Reasoning → Portfolio Manager → Execution/Risk.
- **Data:** `aws/quant_data/` prices, `aws/sentiment_files/` hand-collected news sentiment, `fundamental_test_reports/` fundamentals.
- **Results/updates:** X / Twitter — [@Carlos_O_B1](https://x.com/Carlos_O_B1).

## Repo Map
- `aws/multistock_port_2.0/`: Backtest orchestrator, agents, helpers, system design README.
- `aws/quant_data/`: Historical price data.
- `aws/sentiment_files/`: Curated news sentiment dataset.
- `aws/deployment/`, `aws/scripts/`: Deployment and setup utilities.

## Run Logic
python3 -m venv venv
source venv/bin/activate
pip install -r aws/requirements.txt## Run a Backtest (example)
cd aws/Mid_cap
python ParallelOrchestrator.py --start_date 2025-07-01 --end_date 2025-11-14 Process all stocks with all three analysis agents:
python process_all_stocks_all_agents.py --data_dir .. --start_date 2025-07-01 --end_date 2025-11-14## Notes
- Sentiment uses manually collected news to avoid low-quality historical endpoints.
- Allocation, spread/fee logic, and constraints live with the Portfolio Manager and Orchestrator (`aws/Mid_cap`).
- Research code—validate before production use.
