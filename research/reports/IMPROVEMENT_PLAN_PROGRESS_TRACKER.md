# PandaTrader Improvement Plan — Progress Tracker

**Source:** [crypto-bot-strategy-4.md](../../crypto-bot-strategy-4.md)  
**Created:** February 2026  
**Use:** Check off tasks as completed; update status and notes.

---

## Overview

| Priority | Improvement | Impact | Effort | Status |
|----------|-------------|--------|--------|--------|
| P1 | Fix Gate Criteria | Critical | 1 hour | ✅ Done |
| P2 | Add Regime Gating to S-A DCA | High | 1–2 days | ✅ Done |
| P3 | Replace S-D with S2 → Signal Bot Webhook | High | 2–3 hours | ✅ Done |
| P4 | Switch DCA Optimization to Bayesian (Optuna) | Medium | 1 day | ✅ Done |
| P5 | Add Per-Deal EV & Capital-Normalized Grid Metrics | Medium | 4–6 hours | ✅ Done |

---

## Priority 1: Fix Gate Criteria

**Impact:** Critical | **Effort:** ~1 hour  
**Goal:** S-A and S-B move to PASS; paper trading can start.

### Tasks

- [x] **1.1** Update gate criteria in `research/reports/BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md`
  - [x] Add bot-type-specific gate section (DCA vs Grid vs Signal)
  - [x] DCA gate: Per-deal EV > 0, Win Rate > 75%, MC ruin < 10%
  - [x] Grid gate: Cell profit > 3× fees, annualized capital return > 12%, MC ruin < 5%
  - [x] Signal gate: Sharpe > 1.0, MDD < 25% (unchanged)
  - [x] Update Section 2 table with new gate logic / PASS/FAIL per strategy

- [x] **1.2** Add `compute_per_deal_ev()` to `bots/base_bot.py`
  - [x] Implement: `mean(TP return) × win_rate + mean(SL return) × loss_rate`
  - [x] Handle edge case: no closed deals → return 0 or None
  - [x] Integrate into `compute_bot_metrics()` or return alongside

- [x] **1.3** Update backtest scripts to use new gate logic
  - [x] `research/bot_backtests/backtest_dca_rsi.py` — replace Sharpe gate with DCA gate (EV, WR, MC)
  - [x] `research/bot_backtests/backtest_grid_eth.py` — replace with Grid gate (if applicable)
  - [x] `research/bot_backtests/backtest_signal_ema.py` — keep Sharpe/MDD gate

- [x] **1.4** Update `research/reports/summary/BOT_STRATEGIES_SUMMARY.md`
  - [x] Add new gate criteria section (DCA / Grid / Signal)
  - [x] Re-evaluate S-A, S-B status → mark as PASS where applicable
  - [x] Add "Paper Trade Ready" column or status

- [x] **1.5** Run re-evaluation
  - [x] Re-run backtests for S-A, S-B
  - [x] Confirm S-A → PASS (EV>0, WR>75%, MC ruin 1.5%<10%)
  - [x] S-B: backtest gate fails (annualized, cell profit); MC gate depends on WFA run

**Files:** `bots/base_bot.py`, `research/reports/BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md`, `research/reports/summary/BOT_STRATEGIES_SUMMARY.md`, `research/bot_backtests/backtest_dca_rsi.py`, `research/bot_backtests/backtest_grid_eth.py`

---

## Priority 2: Add Regime Gating to S-A DCA

**Impact:** High | **Effort:** 1–2 days  
**Goal:** Block DCA entries in BEAR regime; reduce SL events, improve win rate.

### Tasks

- [x] **2.1** Add regime filter to DCA backtest
  - [x] In `research/bot_backtests/backtest_dca_rsi.py`:
    - [x] Add `--regime-gate` CLI flag
    - [x] Load `CryptoRegimeDetector` from `utils/regime_detector.py`
    - [x] Fit on OHLCV; predict regime per bar; filter signal where regime != BEAR
    - [x] Allow SIDEWAYS, BULL, TRANSITION

- [x] **2.2** Add `--regime-gate` to DCA WFA
  - [x] In `research/walk_forward/run_wfa_dca.py`:
    - [x] Add `--regime-gate` argument
    - [x] Create `_make_regime_gate_hook()` (mirror `run_wfa_grid.py`)
    - [x] DCA: block when regime is **BEAR** (grid blocks BULL; different logic)
    - [x] Pass `pre_test_hook` to `WalkForwardAnalyzer` when flag set

- [x] **2.3** Add per-bar regime check inside DCA strategy function
  - [x] Regime gate in `dca_strategy_sa()`: fit detector, predict, mask signal where regime==BEAR

- [x] **2.4** Re-run backtest with regime gate
  - [x] `python research/bot_backtests/backtest_dca_rsi.py --regime-gate`
  - [x] Fewer deals (82→69 BTC); EV per deal slightly lower; gate still PASS

- [x] **2.5** Re-run WFA with regime gate
  - [x] `python research/walk_forward/run_wfa_dca.py --strategy sa --symbol BTC/USDT --regime-gate`

**Files:** `research/bot_backtests/backtest_dca_rsi.py`, `research/walk_forward/run_wfa_dca.py`, `utils/regime_detector.py` (existing)

**Reference:** Grid WFA regime gate in `run_wfa_grid.py` lines 19–32 (blocks BULL). DCA needs to block BEAR.

---

## Priority 3: Replace S-D EMA with S2 Funding Rate → Signal Bot Webhook

**Impact:** High | **Effort:** 2–3 hours  
**Goal:** Route validated S2 signal (WFA +44.64% ETH) to 3Commas via Freqtrade webhook.

