#!/usr/bin/env python3
"""
Summarize portfolio manager decision JSON files for a single model run.

Typical usage from inside a model's `portfolio_decisions_*` directory:

    python ../scripts/collect_portfolio_decisions.py \
        --input . \
        --summary-output decisions_summary.csv \
        --details-output decisions_actions.csv

The script scans the input directory for files named `portfolio_decision*.json`,
parses each, and emits:

1. A per-day summary table (`--summary-output`) containing:
   - date
   - model_used
   - cash_reserved
   - total_allocation
   - risk_assessment
   - strategy_notes
   - source_file

2. A per-decision detail table (`--details-output`) capturing each symbol action:
   - date
   - model_used
   - symbol
   - action
   - amount_usd
   - portfolio_weight_target
   - reasoning
   - source_file

Outputs default to CSV; specify `--format json` to produce JSON arrays instead.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize portfolio decision JSON files for a model run."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("."),
        help="Directory containing portfolio_decision JSON files (default: current directory).",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("decisions_summary.csv"),
        help="Path for per-day summary output (default: decisions_summary.csv).",
    )
    parser.add_argument(
        "--details-output",
        type=Path,
        default=Path("decisions_actions.csv"),
        help="Path for per-decision detail output (default: decisions_actions.csv).",
    )
    parser.add_argument(
        "--format",
        choices=("csv", "json"),
        default="csv",
        help="Output format for both files (default: csv).",
    )
    parser.add_argument(
        "--include-fallback",
        action="store_true",
        help="Include decisions whose model_used is 'fallback'. By default these are skipped.",
    )
    return parser.parse_args(argv)


def load_decision(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    data["_source_file"] = path
    return data


def discover_decision_files(directory: Path) -> List[Path]:
    return sorted(directory.glob("portfolio_decision*.json"))


def summarize_decisions(
    decisions: Iterable[Dict], include_fallback: bool
) -> Tuple[List[Dict], List[Dict]]:
    summary_rows: List[Dict] = []
    detail_rows: List[Dict] = []

    for payload in decisions:
        model_used = payload.get("model_used")
        if not model_used:
            raise ValueError(
                f"Decision file {payload.get('_source_file')} missing 'model_used'."
            )
        if (not include_fallback) and model_used.lower() == "fallback":
            continue

        date = payload.get("date")
        if not date:
            raise ValueError(
                f"Decision file {payload.get('_source_file')} missing 'date'."
            )

        summary = payload.get("portfolio_summary", {}) or {}
        decisions_list = payload.get("portfolio_decisions", []) or []
        source_file = str(payload.get("_source_file"))

        summary_rows.append(
            {
                "date": date,
                "model_used": model_used,
                "cash_reserved": _to_float(summary.get("cash_reserved")),
                "total_allocation": _to_float(summary.get("total_allocation")),
                "risk_assessment": summary.get("risk_assessment"),
                "strategy_notes": summary.get("strategy_notes"),
                "source_file": source_file,
            }
        )

        for decision in decisions_list:
            detail_rows.append(
                {
                    "date": date,
                    "model_used": model_used,
                    "symbol": decision.get("symbol"),
                    "action": decision.get("action"),
                    "amount_usd": _to_float(decision.get("amount_usd")),
                    "portfolio_weight_target": _to_float(
                        decision.get("portfolio_weight_target")
                    ),
                    "reasoning": decision.get("reasoning"),
                    "source_file": source_file,
                }
            )

    return summary_rows, detail_rows


def _to_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def write_output(rows: List[Dict], output_path: Path, fmt: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "csv":
        if not rows:
            # Create empty file with headers if possible
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


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    input_dir = args.input.resolve()

    if not input_dir.exists():
        print(f"[ERROR] Input directory '{input_dir}' does not exist.", file=sys.stderr)
        return 1

    decision_files = discover_decision_files(input_dir)
    if not decision_files:
        print(
            f"[ERROR] No decision files found in '{input_dir}'. Expected names like 'portfolio_decision_*.json'.",
            file=sys.stderr,
        )
        return 1

    try:
        decision_payloads = [load_decision(path) for path in decision_files]
        summary_rows, detail_rows = summarize_decisions(
            decision_payloads, include_fallback=args.include_fallback
        )
    except Exception as exc:  # pylint: disable=broad-except
        print(f"[ERROR] Failed to process decisions: {exc}", file=sys.stderr)
        return 1

    if not summary_rows:
        print(
            "[WARN] No summary rows produced (possibly all files were fallback and --include-fallback was not set).",
            file=sys.stderr,
        )

    write_output(summary_rows, args.summary_output, args.format)
    write_output(detail_rows, args.details_output, args.format)

    print(
        f"Wrote {len(summary_rows)} summary rows and {len(detail_rows)} decision rows "
        f"to '{args.summary_output}' and '{args.details_output}'."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())


