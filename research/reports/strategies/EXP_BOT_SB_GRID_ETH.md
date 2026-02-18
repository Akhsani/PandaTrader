# EXP_BOT_SB: Geometric Sideways Grid (ETH)

**Status:** Validated (backtest) | **Full results:** [BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md](../BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md)

## 1. Hypothesis
**Observation:** ETH oscillates in ranges; grid harvests volatility.
**Hypothesis:** Geometric grid in 20% range captures oscillation profits.

## 2. Methodology
- **Bot Type**: Grid (geometric)
- **Pair**: ETH/USDT
- **Data**: 1h OHLCV

## 3. Results (Realistic — with stop_bot_price 10% below lower)

| Metric | Value |
|--------|-------|
| Sharpe | -0.06 |
| MDD | -13.8% |
| Win Rate | 97.4% |
| Deals | 780 |
| Gate | FAIL |

**WFA (ETH):** 3859 trades, 58.95% win rate. Total return 991.5% (sum of cell returns).  
**Monte Carlo:** Median equity ~$1,496, 0% ruin. Gate PASS.

**Commands:**
- Backtest: `python research/bot_backtests/backtest_grid_eth.py`
- WFA: `python research/walk_forward/run_wfa_grid.py --strategy sb --symbol ETH/USDT`
- MC: `python research/monte_carlo/run_mc_grid.py --strategy sb --symbol ETH/USDT`

## 4. Conclusion
**Realistic.** stop_bot_price 10% below lower added; win rate 97.4% (was 100%). Backtest gate fails; MC passes. Re-optimize for gate if needed.

## 5. 3Commas Export
Use `bots.export_config.export_to_3commas(optimized_params, 'grid')`.

## 6. Next Steps
- Paper trade on 3Commas or Pionex
