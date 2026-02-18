
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

class MonteCarloValidator:
    def __init__(self, trades_df, initial_capital=1000):
        self.trades_df = trades_df.copy()
        self.initial_capital = initial_capital

    def run_simulation(self, n_simulations=1000, plot=False, random_state=None):
        """
        Reshuffle trades n times and calculate equity curves.
        random_state: int for reproducible results (e.g. 42).
        """
        if self.trades_df.empty:
            print("No trades to simulate.")
            return None

        pnl_pcts = self.trades_df['pnl'].values
        rng = np.random.default_rng(random_state)

        simulation_results = []
        final_equities = []
        max_drawdowns = []

        print(f"Running {n_simulations} Monte Carlo simulations...")

        for i in range(n_simulations):
            # 1. Shuffle returns
            shuffled_pnls = rng.choice(pnl_pcts, size=len(pnl_pcts), replace=True)
            
            # 2. Calculate equity curve
            # equity = start * (1+r1) * (1+r2) ...
            equity_curve = self.initial_capital * np.cumprod(1 + shuffled_pnls)
            equity_curve = np.insert(equity_curve, 0, self.initial_capital)
            
            final_equity = equity_curve[-1]
            final_equities.append(final_equity)
            
            # 3. Calculate Max Drawdown for this path
            peak = np.maximum.accumulate(equity_curve)
            drawdown = (equity_curve - peak) / peak
            max_dd = drawdown.min()
            max_drawdowns.append(max_dd)
            
            simulation_results.append(equity_curve)
            
        # Statistics
        final_equities = np.array(final_equities)
        max_drawdowns = np.array(max_drawdowns)
        
        ruin_prob = (final_equities < self.initial_capital).mean()
        dd_prob_20 = (max_drawdowns < -0.20).mean()
        var_95 = np.percentile(final_equities, 5)
        median_equity = np.median(final_equities)
        
        stats = {
            'simulations': n_simulations,
            'initial_capital': self.initial_capital,
            'median_final_equity': median_equity,
            'ruin_probability': ruin_prob,
            'prob_dd_gt_20': dd_prob_20,
            'VaR_95': var_95, # 5th percentile outcome
            'worst_case_dd': max_drawdowns.min()
        }
        
        return stats, simulation_results

    def generate_report(self, stats):
        print("\n=== Monte Carlo Simulation Results ===")
        print(f"Simulations: {stats['simulations']}")
        print(f"Start Capital: ${stats['initial_capital']}")
        print(f"Median Final Equity: ${stats['median_final_equity']:.2f}")
        print(f"Probability of Ruin (Loss): {stats['ruin_probability']:.2%}")
        print(f"Probability of Drawdown > 20%: {stats['prob_dd_gt_20']:.2%}")
        print(f"95% VaR (Worst 5% Outcome): ${stats['VaR_95']:.2f}")
        print(f"Worst Case Drawdown: {stats['worst_case_dd']:.2%}")
        print("======================================")


class MonteCarloValidatorGrid:
    """
    Grid bot Monte Carlo: additive returns.
    Each grid cell has fixed capital; equity = initial + cumsum(profit_per_trade).
    """
    def __init__(self, trades_df, initial_capital=1000, investment_amount=1000, grid_lines_count=20):
        self.trades_df = trades_df.copy()
        self.initial_capital = initial_capital
        self.capital_per_trade = investment_amount / grid_lines_count
        # trades_df['pnl'] is return fraction per cell
        self.profit_per_trade = self.trades_df['pnl'].values * self.capital_per_trade

    def run_simulation(self, n_simulations=1000, plot=False, random_state=None):
        """Reshuffle trades n times; equity = initial + cumsum(profit_usdt). random_state for reproducibility."""
        if self.trades_df.empty:
            print("No trades to simulate.")
            return None

        rng = np.random.default_rng(random_state)
        simulation_results = []
        final_equities = []
        max_drawdowns = []

        print(f"Running {n_simulations} Monte Carlo simulations (grid, additive)...")

        for i in range(n_simulations):
            shuffled_profits = rng.choice(
                self.profit_per_trade, size=len(self.profit_per_trade), replace=True
            )
            equity_curve = self.initial_capital + np.cumsum(shuffled_profits)
            equity_curve = np.insert(equity_curve, 0, self.initial_capital)

            final_equity = equity_curve[-1]
            final_equities.append(final_equity)

            peak = np.maximum.accumulate(equity_curve)
            drawdown = np.where(peak > 0, (equity_curve - peak) / peak, 0)
            max_dd = drawdown.min()
            max_drawdowns.append(max_dd)

            simulation_results.append(equity_curve)

        final_equities = np.array(final_equities)
        max_drawdowns = np.array(max_drawdowns)

        ruin_prob = (final_equities < self.initial_capital).mean()
        dd_prob_20 = (max_drawdowns < -0.20).mean()
        var_95 = np.percentile(final_equities, 5)
        median_equity = np.median(final_equities)

        stats = {
            'simulations': n_simulations,
            'initial_capital': self.initial_capital,
            'median_final_equity': median_equity,
            'ruin_probability': ruin_prob,
            'prob_dd_gt_20': dd_prob_20,
            'VaR_95': var_95,
            'worst_case_dd': max_drawdowns.min()
        }
        return stats, simulation_results

    def generate_report(self, stats):
        print("\n=== Monte Carlo Simulation Results (Grid, Additive) ===")
        print(f"Simulations: {stats['simulations']}")
        print(f"Start Capital: ${stats['initial_capital']}")
        print(f"Median Final Equity: ${stats['median_final_equity']:.2f}")
        print(f"Probability of Ruin (Loss): {stats['ruin_probability']:.2%}")
        print(f"Probability of Drawdown > 20%: {stats['prob_dd_gt_20']:.2%}")
        print(f"95% VaR (Worst 5% Outcome): ${stats['VaR_95']:.2f}")
        print(f"Worst Case Drawdown: {stats['worst_case_dd']:.2%}")
        print("======================================")
