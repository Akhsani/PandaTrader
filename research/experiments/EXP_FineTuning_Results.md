# Fine-Tuning Results — Per Improvement Report Recommendations

**Date:** February 18, 2026  
**Script:** `research/backtests/finetune_strategies.py`

---

## Executive Summary

| Strategy | Before Fine-Tune | After Fine-Tune | Best Params |
|----------|------------------|-----------------|-------------|
| **S6** | ~5% APY, 10.79% return | **16.42% return, 7.90% APY** | neg_exit=3, entry=0.00005, cap=1.0 |
| **S9** | 0.76% return | **8.69% return, 4.54% APY** | z_entry=0.3, z_exit=0.3, cap=1.0 |
| **S2** | Fixed params (varies) | **33.41% train score** | z=1.5, adx=20, sl=0.05 |
| **S1 Mon-Wed** | 31.10% (30 trades) | **39.34% (46 trades)** | Pooled BTC+ETH+SOL |

---

## 1. S6 Basis Harvest — Fine-Tuning

**Recommendation:** Relax exit rule (3→4–6 neg funding), lower entry threshold, tune capital deployment.

### Parameter Sweep

| neg_exit | entry_thresh | cap_pct | Avg Return | Avg APY |
|----------|--------------|---------|------------|---------|
| 3 | 0.00005 | 1.0 | **16.42%** | **7.90%** |
| 4 | 0.00005 | 1.0 | 16.35% | 7.87% |
| 5 | 0.00005 | 1.0 | 16.28% | 7.83% |
| 6 | 0.00005 | 1.0 | 16.22% | 7.80% |
| 6 | 0.0001 | 1.0 | 13.02% | 6.31% |
| 6 | 0.0002 | 1.0 | 12.89% | 6.25% |

### Findings

- **Lower entry threshold (0.00005 vs 0.0001)** yields ~3–5pp higher return — more entries capture more funding.
- **Relaxing exit (4–6 neg)** slightly reduces return vs 3 — staying in longer during inversion hurts.
- **Best:** `neg_exit=3`, `entry_threshold=0.00005`, `capital_pct=1.0` → **16.42% return, 7.90% APY** (vs baseline ~5% APY).

### Action

Update `BasisHarvest` / backtest defaults: `entry_threshold=0.00005`, keep `neg_streak_exit=3`.

---

## 2. S9 Cross-Asset Funding Rotation — Fine-Tuning

**Recommendation:** Tune Z entry/exit, increase capital deployment.

### Parameter Sweep

| z_entry | z_exit | cap_pct | Return | APY |
|---------|--------|---------|--------|-----|
| 0.3 | 0.3 | 1.0 | **8.69%** | **4.54%** |
| 0.5 | 0.3 | 1.0 | 8.25% | 4.31% |
| 0.3 | 0.5 | 1.0 | 8.20% | 4.29% |
| 0.5 | 0.5 | 1.0 | 7.85% | 4.11% |
| 0.7 | 0.3 | 1.0 | 7.63% | 4.00% |
| 0.7 | 0.5 | 1.0 | 7.26% | 3.81% |

### Findings

- **Lower Z thresholds** (0.3 entry, 0.3 exit) outperform — more rotation, more funding capture.
- **Full capital deployment (cap=1.0)** beats 0.5 and 0.2.
- **Before:** 0.76% return (Z=0.5, cap=0.1). **After:** 8.69% return — **~11x improvement**.
- Still below S6 single-asset (16.42%) but viable as a diversifier.

### Action

Update S9 defaults: `z_entry=0.3`, `z_exit=0.3`, `capital_pct=1.0`. Consider expanding to 10 assets for further gains.

---

## 3. S2 Funding Reversion — Re-Optimization

**Recommendation:** Run `reoptimize_strategy_2.py` monthly; use optimized params for paper trading.

### Re-Optimization Result (ETH, 180d train)

| Param | Value |
|-------|-------|
| z_score_threshold | 1.5 |
| adx_threshold | 20 |
| stop_loss | 0.05 |
| **Training score** | **33.41%** |

### Action

Params saved to `research/walk_forward/results/strategy2_params.json`. Use for paper trading until next monthly re-optimization.

---

## 4. S1 Pooled Mon-Wed — Walk-Forward

**Recommendation:** Run pooled Mon–Wed for more trades and validation.

### Result

| Metric | Value |
|--------|-------|
| **Total Return** | **39.34%** |
| **Win Rate** | 65.22% |
| **Trades** | 46 |
| By symbol | BTC: 6, ETH: 30, SOL: 10 |

### Comparison

| Variant | Trades | Return | Win Rate |
|---------|--------|--------|----------|
| Fri–Mon pooled (prior) | 20 | 18.24% | 55% |
| Mon–Wed ETH only (prior) | 30 | 31.10% | 70% |
| **Mon–Wed pooled (now)** | **46** | **39.34%** | **65.22%** |

Mon–Wed pooled improves over prior runs: more trades (46 vs 20/30) and higher return (39.34% vs 18.24%/31.10%).

---

## 5. Summary of Chosen Parameters

| Strategy | Parameter | New Value |
|----------|-----------|-----------|
| S6 | entry_threshold | 0.00005 |
| S6 | neg_streak_exit | 3 (unchanged) |
| S6 | capital_pct | 1.0 |
| S9 | z_entry | 0.3 |
| S9 | z_exit | 0.3 |
| S9 | capital_pct | 1.0 |
| S2 | z_score_threshold | 1.5 |
| S2 | adx_threshold | 20 |
| S2 | stop_loss | 0.05 |
| S1 | variant | mon-wed pooled |

---

## 6. Files Updated / Created

- `research/backtests/finetune_strategies.py` — fine-tuning script
- `research/walk_forward/results/strategy2_params.json` — S2 optimized params
- `research/walk_forward/results/wfa_strat1_pooled_mon-wed.csv` — S1 Mon–Wed pooled trades
