# Bot Workflow Runbook

End-to-end workflow for developing and deploying 3Commas bot strategies.

**Test Results:** [BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md](../research/reports/BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md) | **Summary:** [BOT_STRATEGIES_SUMMARY.md](../research/reports/summary/BOT_STRATEGIES_SUMMARY.md)

## Step 1: Define Strategy & Parameter Grid

See `crypto-bot-strategy-3.md` for strategy hypotheses and parameter ranges.

## Step 2: Run Backtest

```bash
# DCA (S-A RSI, S-C BB+RSI)
python research/bot_backtests/backtest_dca_rsi.py
python research/bot_backtests/backtest_dca_bb_rsi.py

# Grid (S-B ETH, S-E Reversal)
python research/bot_backtests/backtest_grid_eth.py
python research/bot_backtests/backtest_grid_btc_reversal.py

# Signal (S-D EMA)
python research/bot_backtests/backtest_signal_ema.py
```

**Gate (bot-type-specific):**
- **DCA:** Per-deal EV > 0, Win Rate > 75%
- **Grid:** Cell profit > 3× fees, annualized return > 12%
- **Signal:** Sharpe > 1.0, MDD < 25%

If failed, iterate parameters or drop strategy.

## Step 3: Parameter Optimization

```bash
python research/bot_optimization/optimize_dca_params.py --symbol BTC/USDT --top 10
```

## Step 4: Walk-Forward Analysis

```bash
# Default (full param grid)
python research/walk_forward/run_wfa_dca.py --strategy sa --symbol BTC/USDT
python research/walk_forward/run_wfa_grid.py --strategy sb --symbol ETH/USDT
python research/walk_forward/run_wfa_signal.py --strategy sd --symbol BTC/USDT

# Faster: --fast for reduced param grid
python research/walk_forward/run_wfa_dca.py --strategy sa --symbol BTC/USDT --fast

# Multi-symbol: --pool for DCA (BTC, ETH, SOL)
python research/walk_forward/run_wfa_dca.py --strategy sa --pool

# Regime gating: --regime-gate for grid (skip BULL regime)
python research/walk_forward/run_wfa_grid.py --strategy sb --symbol ETH/USDT --regime-gate
```

**Gate:** OOS Sharpe > 0.8, degradation < 40%.

## Step 5: Monte Carlo Validation

```bash
python research/monte_carlo/run_mc_dca.py --strategy sa --symbol BTC/USDT
python research/monte_carlo/run_mc_grid.py --strategy sb --symbol ETH/USDT
python research/monte_carlo/run_mc_signal.py --strategy sd --symbol BTC/USDT
```

**Gate:** Prob of ruin < 20%, 95% VaR acceptable.

## Step 6: Export to 3Commas

```python
from bots.export_config import export_to_3commas

# Use optimized_params from backtest/WFA
config = export_to_3commas(optimized_params, bot_type="dca")
# Paste into 3Commas bot creation form
```

## Step 7: Paper Trade

- Deploy on 3Commas paper mode
- Minimum 4 weeks
- Compare live vs simulated metrics weekly

## Step 8: Live Deploy

- Micro-deploy ($100–200 per bot)
- Monitor, re-optimize monthly, re-WFA quarterly

---

## Unit Tests

```bash
pytest tests/test_dca_bot.py tests/test_grid_bot.py tests/test_signal_bot.py tests/test_base_bot.py tests/test_monte_carlo.py tests/test_walk_forward.py -v
```

All tests must pass before deploying changes.

## 3Commas Fidelity Check

See [3COMMAS_VALIDATION.md](3COMMAS_VALIDATION.md) for comparing results with 3Commas backtester.
