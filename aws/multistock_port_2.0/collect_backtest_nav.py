#!/usr/bin/env python3
"""
Extract per-day NAV and trade stats from a backtest summary JSON.

Typical usage from inside a model directory containing
`parallel_backtest_<run_name>_results.json`:

    python ../scripts/collect_backtest_nav.py \
        --input . \
        --output backtest_nav.csv

By default the script looks for the newest JSON file matching
`parallel_backtest*results.json`. Use `--backtest-file` to target a specific
payload. The output table contains one row per trading day with:

    - date
    - portfolio_value (last NAV recorded that day)
    - trades_executed (count of trades that day)
    - trade_volume (sum of absolute trade amounts)
    - source_file (path to the backtest JSON)

If the backtest includes a final performance summary but no trades on the last
day, the script adds a final row using the `end_date` and the reported
`performance.final_value`.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract per-day NAV from a backtest summary JSON file."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("."),
        help="Directory to search for backtest results (default: current directory).",
    )
    parser.add_argument(
        "--backtest-file",
        type=Path,
        help="Explicit path to the backtest JSON file. Overrides automatic discovery.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("backtest_nav.csv"),
        help="Output path for the per-day NAV table (default: backtest_nav.csv).",
    )
    parser.add_argument(
        "--format",
        choices=("csv", "json"),
        default="csv",
        help="Output format (default: csv).",
    )
    return parser.parse_args(argv)


def discover_backtest_file(directory: Path) -> Optional[Path]:
    candidates = sorted(directory.glob("parallel_backtest*results.json"))
    return candidates[-1] if candidates else None


def load_backtest(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def aggregate_trades(backtest: Dict) -> List[Dict]:
    trades = backtest.get("portfolio", {}).get("theoretical_trades", []) or []
    per_day_nav: Dict[str, float] = {}
    per_day_stats: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {"count": 0, "volume": 0.0}
    )

    for trade in trades:
        date = trade.get("date")
        if not date:
            continue

        nav = trade.get("portfolio_value")
        if nav is not None:
            per_day_nav[date] = float(nav)

        stats = per_day_stats[date]
        stats["count"] += 1

        raw_amount = trade.get("cost")
        if raw_amount is None:
            raw_amount = trade.get("proceeds")
        try:
            stats["volume"] += abs(float(raw_amount or 0.0))
        except (TypeError, ValueError):
            pass

    rows: List[Dict] = []
    for date in sorted(per_day_nav.keys()):
        stats = per_day_stats.get(date, {"count": 0, "volume": 0.0})
        rows.append(
            {
                "date": date,
                "portfolio_value": per_day_nav[date],
                "trades_executed": int(stats.get("count", 0)),
                "trade_volume": float(stats.get("volume", 0.0)),
            }
        )

    # Append final performance if necessary
    end_date = backtest.get("end_date")
    final_value = (
        backtest.get("performance", {}).get("final_value")
        or backtest.get("portfolio", {}).get("final_value")
    )
    if end_date and final_value is not None:
        # Only add if missing or provides newer info
        if not rows or rows[-1]["date"] != end_date:
            rows.append(
                {
                    "date": end_date,
                    "portfolio_value": float(final_value),
                    "trades_executed": 0,
                    "trade_volume": 0.0,
                }
            )
        else:
            rows[-1]["portfolio_value"] = float(final_value)

    # Ensure chronological order
    rows.sort(key=lambda row: datetime.strptime(row["date"], "%Y-%m-%d"))
    return rows


def write_output(rows: List[Dict], output_path: Path, fmt: str, source: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    augmented_rows = [
        {**row, "source_file": str(source)} for row in rows
    ]

    if fmt == "csv":
        if not augmented_rows:
            output_path.write_text("", encoding="utf-8")
            return

        fieldnames = list(augmented_rows[0].keys())

        with output_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(augmented_rows)
    else:
        with output_path.open("w", encoding="utf-8") as fh:
            json.dump(augmented_rows, fh, indent=2, ensure_ascii=False)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    search_dir = args.input.resolve()

    if not search_dir.exists():
        print(f"[ERROR] Input directory '{search_dir}' does not exist.", file=sys.stderr)
        return 1

    backtest_path = args.backtest_file.resolve() if args.backtest_file else discover_backtest_file(search_dir)
    if not backtest_path or not backtest_path.exists():
        print(
            "[ERROR] Unable to locate backtest JSON. "
            "Provide --backtest-file or ensure a file named 'parallel_backtest*results.json' exists.",
            file=sys.stderr,
        )
        return 1

    try:
        backtest_data = load_backtest(backtest_path)
        rows = aggregate_trades(backtest_data)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"[ERROR] Failed to process backtest file: {exc}", file=sys.stderr)
        return 1

    write_output(rows, args.output, args.format, backtest_path)
    print(f"Wrote {len(rows)} NAV rows to '{args.output}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())


