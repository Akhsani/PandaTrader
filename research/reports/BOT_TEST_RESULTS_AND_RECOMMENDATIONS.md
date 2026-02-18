# Bot Test Results & Recommendations

**Date:** February 2026  
**Scope:** Unit tests, backtests, Walk-Forward Analysis, Monte Carlo for 3Commas bot simulators  
**Related:** [BOT_STRATEGIES_SUMMARY.md](summary/BOT_STRATEGIES_SUMMARY.md) | [BOT_WORKFLOW.md](../../docs/BOT_WORKFLOW.md)

---

## 1. Unit Test Results

All 22 unit tests **PASSED**.

| Test File | Tests | Status |
|-----------|-------|--------|
| `test_dca_bot.py` | 6 | PASS |
| `test_grid_bot.py` | 5 | PASS |
| `test_signal_bot.py` | 3 | PASS |
| `test_base_bot.py` | 6 | PASS |
| `test_monte_carlo.py` | 3 | PASS |
| `test_walk_forward.py` | 2 | PASS |

**Coverage:**
- DCA: SO levels, TP price, fee application, cooldown, single-deal lifecycle, export params
- Grid: geometric/arithmetic grid, profit per cell, trailing up, stop bot
- Signal: entry on signal, stop loss, trailing stop
- Base: FeeEngine, compute_per_deal_ev, compute_annualized_capital_return
- Monte Carlo: compound validator, grid additive validator (no inflation)
- Walk-Forward: score_mode compound vs sum for grid

---

## 2. Backtest Results (Realistic — with Stop Loss / Stop Bot)

### Bot-Type-Specific Gate Criteria

| Bot Type | Gate Criteria |
|----------|---------------|
| **DCA** | Per-deal EV > 0, Win Rate > 75%, MC ruin < 10% |
| **Grid** | Cell profit > 3× fees, annualized capital return > 12%, MC ruin < 5% |
| **Signal** | Sharpe > 1.0, MDD < 25% |

### Results Table

| Strategy | Symbol | Sharpe | MDD | Win Rate | EV/Deal | Ann. Ret | Deals | Gate |
|----------|--------|--------|-----|----------|---------|----------|-------|------|
| S-A RSI DCA | BTC | 0.26 | -1.9% | 95.1% | +1.54% | - | 82 | PASS |
| S-A RSI DCA | ETH | -0.95 | -3.9% | 90.5% | +0.74% | - | 116 | PASS |
| S-A RSI DCA | SOL | -1.20 | -4.6% | 90.0% | +0.65% | - | 130 | PASS |
| S-A RSI DCA (regime-gate) | BTC | 0.01 | -2.0% | 94.2% | +1.38% | - | 69 | PASS |
| S-B Grid ETH | ETH | -0.06 | -13.8% | 97.4% | - | -1.1% | 780 | FAIL |
| S-C BB+RSI | BTC | -0.21 | - | - | - | - | 113 | FAIL |
| S-E Grid Reversal | BTC | -0.08 | - | - | - | - | 2146 | FAIL |
| S-D Signal EMA | BTC | -0.38 | -0.5% | 52.4% | - | - | 288 | **FAIL** |

*S-A passes DCA gate (EV>0, WR>75%, MC ruin 2.1%<10%). S-B fails: cell profit 0.33%<0.6%, annualized -1.1%<12%.*

**Realistic risk controls applied (Feb 2026):**
- **DCA:** `stop_loss_percentage: 15%` — cuts loss if avg entry drops 15%. Win rates now 90–95% (was 100%).
- **Grid:** `stop_bot_price: lower * 0.90` — closes at loss if price crashes 10% below grid. Win rate 97.4% (was 100%).
- **S-D:** Already had stop loss; 52.4% win rate is realistic.

**Notes:**
- Previous 100% win rates were due to no SL/stop_bot; only profitable exits were counted. Current results reflect realistic risk management.
- Gate failures indicate strategies may need re-optimization with SL/stop_bot in the param grid.

---

## 3. Walk-Forward Analysis

### S-A RSI DCA (BTC/USDT) — 365d train, 90d test, --fast
- **Total Return (OOS):** 81.66%
- **EV per deal:** 0.0154
- **Win Rate:** 95.12%
- **Trades:** 41
- **Best params:** TP 2.5%, stop_loss 15%

