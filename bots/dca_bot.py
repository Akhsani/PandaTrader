"""
3Commas DCA Bot Simulator — Faithful execution model.
Parameter names match 3Commas API for direct export.
"""
import pandas as pd
import numpy as np
from typing import Optional

from bots.base_bot import FeeEngine, compute_bot_metrics


class DCABotSimulator:
    """
    Faithful simulation of 3Commas DCA Bot logic.
    All parameter names match 3Commas API exactly for direct export.
    """

    def __init__(self, params: dict):
        # --- Entry ---
        self.base_order_volume = float(params["base_order_volume"])
        self.safety_order_volume = float(params["safety_order_volume"])
        self.max_safety_orders = int(params["max_safety_orders"])
        self.safety_order_step_percentage = float(params["safety_order_step_percentage"])
        self.martingale_volume_coefficient = float(params["martingale_volume_coefficient"])
        self.martingale_step_coefficient = float(params["martingale_step_coefficient"])
        # --- Exit ---
        self.take_profit_percentage = float(params["take_profit_percentage"])
        self.trailing_take_profit = params.get("trailing_take_profit", False)
        self.trailing_take_profit_deviation = float(params.get("trailing_take_profit_deviation", 0.5))
        self.stop_loss_percentage = params.get("stop_loss_percentage")
        # --- Deal management ---
        self.max_active_deals = int(params.get("max_active_deals", 1))
        self.cooldown_between_deals = int(params.get("cooldown_between_deals", 0))
        # --- Fees ---
        self.fee = float(params.get("fee", 0.001))
        self.slippage_bps = float(params.get("slippage_bps", 0.0))
        self.fee_engine = FeeEngine(self.fee, slippage_bps=self.slippage_bps)
        # --- State ---
        self.active_deals = []
        self.closed_deals = []
        self.equity_curve = []

    def _calculate_so_levels(self, entry_price: float) -> list:
        """Pre-compute all safety order trigger prices and sizes."""
        levels = []
        deviation = self.safety_order_step_percentage / 100
        size = self.safety_order_volume
        cumulative_deviation = 0
        for i in range(self.max_safety_orders):
            cumulative_deviation += deviation * (self.martingale_step_coefficient ** i)
            trigger = entry_price * (1 - cumulative_deviation)
            levels.append({"trigger": trigger, "size": size, "index": i})
            size *= self.martingale_volume_coefficient
        return levels

    def _calculate_tp_price(self, avg_price: float) -> float:
        """Take profit price from average entry."""
        return avg_price * (1 + self.take_profit_percentage / 100)

    def run(
        self,
        ohlcv: pd.DataFrame,
        signal_series: Optional[pd.Series] = None,
        initial_capital: float = 10000.0,
    ) -> dict:
        """
        Run DCA simulation over OHLCV data.
        ohlcv: DataFrame with columns [open, high, low, close, volume]
        signal_series: boolean Series aligned to ohlcv index (True = open new deal).
                       If None, no new deals are opened (for testing existing deals).
        Returns: performance metrics dict with optimized_params for export.
        """
        self.active_deals = []
        self.closed_deals = []
        self.equity_curve = [initial_capital]

        if signal_series is None:
            signal_series = pd.Series(False, index=ohlcv.index)

        # Align signal to ohlcv
        signal_series = signal_series.reindex(ohlcv.index, fill_value=False).fillna(False)

        last_close_time = None
        idx = ohlcv.index

        for i in range(1, len(ohlcv)):
            ts = idx[i]
            row = ohlcv.iloc[i]
            prev_row = ohlcv.iloc[i - 1]
            open_price = row["open"]  # Limit orders fill at next-candle open
            high = row["high"]
            low = row["low"]
            close = row["close"]

            # Convert timestamp for cooldown (seconds)
            if hasattr(ts, "to_pydatetime"):
                ts_sec = ts.to_pydatetime().timestamp()
            else:
                ts_sec = pd.Timestamp(ts).timestamp()

            # --- Process active deals (SO triggers, TP, SL, trailing) ---
            still_active = []
            for deal in self.active_deals:
                entry_price = deal["entry_price"]
                filled_usdt = deal["filled_usdt"]
                filled_qty = deal["filled_qty"]
                so_levels = deal["so_levels"]
                so_filled = deal.get("so_filled", 0)
                trailing_high = deal.get("trailing_high")

                avg_price = filled_usdt / filled_qty if filled_qty > 0 else entry_price

                # SO triggers: check candle LOW (conservative)
                for j, level in enumerate(so_levels):
                    if j < so_filled:
                        continue
                    if low <= level["trigger"]:
                        so_usdt = level["size"]
                        so_qty = so_usdt / level["trigger"]
                        cost = self.fee_engine.apply_buy_fee(so_usdt)
                        filled_usdt += cost
                        filled_qty += so_qty
                        so_filled = j + 1
                        break

                avg_price = filled_usdt / filled_qty if filled_qty > 0 else entry_price
                tp_price = self._calculate_tp_price(avg_price)

                # Stop loss
                if self.stop_loss_percentage is not None:
                    sl_price = avg_price * (1 - self.stop_loss_percentage / 100)
                    if low <= sl_price:
                        exit_price = sl_price
                        pnl_pct = (exit_price - avg_price) / avg_price
                        proceeds = filled_qty * exit_price * (1 - self.fee)
                        pnl = proceeds - filled_usdt
                        self.closed_deals.append({
                            "entry_time": deal["entry_time"],
                            "exit_time": ts,
                            "pnl": pnl / filled_usdt,
                            "pnl_usdt": pnl,
                            "exit_reason": "stop_loss",
                        })
                        last_close_time = ts_sec
                        continue

                # Take profit: check candle HIGH
                if self.trailing_take_profit and trailing_high is not None:
                    # Trailing: close on reversal (price drops by deviation from highest high)
                    rev_trigger = trailing_high * (1 - self.trailing_take_profit_deviation / 100)
                    if low <= rev_trigger:
                        exit_price = rev_trigger
                        pnl_pct = (exit_price - avg_price) / avg_price
                        proceeds = filled_qty * exit_price * (1 - self.fee)
                        pnl = proceeds - filled_usdt
                        self.closed_deals.append({
                            "entry_time": deal["entry_time"],
                            "exit_time": ts,
                            "pnl": pnl / filled_usdt,
                            "pnl_usdt": pnl,
                            "exit_reason": "trailing_tp",
                        })
                        last_close_time = ts_sec
                        continue
                    # Update trailing high
                    if high > trailing_high:
                        deal["trailing_high"] = high
                    still_active.append(deal)
                    continue

                if high >= tp_price:
                    if self.trailing_take_profit:
                        deal["trailing_high"] = high
                        still_active.append(deal)
                        continue
                    # Simple TP hit
                    exit_price = tp_price
                    proceeds = filled_qty * exit_price * (1 - self.fee)
                    pnl = proceeds - filled_usdt
                    self.closed_deals.append({
                        "entry_time": deal["entry_time"],
                        "exit_time": ts,
                        "pnl": pnl / filled_usdt,
                        "pnl_usdt": pnl,
                        "exit_reason": "take_profit",
                    })
                    last_close_time = ts_sec
                    continue

                deal["filled_usdt"] = filled_usdt
                deal["filled_qty"] = filled_qty
                deal["so_filled"] = so_filled
                still_active.append(deal)

            self.active_deals = still_active

            # --- Open new deal if signal and cooldown passed ---
            if signal_series.iloc[i] and len(self.active_deals) < self.max_active_deals:
                if self.cooldown_between_deals > 0 and last_close_time is not None:
                    if ts_sec - last_close_time < self.cooldown_between_deals:
                        pass  # Skip, still in cooldown
                    else:
                        self._open_deal(ts, open_price)
                else:
                    self._open_deal(ts, open_price)

            # Equity curve (simplified: initial + sum of closed pnl)
            total_pnl = sum(d["pnl_usdt"] for d in self.closed_deals)
            open_exposure = sum(
                d["filled_usdt"] for d in self.active_deals
            )
            eq = initial_capital + total_pnl  # Simplified: ignore open exposure for curve
            self.equity_curve.append(eq)

        # Final equity
        total_pnl = sum(d["pnl_usdt"] for d in self.closed_deals)
        self.equity_curve.append(initial_capital + total_pnl)

        # Metrics
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
            "expected_value_per_deal": metrics["expected_value_per_deal"],
            "closed_deals": self.closed_deals,
            "trades_df": pd.DataFrame(self.closed_deals) if self.closed_deals else pd.DataFrame(),
        }

        # Export-ready params
        exclude = {"active_deals", "closed_deals", "equity_curve", "fee_engine"}
        result["optimized_params"] = {
            k: v for k, v in self.__dict__.items()
            if not k.startswith("_") and k not in exclude
        }
        return result

    def _open_deal(self, ts, open_price: float):
        """Open a new deal at open_price (limit fill at next candle open)."""
        cost = self.fee_engine.apply_buy_fee(self.base_order_volume)
        qty = self.base_order_volume / open_price
        so_levels = self._calculate_so_levels(open_price)
        deal = {
            "entry_time": ts,
            "entry_price": open_price,
            "filled_usdt": cost,
            "filled_qty": qty,
            "so_levels": so_levels,
            "so_filled": 0,
            "trailing_high": None,
        }
        self.active_deals.append(deal)
