# EXP_BOT_SB: Geometric Sideways Grid (ETH)

**Status:** Validated (backtest) | **Full results:** [BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md](../BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md)

## 1. Hypothesis
**Observation:** ETH oscillates in ranges; grid harvests volatility.
**Hypothesis:** Geometric grid in 20% range captures oscillation profits.

## 2. Methodology
- **Bot Type**: Grid (geometric)
- **Pair**: ETH/USDT
- **Data**: 1h OHLCV

## 3. Results

| Metric | Value |
|--------|-------|
| Sharpe | 12.18 |
| MDD | 0% |
| Win Rate | 100% |
| Deals | 773 |
| Gate | PASS |

**WFA (ETH):** 6074 trades, 74.15% win rate. Total return = sum of cell returns (no compounding).  
**Monte Carlo:** Current MC compounds; results inflated. Grid-specific MC needed.

**Commands:**
- Backtest: `python research/bot_backtests/backtest_grid_eth.py`
- WFA: `python research/walk_forward/run_wfa_grid.py --strategy sb --symbol ETH/USDT`
- MC: `python research/monte_carlo/run_mc_grid.py --strategy sb --symbol ETH/USDT`

## 4. Conclusion
**Validated (backtest).** WFA completed. MC needs grid-specific logic before full validation.

## 5. 3Commas Export
Use `bots.export_config.export_to_3commas(optimized_params, 'grid')`.

## 6. Next Steps
- Paper trade on 3Commas or Pionex
