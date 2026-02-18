# Bot Strategies Summary

**Last Updated:** February 2026  
**Full Results:** [BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md](../BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md)

| Strategy | Bot Type | Status | Sharpe | MDD | Win Rate | Gate |
|----------|----------|--------|--------|-----|----------|------|
| S-A RSI DCA | DCA | Realistic | 0.26 (BTC) | -1.9% | 95.1% | FAIL |
| S-B Grid ETH | Grid | Realistic | -0.06 | -13.8% | 97.4% | FAIL |
| S-C BB+RSI | DCA | Tested | -0.16 | - | - | FAIL |
| S-D EMA Signal | Signal | Gate Failed | -0.38 | -0.5% | 52.4% | FAIL |
| S-E Grid Reversal | Grid | Tested | -0.08 | - | - | FAIL |

*Realistic: DCA stop_loss 15%; Grid stop_bot 10% below lower. Win rates no longer 100%.

## WFA & Monte Carlo

| Strategy | WFA OOS Return | WFA Win Rate | MC Ruin Prob | MC Gate |
|----------|----------------|--------------|--------------|---------|
| S-A DCA (BTC) | 105.52% | 93.75% | 1.50% | PASS |
| S-B Grid (ETH) | 991.5% (sum) | 58.95% | 0% | PASS |
| S-D Signal (BTC) | -41.73% (OOS) | - | - | - |

*DCA MC: 40% prob DD>20% (realistic with SL). Grid MC: additive returns.

## How to Update

1. Run backtests: `python research/bot_backtests/backtest_*.py` (see full list in BOT_TEST_RESULTS)
2. Run WFA: `python research/walk_forward/run_wfa_dca.py`, `run_wfa_grid.py`, `run_wfa_signal.py`
3. Run MC: `python research/monte_carlo/run_mc_*.py` (requires WFA output first)
4. Update this table and [BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md](../BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md)

## Gate Criteria

- **Backtest:** Sharpe > 1.0, MDD < 25%
- **WFA:** OOS Sharpe > 0.8, degradation < 40%
- **Monte Carlo:** Prob of ruin < 20%
