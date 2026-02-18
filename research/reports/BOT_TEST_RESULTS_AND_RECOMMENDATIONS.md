# Bot Test Results & Recommendations

**Date:** February 2026  
**Scope:** Unit tests, backtests, Walk-Forward Analysis, Monte Carlo for 3Commas bot simulators  
**Related:** [BOT_STRATEGIES_SUMMARY.md](summary/BOT_STRATEGIES_SUMMARY.md) | [BOT_WORKFLOW.md](../../docs/BOT_WORKFLOW.md)

---

## 1. Unit Test Results

All 14 unit tests **PASSED**.

| Test File | Tests | Status |
|-----------|-------|--------|
| `test_dca_bot.py` | 6 | PASS |
| `test_grid_bot.py` | 5 | PASS |
| `test_signal_bot.py` | 3 | PASS |

**Coverage:**
- DCA: SO levels, TP price, fee application, cooldown, single-deal lifecycle, export params
- Grid: geometric/arithmetic grid, profit per cell, trailing up, stop bot
- Signal: entry on signal, stop loss, trailing stop

---

## 2. Backtest Results

| Strategy | Symbol | Sharpe | MDD | Win Rate | Deals | Gate |
|----------|--------|--------|-----|----------|-------|------|
| S-A RSI DCA | BTC | 4.00 | 0% | 100% | 59 | PASS |
| S-A RSI DCA | ETH | 3.14 | 0% | 100% | 35 | PASS |
| S-A RSI DCA | SOL | 3.50 | 0% | 100% | 47 | PASS |
| S-B Grid ETH | ETH | 12.18 | 0% | 100% | 773 | PASS |
| S-C BB+RSI | BTC | 4.29 | - | - | 67 | - |
| S-E Grid Reversal | BTC | 22.42 | - | - | 2109 | - |
| S-D Signal EMA | BTC | -1.05 | -0.8% | 51.8% | 548 | **FAIL** |

**Notes:**
- S-A, S-B, S-C, S-E show strong in-sample performance; MDD 0% may indicate look-ahead or favorable period.
- S-D (EMA trend signal) failed gate: negative Sharpe, marginal win rate. Needs parameter tuning or different entry logic.

---

## 3. Walk-Forward Analysis

### S-A RSI DCA (BTC/USDT)
- **Train:** 180d | **Test:** 30d (use `--train 180 --test 30`; run scripts default to 365d/90d)
- **Total Return (OOS):** 207.37%
- **Win Rate:** 100%
- **Trades:** 54
- **Best params:** base_order_volume=25, safety_order_volume=30, max_safety_orders=4, take_profit=2.0–2.5%

### S-B Grid (ETH/USDT)
- **Train:** 180d | **Test:** 30d (use `--train 180 --test 30`)
- **Total Return (sum of cell returns):** Corrected metric (no compounding)
- **Win Rate:** 74.15%
- **Trades:** 6074
- **Note:** Grid uses fixed capital per cell; total return displayed as sum of per-cell returns, not compounded.

---

## 4. Monte Carlo Results

### S-A DCA (BTC/USDT)
| Metric | Value |
|--------|-------|
| Simulations | 1000 |
| Median Final Equity | $3,073.74 |
| Probability of Ruin | 0% |
| Prob. Drawdown > 20% | 0% |
| 95% VaR | $2,984.87 |

**Gate:** PASS (ruin < 20%)

### S-B Grid (ETH/USDT)
| Metric | Value |
|--------|-------|
| Median Final Equity | ~$3.5B (from $1k initial) — *invalid* |
| Note | MonteCarloValidator compounds returns; grid uses fixed capital per cell. Results inflated. |

**Recommendation:** Implement grid-specific MC that does not compound, or normalize grid pnl by `1/grid_lines_count` before MC.

---

## 5. Known Issues & Fixes Applied

1. **FutureWarning (fillna):** ✅ **Fixed.** Replaced `fillna(False)` with `where(s.notna(), False).astype(bool)` in backtest, WFA, and optimization scripts.

2. **WFA DCA slowness:** Param grid reduced from ~29k to 2 combos per window for faster runs. Full optimization in `optimize_dca_params.py`.

3. **Grid WFA total return:** Switched from `(1+pnl).prod()-1` to `pnl.sum()` for display, since grid uses fixed capital per cell.

4. **Grid Monte Carlo:** Current MC assumes compounding; grid trades should not compound. Needs separate logic.

5. **WFA Grid scoring:** `WalkForwardAnalyzer.optimize()` uses `(pnl+1).prod()-1` for all strategies. For grid, pnl is per-cell return; compounding 6000+ cells inflates scores. Grid WFA should use `pnl.sum()` for scoring.

---

## 6. Recommendations for Next Improvements

### High Priority
1. **Grid Monte Carlo:** Add `MonteCarloValidatorGrid` or a `compound=False` mode that uses additive returns: `equity = initial + sum(profit_per_trade)`.
2. **S-D Signal Bot:** Re-optimize TP/SL, add trend filter (e.g. only long when price > SMA200), or try different entry (e.g. EMA crossover instead of sustained above).
3. **3Commas validation:** Run same pair/period on 3Commas backtester and compare results within 20% for fidelity check.

### Medium Priority
4. **Report integration:** Wire `bots.report_utils.write_backtest_report()` into backtest scripts so results auto-save to `research/results/backtests/{dca|grid|signal}/`.
5. **WFA full param grid:** Add `--fast` flag for reduced grid; default to full grid when time permits.
6. **Slippage:** Add configurable slippage to fee engine for more realistic backtests.

### Lower Priority
7. **Remaining backtests:** Implement S-F (Heikin Ashi), S-G (ATR), S-H (QFL), S-I (MACD), S-J (Stochastic), S-K (SAR), S-L (RSI Pyramid), S-M (Grid Trailing).
8. **Regime gating:** Integrate `CryptoRegimeDetector` to enable/disable bots by regime (e.g. disable S-B grid in strong trend).
9. **Multi-symbol WFA:** Pool OOS trades across BTC, ETH, SOL for DCA as in existing `run_wfa_strategy_1.py --pool`.

---

## 7. Run Commands

```bash
# Unit tests (14 tests total)
pytest tests/test_dca_bot.py tests/test_grid_bot.py tests/test_signal_bot.py -v

# Backtests
python research/bot_backtests/backtest_dca_rsi.py          # S-A RSI DCA
python research/bot_backtests/backtest_dca_bb_rsi.py      # S-C BB+RSI
python research/bot_backtests/backtest_grid_eth.py        # S-B Grid ETH
python research/bot_backtests/backtest_grid_btc_reversal.py  # S-E Grid Reversal
python research/bot_backtests/backtest_signal_ema.py      # S-D EMA Signal

# WFA (default: 365d train, 90d test; use --train 180 --test 30 for 180/30)
python research/walk_forward/run_wfa_dca.py --strategy sa --symbol BTC/USDT
python research/walk_forward/run_wfa_grid.py --strategy sb --symbol ETH/USDT
python research/walk_forward/run_wfa_signal.py --strategy sd --symbol BTC/USDT

# Monte Carlo (run after WFA; requires WFA output CSV)
python research/monte_carlo/run_mc_dca.py --strategy sa --symbol BTC/USDT
python research/monte_carlo/run_mc_grid.py --strategy sb --symbol ETH/USDT
python research/monte_carlo/run_mc_signal.py --strategy sd --symbol BTC/USDT
```

---

*Generated from test run on PandaTrader bot simulation framework.*
