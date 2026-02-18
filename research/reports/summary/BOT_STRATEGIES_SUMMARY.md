# Bot Strategies Summary

**Last Updated:** February 2026  
**Full Results:** [BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md](../BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md)

| Strategy | Bot Type | Status | Sharpe | MDD | Deals | Gate |
|----------|----------|--------|--------|-----|-------|------|
| S-A RSI DCA | DCA | Validated | 3.55 avg | 0% | 141 | PASS |
| S-B Grid ETH | Grid | Validated | 12.18 | 0% | 773 | PASS |
| S-C BB+RSI | DCA | Tested | 4.29 | - | 67 | - |
| S-D EMA Signal | Signal | Gate Failed | -1.05 | -0.8% | 548 | FAIL |
| S-E Grid Reversal | Grid | Tested | 22.42 | - | 2109 | - |

## WFA & Monte Carlo

| Strategy | WFA OOS Return | MC Ruin Prob | MC Gate |
|----------|----------------|--------------|---------|
| S-A DCA (BTC) | 207.37% | 0% | PASS |
| S-B Grid (ETH) | sum of cell returns | N/A* | - |
| S-D Signal (BTC) | Not run (gate failed) | - | - |

*Grid MC uses compounding; results inflated. Needs grid-specific MC. S-E/S-M grid WFA not yet implemented in run_wfa_grid.py.

## How to Update

1. Run backtests: `python research/bot_backtests/backtest_*.py` (see full list in BOT_TEST_RESULTS)
2. Run WFA: `python research/walk_forward/run_wfa_dca.py`, `run_wfa_grid.py`, `run_wfa_signal.py`
3. Run MC: `python research/monte_carlo/run_mc_*.py` (requires WFA output first)
4. Update this table and [BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md](../BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md)

## Gate Criteria

- **Backtest:** Sharpe > 1.0, MDD < 25%
- **WFA:** OOS Sharpe > 0.8, degradation < 40%
- **Monte Carlo:** Prob of ruin < 20%
