#!/usr/bin/env python3
"""
replay_portfolio_decisions.py

Replays portfolio allocations by loading previously saved reasoning decisions
and re-running the PortfolioManagerAgent to regenerate allocation choices.

This script mirrors the trade execution flow of ParallelOrchestrator so that
existing features—logging, trade application, and portfolio summaries—remain
consistent with the primary backtest pipeline.
"""

import argparse
import glob
import json
import logging
import os
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional

from PortfolioManagerAgent import PortfolioManagerAgent


class PortfolioReplay:
    """
    Reconstruct portfolio decisions by replaying stored reasoning outputs.

    Attributes:
        data_dir: Root directory containing agent artifacts.
        source_backtest: Name suffix used when the reasoning decisions were saved.
        output_backtest: Name suffix for replayed portfolio decisions.
        start_date / end_date: Optional inclusive bounds for the replay window.
        initial_cash: Starting cash balance for the reconstructed portfolio.
        logger: Structured logger aligned with ParallelOrchestrator output.
    """

    def __init__(
        self,
        data_dir: str,
        source_backtest: str,
        output_backtest: str,
        start_date: Optional[str],
        end_date: Optional[str],
        initial_cash: float,
        auto_save: bool = False,
    ) -> None:
        self.data_dir = data_dir
        self.source_backtest = source_backtest
        self.output_backtest = output_backtest
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
        self.initial_cash = initial_cash

        # Set up logging (mirrors ParallelOrchestrator)
        log_dir = os.path.join(self.data_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(os.path.join(log_dir, f"portfolio_replay_{output_backtest}.log")),
                logging.StreamHandler(),
            ],
        )
        self.logger = logging.getLogger(__name__)

        # Initialize portfolio state
        self.portfolio: Dict[str, Any] = {
            "cash": self.initial_cash,
            "positions": {},
            "last_prices": {},
            "theoretical_trades": [],
        }
        self.previous_portfolio_decisions: Deque[Dict[str, Any]] = deque(maxlen=4)

        # Initialize portfolio manager (reuse existing agent)
        self.portfolio_manager = PortfolioManagerAgent(data_dir=self.data_dir, auto_save=auto_save)
        # Ensure compatibility if PortfolioManagerAgent does not persist auto_save internally
        setattr(self.portfolio_manager, "auto_save", auto_save)

        self.logger.info("PortfolioReplay initialized")
        self.logger.info(f"- Data directory: {self.data_dir}")
        self.logger.info(f"- Source backtest tag: {self.source_backtest}")
        self.logger.info(f"- Output backtest tag: {self.output_backtest}")
        self.logger.info(f"- Initial cash: ${self.initial_cash:,.2f}")
        self.logger.info(
            f"- Date window: "
            f"{self.start_date.strftime('%Y-%m-%d') if self.start_date else 'None'} to "
            f"{self.end_date.strftime('%Y-%m-%d') if self.end_date else 'None'}"
        )

    def run(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run the replay across all available reasoning decisions (optionally filtered by symbols).
        """
        decisions_by_date = self._load_reasoning_decisions(symbols)
        if not decisions_by_date:
            self.logger.warning("No reasoning decisions found for the provided criteria.")
            return self._finalize_results(0, 0)

        trading_dates = sorted(decisions_by_date.keys())
        self.logger.info("\n" + "=" * 80)
        self.logger.info("🚀 Starting portfolio replay")
        self.logger.info("=" * 80)
        self.logger.info(f"📅 Found {len(trading_dates)} trading days to replay")

        total_decisions = 0
        total_trades = 0

        for current_date in trading_dates:
            self.logger.info("\n" + "=" * 80)
            self.logger.info(f"📅 REPLAY DAY: {current_date}")
            self.logger.info("=" * 80)

            stock_decisions = decisions_by_date[current_date]
            stock_decisions.sort(key=lambda d: d.get("symbol", ""))
            total_decisions += len(stock_decisions)

            # Update last prices from decisions (if available)
            for decision in stock_decisions:
                symbol = decision.get("symbol")
                current_price = decision.get("current_price")
                if symbol and current_price is not None:
                    self.portfolio["last_prices"][symbol] = current_price

            # Build portfolio state snapshot
            portfolio_state = {
                "cash": self.portfolio["cash"],
                "positions": self.portfolio["positions"],
                "last_prices": self.portfolio["last_prices"],
                "total_value": self._calculate_portfolio_value(),
            }

            previous_decisions_list = list(self.previous_portfolio_decisions)
            portfolio_decisions = self.portfolio_manager.make_portfolio_decisions(
                stock_decisions,
                portfolio_state,
                current_date,
                previous_portfolio_decisions=previous_decisions_list,
            )

            # Log decisions
            self.logger.info("\n💰 Portfolio Manager Decisions:")
            for pd in portfolio_decisions.get("portfolio_decisions", []):
                symbol = pd.get("symbol")
                action = pd.get("action")
                amount = pd.get("amount_usd", 0)
                target = pd.get("portfolio_weight_target", 0)
                self.logger.info(
                    f"  {symbol}: {action} ${amount:,.0f} (target: {target:.1f}%)"
                )

            summary = portfolio_decisions.get("portfolio_summary", {})
            self.logger.info("\n📈 Portfolio Summary:")
            self.logger.info(f"  Total Allocation: ${summary.get('total_allocation', 0):,.2f}")
            self.logger.info(f"  Cash Reserved: ${summary.get('cash_reserved', 0):,.2f}")
            self.logger.info(f"  Risk Assessment: {summary.get('risk_assessment', 'N/A')}")

            # Execute trades and record results
            trades_executed = self._execute_portfolio_trades(portfolio_decisions, current_date)
            total_trades += trades_executed

            # Persist portfolio decision with replay tag
            self._save_portfolio_decision(portfolio_decisions, current_date)
            self.previous_portfolio_decisions.append(portfolio_decisions)

            # Log portfolio value after execution
            portfolio_value = self._calculate_portfolio_value()
            self.logger.info(f"\n💼 Portfolio Value: ${portfolio_value:,.2f}")

        return self._finalize_results(total_decisions, total_trades)

    def _load_reasoning_decisions(
        self, symbols: Optional[List[str]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Load reasoning decisions from disk and group them by trading date.
        """
        decisions_dir = os.path.join(self.data_dir, "reasoning_decisions_Grok")
        if not os.path.exists(decisions_dir):
            self.logger.error(f"Reasoning decisions directory not found: {decisions_dir}")
            return {}

        symbol_filters = set(symbols) if symbols else None
        pattern = os.path.join(decisions_dir, f"*_{self.source_backtest}.json")
        decisions_by_date: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for filepath in glob.glob(pattern):
            try:
                with open(filepath, "r") as fp:
                    decision = json.load(fp)
            except Exception as exc:
                self.logger.error(f"Failed to load reasoning decision {filepath}: {exc}")
                continue

            symbol = decision.get("symbol")
            decision_date = decision.get("date")
            if not symbol or not decision_date:
                continue

            if symbol_filters and symbol not in symbol_filters:
                continue

            try:
                decision_dt = datetime.strptime(decision_date, "%Y-%m-%d")
            except ValueError:
                self.logger.warning(f"Skipping decision with invalid date format: {filepath}")
                continue

            if self.start_date and decision_dt < self.start_date:
                continue
            if self.end_date and decision_dt > self.end_date:
                continue

            decisions_by_date[decision_date].append(decision)

        self.logger.info(
            f"Loaded reasoning decisions for {len(decisions_by_date)} trading days "
            f"from {decisions_dir}"
        )
        return decisions_by_date

    def _execute_portfolio_trades(self, portfolio_decisions: Dict[str, Any], current_date: str) -> int:
        """
        Execute trades based on portfolio manager output (mirrors ParallelOrchestrator logic).
        """
        trades_executed = 0

        for decision in portfolio_decisions.get("portfolio_decisions", []):
            symbol = decision.get("symbol")
            action = decision.get("action")
            amount_usd = decision.get("amount_usd", 0)
            reasoning = decision.get("reasoning", "")

            if action == "BUY" and amount_usd > 0:
                current_price = self.portfolio["last_prices"].get(symbol, 100.0)
                shares = int(amount_usd / current_price)
                cost = shares * current_price

                if shares <= 0:
                    self.logger.warning(f"Skipping BUY for {symbol}: allocation too small for a single share")
                    continue

                if cost <= self.portfolio["cash"]:
                    if symbol not in self.portfolio["positions"]:
                        self.portfolio["positions"][symbol] = {"shares": 0, "avg_price": 0}

                    old_shares = self.portfolio["positions"][symbol]["shares"]
                    old_avg = self.portfolio["positions"][symbol].get("avg_price", 0)
                    new_shares = old_shares + shares
                    new_avg = (
                        ((old_shares * old_avg) + (shares * current_price)) / new_shares
                        if new_shares > 0
                        else current_price
                    )

                    self.portfolio["positions"][symbol]["shares"] = new_shares
                    self.portfolio["positions"][symbol]["avg_price"] = new_avg
                    self.portfolio["cash"] -= cost

                    trade_record = {
                        "date": current_date,
                        "symbol": symbol,
                        "action": "BUY",
                        "shares": shares,
                        "price": current_price,
                        "cost": cost,
                        "reasoning": reasoning,
                        "portfolio_value": self._calculate_portfolio_value(),
                    }
                    self.portfolio["theoretical_trades"].append(trade_record)
                    trades_executed += 1
                    self.logger.info(
                        f"✅ BUY {symbol}: {shares} shares @ ${current_price:.2f} = ${cost:,.2f}"
                    )
                else:
                    self.logger.warning(
                        f"❌ BUY {symbol}: Insufficient cash (need ${cost:,.2f}, have ${self.portfolio['cash']:,.2f})"
                    )

            elif action == "SELL":
                position = self.portfolio["positions"].get(symbol)
                if position and position.get("shares", 0) > 0:
                    shares = position["shares"]
                    current_price = self.portfolio["last_prices"].get(symbol, position.get("avg_price", 0))
                    proceeds = shares * current_price

                    self.portfolio["cash"] += proceeds
                    self.portfolio["positions"][symbol]["shares"] = 0

                    trade_record = {
                        "date": current_date,
                        "symbol": symbol,
                        "action": "SELL",
                        "shares": shares,
                        "price": current_price,
                        "proceeds": proceeds,
                        "reasoning": reasoning,
                        "portfolio_value": self._calculate_portfolio_value(),
                    }
                    self.portfolio["theoretical_trades"].append(trade_record)
                    trades_executed += 1
                    self.logger.info(
                        f"✅ SELL {symbol}: {shares} shares @ ${current_price:.2f} = ${proceeds:,.2f}"
                    )
                else:
                    self.logger.warning(f"❌ SELL {symbol}: No position to sell")

        return trades_executed

    def _calculate_portfolio_value(self) -> float:
        """
        Calculate total portfolio value using current cash and last known prices.
        """
        total_value = self.portfolio["cash"]
        for symbol, pos in self.portfolio["positions"].items():
            shares = pos.get("shares", 0)
            if shares > 0:
                current_price = self.portfolio["last_prices"].get(symbol, pos.get("avg_price", 0))
                total_value += shares * current_price
        return total_value

    def _save_portfolio_decision(self, portfolio_decisions: Dict[str, Any], current_date: str) -> None:
        """
        Save replayed portfolio decisions to disk for future context.
        """
        try:
            decisions_dir = os.path.join(self.data_dir, "portfolio_decisions_Grok")
            os.makedirs(decisions_dir, exist_ok=True)

            filename = f"portfolio_decision_{current_date}_{self.output_backtest}.json"
            filepath = os.path.join(decisions_dir, filename)

            with open(filepath, "w") as fp:
                json.dump(portfolio_decisions, fp, indent=2, default=str)
        except Exception as exc:
            self.logger.error(f"Error saving replay portfolio decision: {exc}")

    def _finalize_results(self, total_decisions: int, total_trades: int) -> Dict[str, Any]:
        """
        Compile final replay statistics and log summary output.
        """
        final_value = self._calculate_portfolio_value()
        total_return = final_value - self.initial_cash
        percent_return = (total_return / self.initial_cash * 100) if self.initial_cash > 0 else 0

        self.logger.info("\n" + "=" * 80)
        self.logger.info("🎉 PORTFOLIO REPLAY COMPLETE!")
        self.logger.info("=" * 80)
        self.logger.info(f"📊 Total decisions processed: {total_decisions}")
        self.logger.info(f"💰 Total trades executed: {total_trades}")
        self.logger.info("\n📈 PORTFOLIO PERFORMANCE:")
        self.logger.info(f"  Starting value: ${self.initial_cash:,.2f}")
        self.logger.info(f"  Final value: ${final_value:,.2f}")
        self.logger.info(f"  Total return: ${total_return:,.2f} ({percent_return:.2f}%)")
        self.logger.info("\n💼 Final positions:")
        for symbol, position in self.portfolio["positions"].items():
            shares = position.get("shares", 0)
            if shares > 0:
                current_price = self.portfolio["last_prices"].get(symbol, position.get("avg_price", 0))
                value = shares * current_price
                pct = (value / final_value * 100) if final_value > 0 else 0
                self.logger.info(
                    f"  {symbol}: {shares} shares @ ${current_price:.2f} "
                    f"= ${value:,.2f} ({pct:.1f}%)"
                )
        self.logger.info(f"  Cash: ${self.portfolio['cash']:,.2f} "
                         f"({(self.portfolio['cash'] / final_value * 100) if final_value > 0 else 0:.1f}%)")

        return {
            "start_date": self.start_date.strftime("%Y-%m-%d") if self.start_date else None,
            "end_date": self.end_date.strftime("%Y-%m-%d") if self.end_date else None,
            "decisions_made": total_decisions,
            "trades_executed": total_trades,
            "portfolio": self.portfolio,
            "performance": {
                "initial_value": self.initial_cash,
                "final_value": final_value,
                "total_return": total_return,
                "percent_return": percent_return,
            },
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replay portfolio allocations using stored reasoning decisions."
    )
    parser.add_argument(
        "--data-dir",
        default=os.path.dirname(os.path.abspath(__file__)),
        help="Root data directory (defaults to script directory).",
    )
    parser.add_argument(
        "--source-backtest",
        default="parallel",
        help="Name suffix of the reasoning decisions to replay (defaults to 'parallel').",
    )
    parser.add_argument(
        "--output-backtest",
        default="replay",
        help="Name suffix to tag replayed portfolio decisions (defaults to 'replay').",
    )
    parser.add_argument("--start-date", help="Optional start date (YYYY-MM-DD).")
    parser.add_argument("--end-date", help="Optional end date (YYYY-MM-DD).")
    parser.add_argument(
        "--symbols",
        default=None,
        help="Optional comma-separated list of symbols to include in the replay.",
    )
    parser.add_argument(
        "--initial-cash",
        type=float,
        default=1_000_000,
        help="Initial cash balance for replay (defaults to $1,000,000).",
    )
    parser.add_argument(
        "--auto-save",
        action="store_true",
        help="Enable PortfolioManagerAgent auto-save while replaying decisions.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    symbols = [s.strip() for s in args.symbols.split(",")] if args.symbols else None

    replay = PortfolioReplay(
        data_dir=args.data_dir,
        source_backtest=args.source_backtest,
        output_backtest=args.output_backtest,
        start_date=args.start_date,
        end_date=args.end_date,
        initial_cash=args.initial_cash,
        auto_save=args.auto_save,
    )

    results = replay.run(symbols=symbols)

    results_file = os.path.join(
        args.data_dir, f"portfolio_replay_{args.output_backtest}_results.json"
    )
    with open(results_file, "w") as fp:
        json.dump(results, fp, indent=2, default=str)

    print("\n✅ Replay complete!")
    print(f"📁 Results saved to {results_file}")
    if results["start_date"] or results["end_date"]:
        print(f"📅 Date window: {results['start_date']} to {results['end_date']}")
    print(f"📊 Decisions processed: {results['decisions_made']}")
    print(f"💰 Trades executed: {results['trades_executed']}")
    print(f"🏁 Final portfolio value: ${results['performance']['final_value']:,.2f}")


if __name__ == "__main__":
    main()

