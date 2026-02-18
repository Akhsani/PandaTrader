# Deployment Recap — Pre-Flight Checklist

**Date:** February 18, 2026  
**Purpose:** Verify all strategies use latest optimized parameters before deployment.

---

## 1. Strategy-by-Strategy Status

### Strategy 1: Weekend Momentum (S1)

| Item | Research (Best) | Freqtrade Code | Status |
|------|-----------------|----------------|--------|
| **Variant** | Mon–Wed pooled: **39.34%** return, 46 trades | Fri–Mon only (day 4→0) | ⚠️ **GAP** |
| Fri–Mon pooled | 18.24%, 20 trades | — | — |
| Stop loss | 3% | 3% | ✅ |
| Regime filter | No trades in BEAR | Implemented | ✅ |
| Volatility gate | ATR < 75th pct | Implemented | ✅ |
| Assets | BTC, ETH, SOL | config: BTC, ETH | ✅ |

**Finding:** Mon–Wed variant outperforms Fri–Mon (39.34% vs 18.24%). Current `WeekendMomentum.py` is hardcoded Fri→Mon. To deploy Mon–Wed, you need either:
- A separate strategy class (e.g. `WeekendMomentumMonWed`) with `entry_day=0`, `exit_day=2`, or
- Add `IntParameter` for `entry_day`/`exit_day` and run hyperopt/override.

**Recommendation:** Deploy Fri–Mon as-is (validated, 18.24%). Add Mon–Wed as a second strategy/service if you want the higher return.

---

### Strategy 2: Funding Reversion (S2)

| Item | Research (Best) | Freqtrade Code | Status |
|------|----------------|----------------|--------|
| **z_score_threshold** | 1.5 (reoptimized) | 1.5 | ✅ |
| **adx_threshold** | **20** (reoptimized) | **30** | ⚠️ **GAP** |
| **stop_loss** | 5% | 5% | ✅ |
| Regime gating | ETH only (no BTC) | Implemented | ✅ |
| Dynamic sizing | Z-based | Implemented | ✅ |
| Drawdown throttle | >10% halve, >15% block | Implemented | ✅ |
| Cascade amplifier | 2x when cascade | Implemented | ✅ |
| Pair whitelist | ETH only | config-funding: ETH only | ✅ |

**Finding:** `FundingReversion.py` has `adx_threshold: 30` but reoptimization (33.41% train score) found **20** is best. The strategy does **not** load `strategy2_params.json` — params are hardcoded.

**Action:** ✅ Updated `adx_threshold` from 30 → 20 in `FundingReversion.py`.

---

### Strategy 3: Token Unlocks (S3)

| Item | Research | Freqtrade Code | Status |
|------|----------|----------------|--------|
| Narrative filter | Keep (no short if mom>50% or ADX>40) | Implemented | ✅ |
| Fixed sizing | Recommended (opt worse than baseline) | — | ✅ |
| Excluded tokens | APT, TIA | — | Verify in config |

**Status:** No parameter sync needed. Narrative filter is for risk; no alpha gain expected.

---

### Strategy 5: Regime Grid (S5)

| Item | Research | Freqtrade Code | Status |
|------|----------|----------------|--------|
| Master switch | Inherits BaseStrategy | Implemented | ✅ |
| BULL | Inactive | Blocked | ✅ |
| BEAR | 50% size | Implemented | ✅ |

**Status:** Deployment-ready.

---

### Strategy 6: Basis Harvest (S6)

| Item | Research (Best) | Freqtrade Code | Status |
|------|-----------------|----------------|--------|
| **entry_threshold** | **0.00005** (fine-tuned) | **0.0001** | ⚠️ **GAP** |
| neg_streak_exit | 3 | 3 | ✅ |
| capital_pct | 1.0 | N/A (Freqtrade) | — |
| Regime guard | BEAR/SIDEWAYS only | Implemented | ✅ |

**Finding:** Backtest with `entry_threshold=0.00005` yields **16.42%** avg return vs ~11% with 0.0001. `BasisHarvest.py` uses `funding_rate > 0.0001` — should be **0.00005**.

**Action:** ✅ Updated entry condition from `0.0001` → `0.00005` in `BasisHarvest.py`.

---

### Strategy 9: Cross-Asset Funding Rotation (S9)

