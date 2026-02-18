"""
3Commas Signal Bot Simulator — TV-style signal consumption.
Single entry, TP/SL, optional trailing stop.
"""
import pandas as pd
import numpy as np
from typing import Optional

from bots.base_bot import FeeEngine, compute_bot_metrics


class SignalBotSimulator:
    """
    Simulates Signal Bot: entry on signal, exit on TP/SL or trailing.
    """

    def __init__(self, params: dict):
        self.position_size = float(params.get("position_size", 100))
        self.take_profit_percentage = float(params.get("take_profit_percentage", 2.0))
        self.stop_loss_percentage = float(params.get("stop_loss_percentage", 2.0))
        self.trailing_stop_loss = params.get("trailing_stop_loss", False)
        self.trailing_stop_loss_percentage = float(params.get("trailing_stop_loss_percentage", 1.0))
        self.fee = float(params.get("fee", 0.001))
        self.slippage_bps = float(params.get("slippage_bps", 0.0))
        self.fee_engine = FeeEngine(self.fee, slippage_bps=self.slippage_bps)

        self.closed_deals = []
        self.equity_curve = []

    def run(
        self,
        ohlcv: pd.DataFrame,
        signal_series: Optional[pd.Series] = None,
        initial_capital: float = 10000.0,
    ) -> dict:
        """
        Run signal bot simulation.
        signal_series: True = enter long at next candle open.
        """
        self.closed_deals = []
        self.equity_curve = [initial_capital]

        if signal_series is None:
            signal_series = pd.Series(False, index=ohlcv.index)
        signal_series = signal_series.reindex(ohlcv.index, fill_value=False).fillna(False)

        position = None
        total_pnl = 0.0
        idx = ohlcv.index

        for i in range(1, len(ohlcv)):
            row = ohlcv.iloc[i]
            open_price = row["open"]
            high = row["high"]
            low = row["low"]

            # Exit logic
            if position is not None:
                entry_price = position["entry_price"]
                qty = position["qty"]
                trailing_high = position.get("trailing_high")

                # SL
                sl_price = entry_price * (1 - self.stop_loss_percentage / 100)
                if low <= sl_price:
                    exit_price = sl_price
                    proceeds = qty * exit_price * (1 - self.fee)
                    cost = position["cost_usdt"]
                    pnl = proceeds - cost
                    total_pnl += pnl
                    self.closed_deals.append({
                        "pnl": pnl / cost,
                        "pnl_usdt": pnl,
                        "entry_time": position["entry_time"],
                        "exit_time": idx[i],
                        "exit_reason": "stop_loss",
                    })
                    position = None
                    self.equity_curve.append(initial_capital + total_pnl)
                    continue

                # Trailing stop
                if self.trailing_stop_loss and trailing_high is not None:
                    rev = trailing_high * (1 - self.trailing_stop_loss_percentage / 100)
                    if low <= rev:
                        exit_price = rev
                        proceeds = qty * exit_price * (1 - self.fee)
                        cost = position["cost_usdt"]
                        pnl = proceeds - cost
                        total_pnl += pnl
                        self.closed_deals.append({
                            "pnl": pnl / cost,
                            "pnl_usdt": pnl,
                            "entry_time": position["entry_time"],
                            "exit_time": idx[i],
                            "exit_reason": "trailing_stop",
                        })
                        position = None
                        self.equity_curve.append(initial_capital + total_pnl)
                        continue

                # TP
                tp_price = entry_price * (1 + self.take_profit_percentage / 100)
                if high >= tp_price:
                    exit_price = tp_price
                    proceeds = qty * exit_price * (1 - self.fee)
                    cost = position["cost_usdt"]
                    pnl = proceeds - cost
                    total_pnl += pnl
                    self.closed_deals.append({
                        "pnl": pnl / cost,
                        "pnl_usdt": pnl,
                        "entry_time": position["entry_time"],
                        "exit_time": idx[i],
                        "exit_reason": "take_profit",
                    })
                    position = None
                    self.equity_curve.append(initial_capital + total_pnl)
                    continue

                # Update trailing high
                if self.trailing_stop_loss:
                    position["trailing_high"] = max(trailing_high or high, high)

            # Entry logic
            if position is None and signal_series.iloc[i]:
                cost = self.fee_engine.apply_buy_fee(self.position_size)
                qty = self.position_size / open_price
                position = {
                    "entry_time": idx[i],
                    "entry_price": open_price,
                    "qty": qty,
                    "cost_usdt": cost,
                    "trailing_high": None,
                }

            self.equity_curve.append(initial_capital + total_pnl)

        self.equity_curve.append(initial_capital + total_pnl)

        metrics = compute_bot_metrics(
            self.closed_deals,
            self.equity_curve,
            initial_capital,
            annual_factor=365 * 24,
        )

        result = {
            "total_profit_pct": metrics["total_return_pct"],
            "max_drawdown": metrics["max_drawdown_pct"],
            "sharpe_ratio": metrics["sharpe_ratio"],
            "win_rate": metrics["win_rate"],
            "total_deals": metrics["total_deals"],
            "avg_deal_duration_hours": metrics["avg_deal_duration_hours"],
            "max_capital_deployed": metrics["max_capital_deployed"],
            "closed_deals": self.closed_deals,
            "trades_df": pd.DataFrame(self.closed_deals) if self.closed_deals else pd.DataFrame(),
        }

        exclude = {"closed_deals", "equity_curve", "fee_engine"}
        result["optimized_params"] = {
            k: v for k, v in self.__dict__.items()
            if not k.startswith("_") and k not in exclude
        }
        return result
