# Bot Strategies Summary

**Last Updated:** February 2026  
**Full Results:** [BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md](../BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md)

| Strategy | Bot Type | Status | Sharpe | MDD | Win Rate | Gate | Paper Trade Ready |
|----------|----------|--------|--------|-----|----------|------|-------------------|
| S-A RSI DCA | DCA | Realistic | 0.26 (BTC) | -1.9% | 95.1% | PASS | Yes |
| S-B Grid ETH | Grid | Realistic | -0.06 | -13.8% | 97.4% | FAIL | No |
| S-C BB+RSI | DCA | Tested | -0.16 | - | - | FAIL | No |
| S-D EMA Signal | Signal | RETIRED | -0.38 | -0.5% | 52.4% | FAIL | No |
| S2 Funding Reversion | Signal | Routing | - | - | - | - | Paper Trade |
| S-E Grid Reversal | Grid | Tested | -0.08 | - | - | FAIL | No |

*S-A passes DCA gate (EV>0, WR>75%, MC ruin<10%). S-B backtest gate fails (cell profit 0.33%<0.6%, annualized -1.1%<12%); MC ruin varies by WFA run.

## WFA & Monte Carlo

| Strategy | WFA OOS Return | WFA Win Rate | MC Ruin Prob | MC Gate |
|----------|----------------|--------------|--------------|---------|
| S-A DCA (BTC) | 81.66% | 95.12% | 2.10% | PASS |
| S-A DCA + regime-gate | 43.34% | 93.55% | 12.70% | FAIL |
| S-B Grid (ETH) | 6.9% (sum), 0.4% ann. | 96.83% | 47.10% | FAIL |
| S-D Signal (BTC) | -15.06% | 51.46% | 76.10% | FAIL |

*Run with --fast. DCA MC: 29.5% prob DD>20%. Grid MC: additive returns; ruin high with low WFA sum. 3Commas validation: see [docs/3COMMAS_VALIDATION.md](../../docs/3COMMAS_VALIDATION.md).

## WFA Options

- `--fast`: Reduced param grid for faster runs
- `--pool`: DCA only; pool OOS trades across BTC, ETH, SOL
- `--regime-gate`: Grid skip BULL; DCA skip BEAR (block entries in bear regime)

## How to Update

1. Run backtests: `python research/bot_backtests/backtest_*.py` (see full list in BOT_TEST_RESULTS)
2. Run WFA: `python research/walk_forward/run_wfa_dca.py`, `run_wfa_grid.py`, `run_wfa_signal.py` (add `--fast`, `--pool`, or `--regime-gate` as needed)
3. Run MC: `python research/monte_carlo/run_mc_*.py` (requires WFA output first)
4. Update this table and [BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md](../BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md)

## Gate Criteria (Bot-Type-Specific)

| Bot Type | Backtest Gate | Monte Carlo Gate |
|----------|---------------|------------------|
| **DCA** | Per-deal EV > 0, Win Rate > 75% | MC ruin < 10% |
| **Grid** | Cell profit > 3× fees, annualized return > 12% | MC ruin < 5% |
| **Signal** | Sharpe > 1.0, MDD < 25% | Prob of ruin < 20% |

- **WFA:** OOS return positive, degradation < 40%
