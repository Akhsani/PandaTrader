# Phase 2B & 2C: Improvement Report — What Works, What Doesn't, and Deep Analysis

**Date:** February 18, 2026  
**Scope:** Comprehensive review of Phase 2B optimizations and Phase 2C new strategies. Parameter/strategy comparisons, result validation, and actionable conclusions.

---

## Executive Summary

| Category | Working | Not Working / Mixed | Deferred |
|----------|---------|---------------------|----------|
| **Phase 2B** | Regime Master Switch, S1 WFA Expansion, S2 Drawdown Mitigation (code), S3 Narrative Filter, Cascade Detector, S5 Master Switch | S2 Regime on BTC (hurts return), S3 Optimization (no improvement), S9 Rotation (yield below S6) | S3 Market-Neutral Leg |
| **Phase 2C** | S6 Basis Harvest (low-risk carry) | S6 APY below target (5% vs 30%), S9 yield (0.76% vs S6 10.79%) | — |

---

## Part 1: Parameter & Strategy Comparison Tables

### 1.1 Strategy 1 (Weekend Momentum) — Before vs After Phase 2B

| Parameter / Metric | Pre-2B (EXP_001) | Post-2B (EXP_Phase2B) | Change |
|-------------------|------------------|----------------------|--------|
| **Assets** | BTC only (WFA) | BTC, ETH, SOL (pooled) | Expanded |
| **Stop Loss** | 5% (WFA opt) | 3% (tightened) | -2pp |
| **Regime Filter** | No | Yes (no trades in BEAR) | Added |
| **Volatility Gate** | No | ATR < 75th percentile | Added |
| **Entry/Exit** | Fri→Mon only | Fri→Mon + Mon→Wed variant | Added |
| **WFA Trades (BTC)** | 9 | 9 (unchanged) | — |
| **WFA Return (BTC)** | +20.84% | +20.84% | — |
| **WFA Win Rate (BTC)** | 77.78% | 77.78% | — |
| **Pooled Trades** | N/A | 20 (BTC 9, ETH 11) | New |
| **Pooled Return** | N/A | 18.24% | New |
| **Pooled Win Rate** | N/A | 55.00% | New |
| **Mon-Wed Return (ETH)** | N/A | 31.10% | New |
| **Mon-Wed Trades** | N/A | 30 | New |
| **Mon-Wed Win Rate** | N/A | 70.00% | New |
| **Monte Carlo Ruin (BTC)** | 6.90% | — | — |
| **Monte Carlo Ruin (Pooled)** | N/A | 19.60% | New |

**Key Finding:** Pooling increases sample size (9→20) but lowers win rate (77%→55%). Mon–Wed variant offers higher frequency (30 trades) and return (31.10%) on ETH — **worth testing further**.

---

### 1.2 Strategy 2 (Funding Reversion) — Before vs After Phase 2B

| Parameter / Metric | Pre-2B (EXP_002) | Post-2B (EXP_Phase2B) | Change |
|-------------------|------------------|----------------------|--------|
| **Risk per Trade** | Fixed 0.25% | Dynamic: Z=1.5→0.5%, Z=2.0→1.0%, Z=2.5+→1.5% | Z-based |
| **Drawdown Throttle** | No | Yes: >10% halve, >15% block | Added |
| **Cascade Amplifier** | No | Yes: 2x stake when cascade fires | Added |
| **Regime Gating** | Yes (BaseStrategy) | Yes (unchanged) | — |
| **WFA Return (ETH)** | +20.47% | +44.64% | +24.17pp |
| **WFA Trades (ETH)** | 226 | 213 | -13 |
| **WFA Win Rate (ETH)** | 58.85% | 59.62% | +0.77pp |
| **Backtest Return (ETH, regime ON)** | — | -14.98% | Fixed-param loss |
| **Backtest Return (BTC, regime ON)** | — | -33.41% | Regime hurts BTC |
| **Regime DD Improvement (ETH)** | — | -7.67pp (58.5%→50.9%) | Yes |
| **Regime DD (BTC)** | — | Worse (-48.3%→-49.5%) | No |
| **Monte Carlo Ruin** | 29.30% | 16.70% | Improved |
| **Monte Carlo Prob DD>20%** | 86.40% | 72.30% | Improved |