### S-A RSI DCA with --regime-gate (BTC/USDT)
- **Total Return (OOS):** 43.34%
- **EV per deal:** 0.0127
- **Win Rate:** 93.55%
- **Trades:** 31
- **Note:** Fewer trades; blocks entries in BEAR regime.

### S-B Grid (ETH/USDT)
- **Total Return (sum of cell returns):** 6.9%
- **Annualized capital return:** 0.4% (on $1000, 20 lines)
- **Win Rate:** 96.83%
- **Trades:** 947
- **Note:** Grid uses fixed capital per cell; sum of cell returns differs from annualized on full capital.

### S-D Signal (BTC/USDT)
- **Total Return (OOS):** -15.06%
- **Win Rate:** 51.46%
- **Trades:** 103

---

## 4. Monte Carlo Results

### S-A DCA (BTC/USDT)
| Metric | Value |
|--------|-------|
| Simulations | 1000 |
| Median Final Equity | $1,816.58 |
| Probability of Ruin | 2.10% |
| Prob. Drawdown > 20% | 29.50% |
| 95% VaR | $1,035.95 |

**Gate:** PASS (ruin 2.1% < 10%). Uses WFA OOS trades (81.66% return, 41 trades).

### S-B Grid (ETH/USDT)
| Metric | Value |
|--------|-------|
| Simulations | 1000 |
| Median Final Equity | $1,003.91 |
| Probability of Ruin | 47.10% |
| Prob. Drawdown > 20% | 0% |
| 95% VaR | $935.11 |

**Gate:** FAIL (ruin 47.1% > 5%). Uses `MonteCarloValidatorGrid` with additive returns. WFA sum 6.9% over period.

### S-D Signal (BTC/USDT)
| Metric | Value |
|--------|-------|
| Simulations | 1000 |
| Median Final Equity | $849.44 |
| Probability of Ruin | 76.10% |
| Prob. Drawdown > 20% | 83.70% |
| 95% VaR | $541.57 |

**Gate:** FAIL (ruin 76.1% > 20%). S-D RETIRED; use S2 Funding Reversion instead.

---

## 4.5 3Commas Fidelity Check (Manual)

| Metric | PandaTrader | 3Commas | Delta |
|--------|-------------|---------|-------|
| Total Return | - | - | Run same pair/period on 3Commas backtester |
| Win Rate | - | - | Compare within 20% |
| Deals | - | - | |
| Max Drawdown | - | - | |

See [docs/3COMMAS_VALIDATION.md](../../docs/3COMMAS_VALIDATION.md) for steps.

---

## 5. Known Issues & Fixes Applied

1. **FutureWarning (fillna):** ✅ **Fixed.** Replaced `fillna(False)` with `where(s.notna(), False).astype(bool)` in backtest, WFA, and optimization scripts.

2. **WFA DCA slowness:** Param grid reduced from ~29k to 2 combos per window for faster runs. Full optimization in `optimize_dca_params.py`.

3. **Grid WFA total return:** ✅ **Fixed.** Switched from `(1+pnl).prod()-1` to `pnl.sum()` for display, since grid uses fixed capital per cell.

4. **Grid Monte Carlo:** ✅ **Fixed.** Added `MonteCarloValidatorGrid` with additive returns. Median equity now ~$1,756 (was inflated to ~$3.5B).

5. **WFA Grid scoring:** ✅ **Fixed.** `WalkForwardAnalyzer` accepts `score_mode="sum"`; grid WFA uses `pnl.sum()` for optimization scoring.

6. **Report integration:** ✅ **Fixed.** Backtest scripts call `write_backtest_report()`; results auto-save to `research/results/backtests/{dca|grid|signal}/`.

7. **Realistic win rates:** ✅ **Fixed.** Added `stop_loss_percentage: 15%` to DCA and `stop_bot_price: lower*0.90` to Grid. Win rates now 90–97% (was 100%). Report JSON: added `_json_safe()` for numpy/pandas type serialization.

8. **WFA --fast, --pool, --regime-gate:** ✅ **Added.** `--fast` reduces param grid; `--pool` pools DCA across BTC/ETH/SOL; `--regime-gate` skips grid when regime is BULL. WalkForwardAnalyzer accepts `pre_test_hook`.

9. **Slippage:** ✅ **Added.** FeeEngine accepts `slippage_bps`; bots pass it via params. Use `slippage_bps: 10` for 0.1% slippage in backtests.

---

