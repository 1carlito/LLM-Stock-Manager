import os
from datetime import datetime
from typing import List

from StockData_FmpApi import StockDataFmpApi

OUTPUT_DIR = "/Users/pc/stock_agent_eval/stock_agent_eval_clean/aws/Mid_Cap"

TICKERS: List[str] = [
	"HAG.DE", "AKAM",
]


def ensure_output_dir(path: str) -> None:
	os.makedirs(path, exist_ok=True)


def main():
	from_date = "2025-07-01"
	to_date = "2025-11-01"

	api_key = os.getenv("FMP_API_KEY")
	if not api_key:
		raise EnvironmentError("FMP_API_KEY environment variable not set.")

	tickers = [t for t in TICKERS if t]
	print(f"Using {len(tickers)} tickers: {', '.join(tickers)}")

	client = StockDataFmpApi(api_key)
	data = client.fetch_batch_stock_data(
		symbols=tickers,
		historical_days=240,
		from_date=from_date,
		to_date=to_date,
		delay=0.5,
	)

	# Decide merge target: pick latest existing mid_cap json for this date window if present
	ensure_output_dir(OUTPUT_DIR)
	prefix = f"mid_cap_stock_data_{from_date.replace('-', '')}_{to_date.replace('-', '')}_"
	candidates = [
		fn for fn in os.listdir(OUTPUT_DIR)
		if fn.startswith(prefix) and fn.endswith(".json")
	]
	if candidates:
		latest = max(candidates, key=lambda fn: os.path.getmtime(os.path.join(OUTPUT_DIR, fn)))
		output_path = os.path.join(OUTPUT_DIR, latest)
		# Load existing and merge
		try:
			import json
			with open(output_path, "r") as f:
				existing = json.load(f)
		except Exception:
			existing = {}
		merged = dict(existing)
		for symbol, stock_data in data.items():
			merged[symbol] = stock_data.to_dict()
		with open(output_path, "w") as f:
			json.dump(merged, f, indent=2)
		print(f"Merged {len(data)} symbols into existing file: {output_path}")
	else:
		# Create a new timestamped file
		timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		output_path = os.path.join(
			OUTPUT_DIR, f"mid_cap_stock_data_{from_date.replace('-', '')}_{to_date.replace('-', '')}_{timestamp}.json"
		)
		# Serialize fresh data
		import json
		serialized = {sym: sd.to_dict() for sym, sd in data.items()}
		with open(output_path, "w") as f:
			json.dump(serialized, f, indent=2)
		print(f"Saved new stock data file: {output_path}")


if __name__ == "__main__":
	main()