**Key Finding:** WFA return improved (+44.64% vs +20.47%) — likely data-period and re-optimization. Regime filter **helps ETH** (DD -7.67pp) but **hurts BTC** (return -9.7%→-33.4%). **Deploy S2 on ETH only.** Dynamic sizing and drawdown throttle are implemented but not validated in standalone backtest (backtest uses fixed logic).

---

### 1.3 Strategy 3 (Token Unlocks) — Before vs After Phase 2B

| Parameter / Metric | Pre-2B (EXP_003 v3) | Post-2B (EXP_Phase2B) | Change |
|-------------------|---------------------|----------------------|--------|
| **Narrative Filter** | No | Yes: no short if 30d mom>50% or ADX>40 | Added |
| **Graduated Sizing** | 1.5x in Bull | 1.5x (unchanged) | — |
| **Funding Cost** | -0.03% daily | -0.03% daily | — |
| **Excluded Tokens** | APT, TIA | APT, TIA | — |
| **ARB Return (Opt)** | 15.41% | 14.73% | -0.68pp |
| **OP Return (Opt)** | 64.31% | 62.64% | -1.67pp |
| **SUI Return (Opt)** | 33.02% | 32.49% | -0.53pp |
| **Avg Improvement vs Baseline** | -1.47pp | -1.34pp | Similar |

**Key Finding:** Narrative filter **does not improve returns** — it reduces shorts in strong momentum, which may avoid some losses but also misses some profitable shorts. Optimization (graduated sizing + funding cost) **still fails** to beat baseline. **Fixed sizing recommended.**

---

### 1.4 Strategy 5 (Regime Grid) — Before vs After Phase 2B

| Parameter / Metric | Pre-2B (EXP_005) | Post-2B (EXP_Phase2B) | Change |
|-------------------|------------------|----------------------|--------|
| **Inheritance** | IStrategy | BaseStrategy | Master Switch |
| **Regime Source** | Local HMM in RegimeGrid | Portfolio-level (2B.1) | Centralized |
| **S5 in BULL** | No action | Inactive (blocked) | Explicit |
| **S5 in BEAR** | Cash preservation | 50% position size | Refined |
| **Buy & Hold** | -28.90% | -33.09% | Different period |
| **Grid Return (v1)** | -11.18% (orig) / 1.34% (v2 run) | -0.60% | Data drift |
| **Grid Return (v2)** | 0.24% (prior run) | -0.67% | Data drift |

**Key Finding:** Master switch integration is **correct**. Grid still reduces drawdown vs Buy & Hold. Return variance across runs suggests **test-period sensitivity** — bear market data yields different results.

---

### 1.5 Strategy 6 (Basis Harvest) — Phase 2C New

| Parameter / Metric | Target (Plan) | Actual (EXP_006) | Gap |
|-------------------|---------------|------------------|-----|
| **APY** | 30%+ | ~5.22% | **-25pp** |
| **Max Drawdown** | <5% | <0.1% | Exceeded (better) |
| **Sharpe** | >2.0 | Not computed | — |
| **Logic** | Long spot, short perp, 8h funding | Implemented | Match |
| **Exit** | 3 consecutive negative funding | Implemented | Match |
| **Regime Guard** | BEAR/SIDEWAYS only | Implemented | Match |

**Key Finding:** Yield **far below target** (5% vs 30% APY). Drawdown is excellent. Likely causes: (1) funding rates in test period were modest, (2) basis inversion exit may be too conservative, (3) capital deployment assumption in backtest may be conservative.

---

### 1.6 Strategy 9 (Cross-Asset Funding) — Phase 2C New

| Parameter / Metric | Target | Actual (EXP_009) | Gap |
|-------------------|--------|------------------|-----|
| **Yield vs S6** | Improve over single-asset | 0.76% vs S6 10.79% | **Worse** |
| **Universe** | 10 assets | 3 (BTC, ETH, SOL) | Partial |
| **Z-Score Window** | 30 days | 90 periods (8h) | ~30 days |
| **Entry Threshold** | Z > 0.5 | Z > 0.5 | Match |
| **Exit Threshold** | Z < 0.5 | Z < 0.5 | Match |

**Key Finding:** Rotation **underperforms** single-asset S6. Possible causes: (1) 3-asset universe too small, (2) Z-thresholds need tuning, (3) rotation logic may over-trade or under-capture funding.