## 6. Recommendations for Next Improvements

### High Priority
1. ~~**Grid Monte Carlo:**~~ ✅ Done. `MonteCarloValidatorGrid` implemented.
2. ~~**S-D Signal Bot:**~~ ✅ RETIRED. S-D EMA crossover structurally bad; replaced by S2 Funding Reversion → Signal Bot webhook. See [docs/S2_SIGNAL_BOT_WEBHOOK.md](../../docs/S2_SIGNAL_BOT_WEBHOOK.md).
3. **3Commas validation:** Run same pair/period on 3Commas backtester and compare results within 20% for fidelity check.

### Medium Priority
4. ~~**Report integration:**~~ ✅ Done. Backtest scripts write to `research/results/backtests/{dca|grid|signal}/`.
5. ~~**WFA full param grid:**~~ ✅ Done. Added `--fast` flag for reduced grid; default is full grid.
6. ~~**Slippage:**~~ ✅ Done. Added `slippage_bps` to FeeEngine; bots accept it in params.

### Lower Priority
7. **Remaining backtests:** Implement S-F (Heikin Ashi), S-G (ATR), S-H (QFL), S-I (MACD), S-J (Stochastic), S-K (SAR), S-L (RSI Pyramid), S-M (Grid Trailing).
8. ~~**Regime gating:**~~ ✅ Done. Added `--regime-gate` to `run_wfa_grid.py`; skips grid when regime is BULL.
9. ~~**Multi-symbol WFA:**~~ ✅ Done. Added `--pool` to `run_wfa_dca.py`; pools OOS trades across BTC, ETH, SOL.

---

## 7. Run Commands

```bash
# Unit tests (22 tests total)
pytest tests/test_dca_bot.py tests/test_grid_bot.py tests/test_signal_bot.py tests/test_base_bot.py tests/test_monte_carlo.py tests/test_walk_forward.py -v

# Backtests
python research/bot_backtests/backtest_dca_rsi.py          # S-A RSI DCA
python research/bot_backtests/backtest_dca_rsi.py --regime-gate  # S-A with regime gate
python research/bot_backtests/backtest_dca_bb_rsi.py      # S-C BB+RSI
python research/bot_backtests/backtest_grid_eth.py        # S-B Grid ETH
python research/bot_backtests/backtest_grid_btc_reversal.py  # S-E Grid Reversal
python research/bot_backtests/backtest_signal_ema.py      # S-D EMA Signal

# WFA (default: 365d train, 90d test; use --train 180 --test 30 for 180/30)
python research/walk_forward/run_wfa_dca.py --strategy sa --symbol BTC/USDT
python research/walk_forward/run_wfa_grid.py --strategy sb --symbol ETH/USDT
python research/walk_forward/run_wfa_signal.py --strategy sd --symbol BTC/USDT

# WFA options: --fast (reduced grid), --pool (DCA multi-symbol), --regime-gate (grid skip BULL)
python research/walk_forward/run_wfa_dca.py --strategy sa --pool --fast
python research/walk_forward/run_wfa_grid.py --strategy sb --symbol ETH/USDT --regime-gate

# Monte Carlo (run after WFA; requires WFA output CSV)
python research/monte_carlo/run_mc_dca.py --strategy sa --symbol BTC/USDT
python research/monte_carlo/run_mc_grid.py --strategy sb --symbol ETH/USDT  # uses --investment 1000 --grid-lines 20
python research/monte_carlo/run_mc_signal.py --strategy sd --symbol BTC/USDT
```

---

## 8. Next Recommendations (Post-Implementation)

1. **Re-optimize for gate pass:** With SL/stop_bot, backtest gates fail. Consider TP/SL/stop_bot in WFA param grid; tune for Sharpe > 1.0, MDD < 25%.
2. **3Commas fidelity check:** See [docs/3COMMAS_VALIDATION.md](../../docs/3COMMAS_VALIDATION.md). Run same pair/period on 3Commas backtester; compare within 20%.
3. **S-D further tuning:** Try different indicators (e.g. MACD crossover, RSI oversold in uptrend) or multi-timeframe confirmation.
4. **Slippage:** Add `slippage_bps` to `FeeEngine` for realistic backtests.
5. **Regime gating:** Integrate `CryptoRegimeDetector` to disable S-B grid in strong trend regimes.

---

*Generated from test run on PandaTrader bot simulation framework. Last updated: February 2026.*
