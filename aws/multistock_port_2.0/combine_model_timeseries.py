#!/usr/bin/env python3
"""
Combine per-day decision summaries with NAV data for a single model run.

Usage example (from inside a model directory after running the other helpers):

    python ../scripts/combine_model_timeseries.py \
        --decisions decisions_summary.csv \
        --nav backtest_nav.csv \
        --output model_timeseries.csv \
        --forward-fill

The script aligns rows by date, merges decision metadata with portfolio values,
and optionally forward-fills the NAV series. Output format defaults to CSV.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge decision summaries and NAV data into a daily timeseries."
    )
    parser.add_argument(
        "--decisions",
        type=Path,
        required=True,
        help="Path to decisions summary file (CSV or JSON).",
    )
    parser.add_argument(
        "--nav",
        type=Path,
        required=True,
        help="Path to NAV table file (CSV or JSON).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("model_timeseries.csv"),
        help="Destination file for the merged dataset (default: model_timeseries.csv).",
    )
    parser.add_argument(
        "--format",
        choices=("csv", "json"),
        default="csv",
        help="Output format (default: csv).",
    )
    parser.add_argument(
        "--forward-fill",
        action="store_true",
        help="Forward-fill missing NAV values across dates.",
    )
    return parser.parse_args(argv)


def load_table(path: Path) -> List[Dict]:
    if not path.exists():
        raise FileNotFoundError(path)

    if path.suffix.lower() == ".json":
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
            if isinstance(data, dict):
                raise ValueError(f"Expected JSON array, got object in {path}")
            return data

    # Treat as CSV by default
    with path.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return [row for row in reader]


def to_float(value) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_int(value) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def build_index(rows: List[Dict], key_field: str) -> Dict[str, Dict]:
    index: Dict[str, Dict] = {}
    for row in rows:
        key = row.get(key_field)
        if not key:
            continue
        index[key] = row
    return index


def sorted_dates(*date_sets: Sequence[str]) -> List[str]:
    unique = set()
    for seq in date_sets:
        unique.update(seq)
    return sorted(unique, key=lambda d: datetime.strptime(d, "%Y-%m-%d"))


def merge_timeseries(
    decisions_rows: List[Dict],
    nav_rows: List[Dict],
    forward_fill: bool,
) -> List[Dict]:
    decisions_index = build_index(decisions_rows, "date")
    nav_index = build_index(nav_rows, "date")

    all_dates = sorted_dates(decisions_index.keys(), nav_index.keys())
    merged: List[Dict] = []
    last_nav: Optional[float] = None

    model_ids = {row.get("model_used") for row in decisions_rows if row.get("model_used")}
    model_id = model_ids.pop() if len(model_ids) == 1 else None

    for date in all_dates:
        dec = decisions_index.get(date, {})
        nav = nav_index.get(date, {})

        # Determine model_id per row
        row_model_id = dec.get("model_used") or model_id or nav.get("model_used")

        nav_value = to_float(nav.get("portfolio_value"))
        if nav_value is not None:
            last_nav = nav_value
        elif forward_fill and last_nav is not None:
            nav_value = last_nav

        merged.append(
            {
                "date": date,
                "model_id": row_model_id,
                "portfolio_value": nav_value,
                "cash_reserved": to_float(dec.get("cash_reserved")),
                "total_allocation": to_float(dec.get("total_allocation")),
                "trades_executed": to_int(nav.get("trades_executed")),
                "trade_volume": to_float(nav.get("trade_volume")),
                "risk_assessment": dec.get("risk_assessment"),
                "strategy_notes": dec.get("strategy_notes"),
                "decision_source": dec.get("source_file"),
                "nav_source": nav.get("source_file"),
            }
        )

    return merged


def write_output(rows: List[Dict], output_path: Path, fmt: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "csv":
        if not rows:
            output_path.write_text("", encoding="utf-8")
            return
        fieldnames = list(rows[0].keys())
        with output_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    else:
        with output_path.open("w", encoding="utf-8") as fh:
            json.dump(rows, fh, indent=2, ensure_ascii=False)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)

    try:
        decisions_rows = load_table(args.decisions.resolve())
        nav_rows = load_table(args.nav.resolve())
    except Exception as exc:  # pylint: disable=broad-except
        print(f"[ERROR] Failed to load inputs: {exc}", file=sys.stderr)
        return 1

    try:
        merged_rows = merge_timeseries(decisions_rows, nav_rows, args.forward_fill)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"[ERROR] Failed to merge datasets: {exc}", file=sys.stderr)
        return 1

    write_output(merged_rows, args.output, args.format)
    print(f"Wrote {len(merged_rows)} merged rows to '{args.output}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())