---

## Part 2: What Works

### 2.1 Regime Master Switch (2B.1)
- **Status:** Working
- **Evidence:** 7/7 unit tests pass. Logic correctly gates S1/S2/S3/S5 by regime. S5 gets 50% size in BEAR.
- **Recommendation:** Deploy. Centralizes regime logic across strategies.

### 2.2 S1 WFA Expansion (2B.2)
- **Status:** Working
- **Evidence:** Pooled WFA yields 20 trades (vs 9 BTC-only), 18.24% return. Mon–Wed variant: 30 trades, 31.10% return, 70% win rate on ETH.
- **Recommendation:** Use pooled OOS for Monte Carlo. Consider Mon–Wed as higher-frequency alternative.

### 2.3 S2 Drawdown Mitigation — Code (2B.3)
- **Status:** Implemented, partial validation
- **Evidence:** Z-based sizing and drawdown throttle coded. Monte Carlo improved (Ruin 29%→17%, Prob DD>20% 86%→72%). Regime filter reduces ETH DD by 7.67pp.
- **Caveat:** Standalone backtest still shows negative return on fixed params. WFA validates edge; use monthly re-optimization.

### 2.4 S3 Narrative Filter (2B.4)
- **Status:** Working as designed
- **Evidence:** Filter prevents shorts when 30d momentum > 50% or ADX > 40. No return improvement vs baseline.
- **Recommendation:** Keep for risk reduction; do not expect alpha from it.

### 2.5 Cascade as S2 Amplifier (2B.5)
- **Status:** Implemented, unit-tested
- **Evidence:** 4/4 cascade detector tests pass. CascadeBounce standalone: ETH +3.84%, 87.5% win rate.
- **Caveat:** Cascade amplifier effect on S2 not isolated in backtest (S2 backtest does not use Freqtrade with cascade).

### 2.6 S5 Master Switch (2B.6)
- **Status:** Working
- **Evidence:** RegimeGrid inherits BaseStrategy. Grid reduces loss vs Buy & Hold.
- **Recommendation:** Deploy as defensive overlay.

### 2.7 S6 Basis Harvest (2C)
- **Status:** Working, yield below target
- **Evidence:** ~10.8% return, ~5.2% APY, <0.1% DD. Low risk, suitable as diversifier.
- **Recommendation:** Use as portfolio stabilizer; do not rely on 30% APY.

---

## Part 3: What Doesn't Work / Mixed Results

### 3.1 S2 Regime Filter on BTC
- **Issue:** Regime gating **worsens** BTC: -9.70% (baseline) → -33.41% (filtered).
- **Cause:** BTC funding reversion may work better without regime filter in this period; filter removes profitable trades.
- **Action:** **Do not run S2 on BTC.** ETH only.

### 3.2 S3 Optimization (Graduated Sizing + Funding Cost)
- **Issue:** Optimized return **below** baseline for all tokens. Narrative filter does not improve returns.
- **Cause:** Funding drag outweighs 1.5x long sizing. Narrative filter reduces opportunity set.
- **Action:** Fixed sizing. Keep narrative filter for risk; accept no alpha gain.

### 3.3 S6 APY vs Target
- **Issue:** 5% APY vs 30% target.
- **Cause:** Test-period funding rates, conservative exit (3 neg funding), or capital deployment assumption.
- **Action:** Research: relax exit rule, test different periods, or accept lower yield.

### 3.4 S9 Cross-Asset Rotation
- **Issue:** 0.76% return vs S6 10.79% single-asset.
- **Cause:** Small universe (3 assets), possible over-rotation or suboptimal Z thresholds.
- **Action:** Expand to 10 assets, tune Z entry/exit, compare to S6.

---

## Part 4: Deep Analysis

### 4.1 Backtest vs WFA Discrepancy (S2)
- **Observation:** Fixed-param backtest ETH -14.98% vs WFA +44.64%.
- **Interpretation:** S2 edge is **parameter- and time-sensitive**. WFA re-optimizes every 30 days; fixed params from one period fail in another.
- **Implication:** For live/paper: **monthly re-optimization** via `reoptimize_strategy_2.py` is essential.

