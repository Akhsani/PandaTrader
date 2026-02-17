
import pandas as pd
import numpy as np
import itertools
from datetime import timedelta
import matplotlib.pyplot as plt

class WalkForwardAnalyzer:
    def __init__(self, strategy_func, param_grid, price_df, funding_df=None, 
                 train_window_days=180, test_window_days=30):
        self.strategy = strategy_func
        self.param_grid = param_grid
        self.price_df = price_df
        self.funding_df = funding_df
        self.train_window = timedelta(days=train_window_days)
        self.test_window = timedelta(days=test_window_days)
        
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
        """Find best params in training window"""
        best_params = None
        best_score = -np.inf
        
        # Slicing data for optimization is expensive if done repeatedly inside loop
        # But necessary.
        mask = (self.price_df.index >= start_date) & (self.price_df.index < end_date)
        train_price = self.price_df.loc[mask]
        
        train_funding = None
        if self.funding_df is not None:
             mask_f = (self.funding_df.index >= start_date) & (self.funding_df.index < end_date)
             train_funding = self.funding_df.loc[mask_f]

        keys, values = zip(*self.param_grid.items())
        combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
        
        for params in combinations:
            # Run strategy
            results = self.strategy(train_price, train_funding, **params)
            
            if results is None or results.empty:
                score = -np.inf
            else:
                # Scoring metric: Sharpe * log(1+Return) ? 
                # Simple: Total Return if Drawdown < 20%
                total_return = (results['pnl'] + 1).prod() - 1
                
                # Drawdown penalty
                cum_ret = (results['pnl'] + 1).cumprod()
                max_dd = ((cum_ret - cum_ret.cummax()) / cum_ret.cummax()).min()
                
                if max_dd < -0.30: # Penalize heavy DD
                    score = -1.0
                else:
                    score = total_return
            
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
                
            print(f"    Best Params: {best_params} (Score: {train_score:.2%})")
            
            # 2. Test
            mask_test = (self.price_df.index >= train_end) & (self.price_df.index < test_end)
            test_price = self.price_df.loc[mask_test]
            
            test_funding = None
            if self.funding_df is not None:
                mask_tf = (self.funding_df.index >= train_end) & (self.funding_df.index < test_end)
                test_funding = self.funding_df.loc[mask_tf]
                
            test_results = self.strategy(test_price, test_funding, **best_params)
            
            if test_results is not None and not test_results.empty:
                pnl = test_results['pnl'].sum() # Approximation for log returns, or exact calc
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
