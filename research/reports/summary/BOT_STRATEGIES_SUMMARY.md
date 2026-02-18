# Bot Strategies Summary

**Last Updated:** February 2026  
**Full Results:** [BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md](../BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md)

| Strategy | Bot Type | Status | Sharpe | MDD | Win Rate | Gate | Paper Trade Ready |
|----------|----------|--------|--------|-----|----------|------|-------------------|
| S-A RSI DCA | DCA | Realistic | 0.26 (BTC) | -1.9% | 95.1% | PASS | Yes |
| S-B Grid ETH | Grid | Realistic | -0.56 | -12.3% | 97.9% | FAIL | No |
| S-C BB+RSI | DCA | Tested | -0.21 | -2.4% | 93.8% | PASS | No |
| S-D EMA Signal | Signal | RETIRED | -0.38 | -0.5% | 52.4% | FAIL | No |
| S2 Funding Reversion | Signal | Routing | - | - | - | - | Paper Trade |
| S-E Grid Reversal | Grid | Tested | -0.08 | - | - | FAIL | No |

*S-A, S-C pass DCA gate (EV>0, WR>75%). S-B fails: cell profit 0.17%<0.6%, annualized -2.7%<12% (post methodology fix).

## WFA & Monte Carlo

| Strategy | WFA OOS Return | WFA Win Rate | MC Ruin Prob | MC Gate |
|----------|----------------|--------------|--------------|---------|
| S-A DCA (BTC) | 81.66% | 95.12% | 2–15% (run-dep) | PASS |
| S-A DCA + regime-gate | 43.34% | 93.55% | 12.70% | FAIL |
| S-B Grid (ETH) | -31.4% (sum), -1.6% ann. | 91.80% | 73.10% | FAIL |
| S-D Signal (BTC) | -37.84% | 40.66% | 96.30% | FAIL |

*Run with --fast. S-A (non-gated) is the paper trading candidate; S-A + regime-gate FAILs MC (ruin 12.70% > 10%). S-B post methodology fix (range from first 120 bars, break on stop). 3Commas validation: see [docs/3COMMAS_VALIDATION.md](../../docs/3COMMAS_VALIDATION.md).

## WFA Options

- `--fast`: Reduced param grid for faster runs
- `--pool`: DCA only; pool OOS trades across BTC, ETH, SOL
- `--regime-gate`: Grid skip BULL; DCA skip BEAR (block entries in bear regime)
- `--score-mode ev`: DCA only; optimize by EV×win_rate instead of total return

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