### 4.2 Sample Size and Statistical Significance (S1)
- **Pre-2B:** 9 BTC trades — too few for robust inference.
- **Post-2B:** 20 pooled trades — better but still below 60+ target.
- **Mon–Wed:** 30 ETH trades — closer to target.
- **Implication:** Pooling and Mon–Wed improve inference. Continue pooling for Monte Carlo.

### 4.3 Regime Filter Asymmetry (S2)
- **ETH:** Regime helps (DD -7.67pp). Longs blocked in BEAR, shorts in BULL — aligns with funding mean reversion in chop.
- **BTC:** Regime hurts. Possible structural difference: BTC funding may trend more, ETH may mean-revert more.
- **Implication:** Asset-specific regime sensitivity. Do not assume one-size-fits-all.

### 4.4 S6 vs S9 Yield Gap
- **S6:** Single-asset, hold through positive funding, exit on 3 neg. Simple, captures funding carry.
- **S9:** Rotate to highest Z. More turnover, may miss extended funding regimes, or Z-score may be noisy.
- **Implication:** Rotation adds complexity without proven benefit. Simplify S9 or increase universe before deployment.

### 4.5 Portfolio Diversification
- **Correlation:** S1_BTC, S2_ETH, S3_ARB near zero correlation. Good for portfolio construction.
- **Combined:** 12.25% return, -6.24% DD, Sharpe 0.79 (one run). Prior run: 16.63%, -6.39% DD, Sharpe 1.05.
- **Implication:** Diversification holds. Use Strat2_ETH (not BTC) in portfolio.

### 4.6 Monte Carlo Risk Summary
| Strategy | Ruin Prob | Prob DD>20% | Median Equity ($1k start) |
|----------|-----------|-------------|----------------------------|
| S1 BTC (9 trades) | 6.90% | 0.20% | $1,214 |
| S1 Pooled (20 trades) | 19.60% | 16.20% | $1,191 |
| S2 ETH (213 trades) | 16.70% | 72.30% | $1,437 |

- **S1:** Pooling increases risk (more trades, more variance). BTC-only was very safe but tiny sample.
- **S2:** High DD risk (72% prob >20% DD) — **deploy with strict position sizing and drawdown throttle.**

---

## Part 5: Recommendations Summary

| Item | Action |
|------|--------|
| **S1** | Use pooled WFA for validation. Test Mon–Wed variant in paper trading. |
| **S2** | ETH only. Monthly re-optimization. Dynamic sizing + drawdown throttle deployed. |
| **S3** | Fixed sizing. Keep narrative filter. Exclude APT, TIA. |
| **S5** | Deploy with master switch. Defensive overlay. |
| **S6** | Deploy as low-risk diversifier. Accept ~5% APY. |
| **S9** | Do not deploy until 10-asset test and tuning complete. |
| **Regime Master Switch** | Deploy. Central to risk management. |

---

## Part 6: Experiment Cross-Reference

| Experiment | Phase 2B/2C Component | Key Result |
|------------|----------------------|------------|
| EXP_001 | S1 WFA | 9 trades BTC, 77% win rate |
| EXP_001_v2 | S1 multi-asset | 223→109 trades (vol gate), 56→61% win rate |
| EXP_Phase2B | S1 pooled, Mon–Wed | 20 pooled, 18.24%; 30 Mon–Wed, 31.10% |
| EXP_002 | S2 ETH | WFA +20.47%, MC ruin 29% |
| EXP_Phase2B | S2 2B.3 | WFA +44.64%, MC ruin 17%, regime helps ETH |
| EXP_003_v3 | S3 optimization | Opt worse than baseline |
| EXP_Phase2B | S3 narrative | Filter added, no return improvement |
| EXP_004 | CascadeBounce | ETH +3.84%, low frequency |
| EXP_Phase2B | Cascade detector | Extracted, S2 amplifier |
| EXP_005 | S5 Regime Grid | -11% vs -29% B&H |
| EXP_Phase2B | S5 master switch | -0.67% grid vs -33% B&H |
| EXP_006 | S6 Basis | 10.79% return, 5.22% APY |
| EXP_009 | S9 Rotation | 0.76% return, underperforms S6 |
| **EXP_FineTuning_Results** | **S6, S9, S2, S1** | **S6: 16.42% (entry=0.00005); S9: 8.69% (z=0.3, cap=1.0); S2: 33.41% train; S1 Mon-Wed pooled: 39.34%** |
