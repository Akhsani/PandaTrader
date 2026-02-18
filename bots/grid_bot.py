"""
3Commas Grid Bot Simulator — Faithful execution model.
Geometric and arithmetic modes, Trailing Up, Expansion Down.
"""
import pandas as pd
import numpy as np
from typing import Optional

from bots.base_bot import FeeEngine, compute_bot_metrics, compute_annualized_capital_return


class GridBotSimulator:
    """
    Faithful simulation of 3Commas Grid Bot.
    Supports geometric and arithmetic grid types.
    """

    def __init__(self, params: dict):
        self.upper_price = float(params["upper_price"])
        self.lower_price = float(params["lower_price"])
        self.investment_amount = float(params["investment_amount"])
        self.grid_lines_count = int(params["grid_lines_count"])
        self.grid_type = params.get("grid_type", "geometric")
        self.trailing_up = params.get("trailing_up", False)
        self.expansion_down = params.get("expansion_down", False)
        self.stop_bot_price = params.get("stop_bot_price")
        self.fee = float(params.get("fee", 0.001))
        self.slippage_bps = float(params.get("slippage_bps", 0.0))
        self.leverage = int(params.get("leverage", 1))
        self.fee_engine = FeeEngine(self.fee, slippage_bps=self.slippage_bps)

        self.levels = []
        self.closed_deals = []
        self.equity_curve = []

    def _build_grid(self) -> list:
        """Build price levels. Geometric: equal % spacing. Arithmetic: equal $ spacing."""
        if self.grid_type == "geometric":
            ratio = (self.upper_price / self.lower_price) ** (1 / self.grid_lines_count)
            levels = [self.lower_price * (ratio ** i) for i in range(self.grid_lines_count + 1)]
        else:
            step = (self.upper_price - self.lower_price) / self.grid_lines_count
            levels = [self.lower_price + step * i for i in range(self.grid_lines_count + 1)]
        return sorted(levels)

    def _profit_per_grid(self, level_low: float, level_high: float) -> float:
        """Profit per completed buy-sell cycle between two adjacent levels."""
        order_size = self.investment_amount / self.grid_lines_count
        buy_cost = order_size * (1 + self.fee)
        sell_proceeds = order_size * (level_high / level_low) * (1 - self.fee)
        return sell_proceeds - buy_cost

    def run(
        self,
        ohlcv: pd.DataFrame,
        initial_capital: Optional[float] = None,
    ) -> dict:
        """
        Simulate grid fills bar by bar.
        - Each bar: check if price crossed any grid level (up and down)
        - Profit locked on each complete buy->sell cycle
        - Trailing Up: when price closes above upper_price, extend grid upward
        - Stop: if price crosses stop_bot_price, close open buys at loss
        """
        if initial_capital is None:
            initial_capital = self.investment_amount

        self.levels = self._build_grid()
        self.closed_deals = []
        self.equity_curve = [initial_capital]

        upper = self.upper_price
        lower = self.lower_price
        order_size = self.investment_amount / self.grid_lines_count

        # Track open buy orders per grid cell: {level_idx: (buy_price, qty)}
        open_buys = {}
        total_profit = 0.0

        idx = ohlcv.index
        prev_low = ohlcv.iloc[0]["low"]
        prev_high = ohlcv.iloc[0]["high"]

        for i in range(1, len(ohlcv)):
            row = ohlcv.iloc[i]
            low = row["low"]
            high = row["high"]
            close = row["close"]

            # Stop bot
            if self.stop_bot_price is not None:
                if low <= self.stop_bot_price:
                    for k, (bp, qty, cost_usdt) in list(open_buys.items()):
                        proceeds = qty * self.stop_bot_price * (1 - self.fee)
                        loss = proceeds - cost_usdt
                        total_profit += loss
                        self.closed_deals.append({"pnl": loss / cost_usdt, "pnl_usdt": loss, "exit_reason": "stop"})
                    open_buys = {}
                    self.equity_curve.append(initial_capital + total_profit)
                    break  # Bot stops permanently after stop event (matches 3Commas behavior)

            # Trailing Up: extend upper when close > upper
            if self.trailing_up and close > upper:
                upper = close
                self.upper_price = upper
                self.levels = self._build_grid()

            # Check grid level crossings: buy at level_lo when price drops, sell at level_hi when price rises
            for j in range(len(self.levels) - 1):
                level_lo = self.levels[j]
                level_hi = self.levels[j + 1]

                # Price crossed down through level_lo -> buy at level_lo
                if prev_high >= level_lo and low <= level_lo and j not in open_buys:
                    cost_usdt = order_size * (1 + self.fee)
                    qty = order_size / level_lo
                    open_buys[j] = (level_lo, qty, cost_usdt)

                # Price crossed up through level_hi -> sell (if we have a buy at level_lo)
                if j in open_buys and prev_low <= level_hi and high >= level_hi:
                    bp, qty, cost_usdt = open_buys.pop(j)
                    proceeds = qty * level_hi * (1 - self.fee)
                    profit = proceeds - cost_usdt
                    total_profit += profit
                    self.closed_deals.append({
                        "pnl": profit / cost_usdt,
                        "pnl_usdt": profit,
                        "exit_reason": "grid",
                        "entry_time": idx[i - 1],
                        "exit_time": idx[i],
                    })

            prev_low = low
            prev_high = high
            self.equity_curve.append(initial_capital + total_profit)

        # Years elapsed for annualized return
        first_ts = idx[0]
        last_ts = idx[-1]
        if hasattr(first_ts, "to_pydatetime"):
            first_ts = first_ts.to_pydatetime()
        if hasattr(last_ts, "to_pydatetime"):
            last_ts = last_ts.to_pydatetime()
        delta = (last_ts - first_ts).total_seconds() / (365.25 * 24 * 3600)
        years_elapsed = max(delta, 0.001)
        annualized_return = compute_annualized_capital_return(
            total_profit, initial_capital, years_elapsed
        )

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
            "annualized_capital_return": annualized_return,
            "closed_deals": self.closed_deals,
            "trades_df": pd.DataFrame(self.closed_deals) if self.closed_deals else pd.DataFrame(),
        }

        exclude = {"levels", "closed_deals", "equity_curve", "fee_engine"}
        result["optimized_params"] = {
            k: v for k, v in self.__dict__.items()
            if not k.startswith("_") and k not in exclude
        }
        return result