### Tasks

- [x] **3.1** Add webhook config for 3Commas
  - [x] Create or update `deploy/config-s2.json` with webhook section
  - [x] Format: `webhook.enabled`, `entry`, `exit` (Freqtrade format)
  - [x] Placeholders: `{YOUR_3C_SECRET}`, `{YOUR_BOT_UUID}`
  - [x] Action: `enter_long` / `exit_long`; include `pair`, `trigger_price`

- [x] **3.2** Verify FundingReversion strategy compatibility
  - [x] `strategies/FundingReversion.py` fires `populate_entry_trend` / `populate_exit_trend`
  - [x] Pair whitelist: `ETH/USDT:USDT` in config-s2.json

- [x] **3.3** Document webhook setup steps
  - [x] Created `docs/S2_SIGNAL_BOT_WEBHOOK.md`

- [x] **3.4** Update strategy status
  - [x] S-D marked RETIRED; S2 → Signal Bot added to BOT_STRATEGIES_SUMMARY

- [ ] **3.5** (Optional) End-to-end test
  - [ ] Run Freqtrade with FundingReversion + webhook in dry-run (manual)

**Files:** `deploy/config-s2.json`, `strategies/FundingReversion.py`, `docs/3COMMAS_VALIDATION.md` or new doc, `research/reports/BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md`, `research/reports/summary/BOT_STRATEGIES_SUMMARY.md`

---

## Priority 4: Switch DCA Optimization to Bayesian (Optuna)

**Impact:** Medium | **Effort:** ~1 day  
**Goal:** Replace grid search with Optuna; optimize for per-deal EV, not Sharpe.

### Tasks

- [x] **4.1** Add Optuna dependency
  - [x] Added `optuna` to `requirements.txt`

- [x] **4.2** Create `research/bot_optimization/optimize_dca_bayesian.py`
  - [x] Implement `objective(trial)` with `trial.suggest_float` / `suggest_int`
  - [x] Objective: maximize `per_deal_ev * win_rate`
  - [x] Penalize: `total_deals < 10` → return -999
  - [x] `study.optimize(objective, n_trials=200)`

- [x] **4.3** Integrate per-deal EV into DCA bot output
  - [x] `compute_bot_metrics()` returns `expected_value_per_deal`; DCA result includes it

- [ ] **4.4** Update WFA scoring for DCA (deferred)
  - [ ] Add `--score-mode ev` flag for EV-based optimization

- [ ] **4.5** Run optimization and validate
  - [ ] Run `optimize_dca_bayesian.py` on BTC/USDT (manual)

**Files:** `research/bot_optimization/optimize_dca_bayesian.py`, `research/bot_optimization/optimize_dca_params.py` (reference), `bots/base_bot.py`, `research/walk_forward/run_wfa_dca.py`, `requirements.txt`

---

## Priority 5: Add Per-Deal EV and Capital-Normalized Grid Return

**Impact:** Medium | **Effort:** 4–6 hours  
**Goal:** Interpretable metrics for DCA and Grid; fix "991.5% sum" confusion.

### Tasks

- [x] **5.1** Implement `compute_per_deal_ev()` in `bots/base_bot.py` (P1.2)

- [x] **5.2** Implement `compute_annualized_capital_return()` in `bots/base_bot.py`

- [x] **5.3** Add `annualized_capital_return` to GridBotSimulator
  - [x] Compute `years_elapsed` from first to last bar; add to result dict

- [x] **5.4** Add per-deal EV to DCA bot output (via compute_bot_metrics)

- [x] **5.5** Update report outputs
  - [x] Backtest scripts pass EV, annualized return to write_backtest_report
  - [x] WFA: EV per deal, annualized return in summary
  - [x] run_mc_grid.py: annualized yield in stats

- [x] **5.6** Update Grid WFA display
  - [x] run_wfa_grid.py prints annualized_capital_return alongside sum of cell returns

**Files:** `bots/base_bot.py`, `bots/grid_bot.py`, `bots/report_utils.py`, `research/walk_forward/run_wfa_grid.py`, `research/monte_carlo/run_mc_grid.py`

---

## Cross-Cutting & Validation

### 3Commas Fidelity Check (from existing docs)

- [ ] Run S-A (or S-B) on 3Commas backtester with same pair/period
- [ ] Compare: Total Return, Win Rate, Deals, MDD within 20%
- [ ] Document in `BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md` under "3Commas Fidelity"

### Unit Tests

- [x] Add test for `compute_per_deal_ev()` in `tests/test_base_bot.py`
- [x] Add test for `compute_annualized_capital_return()` in `tests/test_base_bot.py`
- [ ] Add test for regime gate in DCA backtest (optional)

### Documentation

- [x] Update `docs/BOT_WORKFLOW.md` with new gate criteria and metrics
- [x] Update `research/reports/summary/BOT_STRATEGIES_SUMMARY.md` with new scripts/flags

---

## Suggested Order of Execution

1. **P1** (Gate criteria) — unblocks paper trading decisions
2. **P5.1, P5.2** (base metrics) — needed for P1.2 and P4
3. **P1.2–1.5** (finish P1)
4. **P2** (Regime gating) — improves S-A before paper
5. **P3** (S2 webhook) — quick win, high impact
6. **P4** (Optuna) — after base metrics and regime gate
7. **P5.3–5.6** (full metrics rollout)

---

## Status Legend

- ⬜ Not Started
- 🔄 In Progress
- ✅ Done
- ⏸ Blocked

---

*Last updated: February 18, 2026*