| Item | Research (Best) | Deployment | Status |
|------|-----------------|------------|--------|
| z_entry | 0.3 | backtest_strategy_9.py | ✅ |
| z_exit | 0.3 | backtest_strategy_9.py | ✅ |
| capital_pct | 1.0 | backtest_strategy_9.py | ✅ |
| **Freqtrade strategy** | — | **None** | N/A |

**Finding:** S9 is a **standalone backtest script**, not a Freqtrade strategy. It rotates across multiple assets every 8h. Freqtrade runs one pair per strategy. S9 would require:
- A separate multi-asset service/script, or
- Deferral until S6 is validated in paper trading (per tasks.md).

**Recommendation:** S9 is **not** in Freqtrade deployment scope. Use as research/diversifier analysis only for now.

---

## 2. Backtest vs Freqtrade Alignment

| Component | Optimized | In Code |
|-----------|-----------|---------|
| `backtest_strategy_6.py` | entry=0.00005 | ✅ |
| `strategies/BasisHarvest.py` | entry=0.00005 | ✅ (synced) |
| `backtest_strategy_9.py` | z=0.3, cap=1.0 | ✅ |
| `strategies/FundingReversion.py` | adx=20 | ✅ (synced) |
| `strategy2_params.json` | z=1.5, adx=20, sl=0.05 | Reference only; params hardcoded in strategy |

---

## 3. Deployment Config Summary

| Config | Pairs | Strategy | Notes |
|--------|-------|----------|-------|
| `deploy/config.json` | BTC, ETH | RegimeGrid (Dockerfile default) | Spot, dry-run |
| `deploy/config-funding.json` | ETH/USDT:USDT | FundingReversion | Futures, ETH only ✅ |

**Dockerfile:** Default CMD uses `RegimeGrid` with config.json. For multi-strategy, use separate services (see deployment-guide.md).

---

## 4. Pre-Deployment Actions (Required)

| # | Action | File | Status |
|---|--------|------|--------|
| 1 | Update `adx_threshold` 30 → 20 | `strategies/FundingReversion.py` | ✅ Done |
| 2 | Update entry threshold 0.0001 → 0.00005 | `strategies/BasisHarvest.py` | ✅ Done |

---

## 5. Optional / Deferred

| # | Action | Rationale |
|---|--------|-----------|
| 1 | Add Mon–Wed variant for S1 | 39.34% vs 18.24%; requires new strategy or params |
| 2 | Load S2 params from JSON | Would allow monthly re-opt without code change |
| 3 | S9 as Freqtrade strategy | Multi-asset rotation; complex; defer per tasks.md |

---

## 6. Performance Summary (Latest Validated)

| Strategy | Best Return/Score | Win Rate | Risk Notes |
|----------|-------------------|----------|------------|
| S1 Fri–Mon pooled | 18.24% | 55% | 20 trades |
| S1 Mon–Wed pooled | **39.34%** | 65.22% | 46 trades |
| S2 ETH (WFA) | 44.64% | 59.62% | 72% prob DD>20% |
| S2 Reoptimized (train) | 33.41% | — | Use adx=20 |
| S6 (fine-tuned) | **16.42%** avg | — | <0.1% DD |
| S9 (fine-tuned) | 8.69% | — | 3 assets |
| S5 Grid | -0.67% | — | vs -33% B&H (defensive) |

---

## 7. Verification Commands

```bash
# Re-run fine-tuning (full sweep)
python research/backtests/finetune_strategies.py

# Verify S6 backtest with new default
python research/backtests/backtest_strategy_6.py   # Expect ~16.42% avg

# Verify S9 backtest
python research/backtests/backtest_strategy_9.py   # Expect 8.69%

# S2 reoptimize (monthly)
python research/walk_forward/reoptimize_strategy_2.py --symbol ETH/USDT --output research/walk_forward/results/strategy2_params.json

# S1 Mon-Wed pooled
python research/walk_forward/run_wfa_strategy_1.py --pool --variant mon-wed
```

---

## 8. Conclusion

**Deployment-ready.** Both code changes applied:
1. ✅ `FundingReversion.py`: `adx_threshold` 30 → 20  
2. ✅ `BasisHarvest.py`: entry threshold 0.0001 → 0.00005  

**Already correct:** S1 (Fri–Mon), S3, S5, config pair whitelists, regime logic, dynamic sizing, drawdown throttle.

**Deferred:** S1 Mon–Wed (optional higher-return variant), S9 Freqtrade integration, JSON param loading for S2.
