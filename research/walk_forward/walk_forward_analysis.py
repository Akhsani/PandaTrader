
import pandas as pd
import numpy as np
import itertools
from datetime import timedelta
import matplotlib.pyplot as plt

try:
    import optuna
    HAS_OPTUNA = True
except ImportError:
    HAS_OPTUNA = False


def _optuna_to_dca_params(trial_params: dict, extra: dict = None) -> dict:
    """Map Optuna trial params to DCA bot param names."""
    extra = extra or {}
    return {
        "base_order_volume": trial_params["base_order_volume"],
        "safety_order_volume": trial_params["safety_order_volume"],
        "max_safety_orders": trial_params["max_safety_orders"],
        "safety_order_step_percentage": trial_params["safety_order_step"],
        "martingale_volume_coefficient": trial_params["mv_coeff"],
        "martingale_step_coefficient": trial_params["ms_coeff"],
        "take_profit_percentage": trial_params["tp_pct"],
        "stop_loss_percentage": trial_params["sl_pct"],
        "trailing_take_profit": False,
        "max_active_deals": 1,
        "cooldown_between_deals": 0,
        "fee": 0.001,
        **extra,
    }


class WalkForwardAnalyzer:
    def __init__(self, strategy_func, param_grid, price_df, funding_df=None,
                 train_window_days=180, test_window_days=30, score_mode="compound",
                 pre_test_hook=None, optuna_trials=None):
        """
        score_mode: "compound" for DCA/Signal (equity compounds), "sum" for Grid (fixed capital per cell),
        "ev" for DCA EV-based optimization (ev_per_deal * win_rate).
        pre_test_hook: optional (train_price, test_price, best_params) -> bool. If False, skip test window.
        optuna_trials: when set with score_mode="ev", use Optuna instead of grid search (e.g. 50).
        """
        self.strategy = strategy_func
        self.param_grid = param_grid
        self.price_df = price_df
        self.funding_df = funding_df
        self.train_window = timedelta(days=train_window_days)
        self.test_window = timedelta(days=test_window_days)
        self.score_mode = score_mode
        self.pre_test_hook = pre_test_hook
        self.optuna_trials = optuna_trials
        
    def generate_windows(self):
        """Generator for (train_start, train_end, test_end)"""
        start_date = self.price_df.index.min()
        end_date = self.price_df.index.max()
        
        current_date = start_date
        
        while current_date + self.train_window + self.test_window <= end_date:
            train_end = current_date + self.train_window
            test_end = train_end + self.test_window
            yield current_date, train_end, test_end
            current_date += self.test_window

    def optimize(self, start_date, end_date):
        """Find best params in training window. Uses Optuna when score_mode=='ev' and optuna_trials set."""
        best_params = None
        best_score = -np.inf

        mask = (self.price_df.index >= start_date) & (self.price_df.index < end_date)
        train_price = self.price_df.loc[mask]

        train_funding = None
        if self.funding_df is not None:
            mask_f = (self.funding_df.index >= start_date) & (self.funding_df.index < end_date)
            train_funding = self.funding_df.loc[mask_f]

        # Extra params from grid to pass through (e.g. regime_gate)
        optuna_extra = {k: v[0] for k, v in self.param_grid.items()
                        if k not in ("base_order_volume", "safety_order_volume", "max_safety_orders",
                                    "safety_order_step_percentage", "martingale_volume_coefficient",
                                    "martingale_step_coefficient", "take_profit_percentage", "stop_loss_percentage")
                        and len(v) == 1}

        if (self.score_mode == "ev" and self.optuna_trials and HAS_OPTUNA):
            # Use Optuna instead of grid search
            def objective(trial):
                trial_params = {
                    "base_order_volume": trial.suggest_float("base_order_volume", 15, 50),
                    "safety_order_volume": trial.suggest_float("safety_order_volume", 20, 80),
                    "max_safety_orders": trial.suggest_int("max_safety_orders", 2, 7),
                    "safety_order_step": trial.suggest_float("safety_order_step", 0.3, 2.0),
                    "mv_coeff": trial.suggest_float("mv_coeff", 1.2, 3.0),
                    "ms_coeff": trial.suggest_float("ms_coeff", 1.0, 2.5),
                    "tp_pct": trial.suggest_float("tp_pct", 1.0, 4.0),
                    "sl_pct": trial.suggest_float("sl_pct", 8.0, 25.0),
                }
                # Capital-at-risk constraint (10% of $10k account = $1,000 max)
                bo = trial_params["base_order_volume"]
                so_vol = trial_params["safety_order_volume"]
                max_so = trial_params["max_safety_orders"]
                mv_coeff = trial_params["mv_coeff"]
                sl_pct = trial_params["sl_pct"]
                total_so_capital = so_vol * sum(mv_coeff**i for i in range(max_so))
                total_capital_at_risk = bo + total_so_capital
                if total_capital_at_risk > 1000:
                    return -999.0
                # Worst-case loss constraint (5% of $10k = $500 max)
                worst_loss = total_capital_at_risk * (sl_pct / 100)
                if worst_loss > 500:
                    return -999.0
                params = _optuna_to_dca_params(trial_params, optuna_extra)
                results = self.strategy(train_price, train_funding, **params)
                if results is None or results.empty or len(results) < 10:
                    return -999.0
                ev_per_deal = results["pnl"].mean()
                win_rate = (results["pnl"] > 0).mean()
                return float(ev_per_deal * win_rate * 100) if win_rate > 0 else -999.0

            study = optuna.create_study(direction="maximize")
            study.optimize(objective, n_trials=self.optuna_trials, show_progress_bar=False)
            best_trial = study.best_params
            best_params = _optuna_to_dca_params(best_trial, optuna_extra)
            best_score = study.best_value
            return best_params, best_score

        # Grid search (original logic)
        keys, values = zip(*self.param_grid.items())
        combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]

        for params in combinations:
            results = self.strategy(train_price, train_funding, **params)

            if results is None or results.empty:
                score = -np.inf
            else:
                if self.score_mode == "ev":
                    ev_per_deal = results["pnl"].mean()
                    win_rate = (results["pnl"] > 0).mean()
                    score = float(ev_per_deal * win_rate * 100) if win_rate > 0 else -np.inf
                elif self.score_mode == "sum":
                    total_return = results["pnl"].sum()
                    cum_ret = 1 + results["pnl"].cumsum()
                    peak = cum_ret.cummax()
                    denom = np.maximum(peak.values, 1e-10)
                    max_dd = ((cum_ret.values - peak.values) / denom).min()
                    score = -1.0 if max_dd < -0.30 else total_return
                else:
                    total_return = (results["pnl"] + 1).prod() - 1
                    cum_ret = (results["pnl"] + 1).cumprod()
                    peak = cum_ret.cummax()
                    denom = np.maximum(peak.values, 1e-10)
                    max_dd = ((cum_ret.values - peak.values) / denom).min()
                    score = -1.0 if max_dd < -0.30 else total_return

            if score > best_score:
                best_score = score
                best_params = params

        return best_params, best_score

    def run(self):
        walk_forward_results = []
        
        print(f"Starting Walk-Forward Analysis...")
        print(f"Train: {self.train_window.days}d, Test: {self.test_window.days}d")
        
        for train_start, train_end, test_end in self.generate_windows():
            print(f"  Window: {train_start.date()} -> {train_end.date()} (Test -> {test_end.date()})")
            
            # 1. Optimize
            best_params, train_score = self.optimize(train_start, train_end)
            
            if best_params is None:
                print("    No profitable params found in train.")
                continue
                
            score_fmt = f"{train_score:.2f}" if self.score_mode == "ev" else f"{train_score:.2%}"
            print(f"    Best Params: {best_params} (Score: {score_fmt})")
            
            # 2. Test
            mask_test = (self.price_df.index >= train_end) & (self.price_df.index < test_end)
            test_price = self.price_df.loc[mask_test]
            mask_train = (self.price_df.index >= train_start) & (self.price_df.index < train_end)
            train_price = self.price_df.loc[mask_train]

            if self.pre_test_hook is not None:
                if not self.pre_test_hook(train_price, test_price, best_params):
                    print(f"    Test skipped (pre_test_hook)")
                    continue

            test_funding = None
            if self.funding_df is not None:
                mask_tf = (self.funding_df.index >= train_end) & (self.funding_df.index < test_end)
                test_funding = self.funding_df.loc[mask_tf]
                
            test_results = self.strategy(test_price, test_funding, **best_params)
            
            if test_results is not None and not test_results.empty:
                if self.score_mode == "sum":
                    ret = test_results['pnl'].sum()
                elif self.score_mode == "ev":
                    ret = (test_results['pnl'] + 1).prod() - 1  # OOS return for display
                else:
                    ret = (test_results['pnl'] + 1).prod() - 1
                print(f"    Test Return: {ret:.2%}")
                
                # Store trades
                test_results['window_start'] = train_end
                walk_forward_results.append(test_results)
            else:
                print(f"    Test Return: 0.00%")
        
        if not walk_forward_results:
            return pd.DataFrame()
            
        all_trades = pd.concat(walk_forward_results)
        all_trades.sort_values('exit_time', inplace=True)
        return all_trades
