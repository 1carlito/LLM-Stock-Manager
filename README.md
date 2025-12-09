
<img width="618" height="90" alt="Screenshot 2025-12-09 at 14 06 35" src="https://github.com/user-attachments/assets/a2b0a55f-ba02-454e-9fa6-dc46ff25c5f3" />










<img width="1098" height="758" alt="Screenshot 2025-12-09 at 13 57 07" src="https://github.com/user-attachments/assets/a7705a65-b685-4902-bfe9-dad713f109df" />














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
