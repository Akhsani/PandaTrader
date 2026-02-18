# PandaTrader — Current State Analysis
**Date:** February 2026 | **Based on:** Updated BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md + codebase review

---

## What's Actually Done (Confirmed Against Code)

All five priorities in IMPROVEMENT_PLAN_PROGRESS_TRACKER.md are marked ✅ Done, and the code confirms most of it:

- `compute_per_deal_ev()` and `compute_annualized_capital_return()` exist in `bots/base_bot.py` ✅
- Tests for both functions exist and pass ✅
- DCA/Grid/Signal gate criteria differentiated in reports ✅
- `--regime-gate` added to `backtest_dca_rsi.py` and `run_wfa_dca.py` ✅
- `optimize_dca_bayesian.py` created with Optuna, EV×win_rate objective ✅
- S-D marked RETIRED, `deploy/config-s2.json` created with webhook config ✅
- `annualized_capital_return` added to `GridBotSimulator.run()` ✅

**Three tasks remain incomplete** despite being marked done, and one finding from the results is counterintuitive enough to require direct attention.

---

## Problem 1: The Regime Gate Is Hurting S-A, Not Helping It

This is the most urgent finding in the current results. Comparing S-A with and without regime gate:

| Variant | WFA OOS Return | Trades | MC Ruin | MC Gate |
|---|---|---|---|---|
| S-A (no gate) | **81.66%** | 41 | **2.10%** | ✅ PASS |
| S-A (regime gate) | 43.34% | 31 | **12.70%** | ❌ FAIL |

The regime gate was supposed to reduce risk by blocking BEAR entries. Instead, it:
- Cut OOS return by 47% (81.66% → 43.34%)
- Raised MC ruin probability by 6× (2.10% → 12.70%)
- Made the strategy *fail* its MC gate

This is counterintuitive and needs a clear explanation before the gated version is used for anything.

**Why the MC ruin went up, not down:** The MC validator resamples the actual WFA OOS trades. Without the gate, you have 41 trades to reshuffle — a reasonable sample for MC. With the gate, you have only 31 trades. Fewer trades means: (a) less diversification within each MC simulation path, (b) any single bad trade has more weight, and (c) the gap between the worst few trades and the average is a bigger fraction of the portfolio. The regime gate removed 10 trades, but those 10 trades were likely not the losers — RSI DCA mean-reversion in sideways markets (which the gate allows) generates wins; the gate was probably blocking some of these sideways entries that happened to be labeled BEAR by the detector.

**The likely root cause:** `CryptoRegimeDetector` may be labeling some profitable sideways/recovery setups as BEAR because the daily HMM sees trending features that don't reflect the local oversold condition the DCA is actually exploiting. The 1H RSI < 20 fires specifically when price has dropped sharply — this can occur during regime transitions or late-stage BEAR periods when mean reversion actually succeeds.

**Decision:** Use S-A without regime gate for paper trading. The non-gated version passes all gates and has 4× better MC profile. The gated version is worth further investigation (longer data, different detector thresholds) but should not be the paper trading configuration.

**Action required in `BOT_STRATEGIES_SUMMARY.md`:** Change the "S-A DCA + regime-gate" MC row from ambiguous to explicit FAIL, and confirm the non-gated S-A as the paper trading candidate.

---

## Problem 2: S-B Grid Simulation Has a Methodology Bug

This explains why S-B shows -1.1% annualized return and 47.1% MC ruin despite being structurally sound. Looking at `grid_bot.py` `run()` directly:

```python
# Stop bot
if self.stop_bot_price is not None:
    if low <= self.stop_bot_price:
        # Close open buys at loss
        ...
        open_buys = {}
        self.equity_curve.append(initial_capital + total_profit)
        continue   # ← bot keeps running next bar with same grid range
```

After hitting `stop_bot_price`, the code clears `open_buys` and `continue`s. On the very next bar, if price crosses any level, it starts placing new buys again with the **same grid range**. The bot silently restarts itself without capital adjustment or range reset.

In reality, 3Commas halts the bot when `stop_bot_price` is triggered. A human then re-evaluates the market, sets a fresh grid range reflecting current prices, and manually restarts. The simulation is modelling a zombie bot that keeps running a stale grid after being stopped.

**Compounding this:** The grid range in `backtest_grid_eth.py` is calculated from `df["high"].rolling(120).max()` and `df["low"].rolling(120).min()` — evaluated at the **end** of the dataset (Feb 2026 prices). This range (~$1,897–$2,107) is then applied retroactively to the entire 2-year backtest starting Feb 2024, when ETH was trading at completely different levels ($2,000–$4,000 during the 2024 bull run). The grid is fundamentally wrong for most of the backtest period.

**What's actually happening in the 780 closed deals / 47.1% MC ruin:**
- The fixed Feb-2026-calibrated grid repeatedly intersects with historical ETH prices that are either far above the range (in-range sells never trigger, just buys accumulate) or below the stop (stop events occur, losses locked, then bot phantom-restarts)
- The 780 deals include many partial cycles from a miscalibrated grid
- MC ruin of 47.1% reflects resampling losses from these phantom-restart cycles

**The fix is a two-part change to `backtest_grid_eth.py`:**

Part A — Set the grid range from the START of the test period, not the end:
```python
# Current (wrong): uses rolling window ending at the last bar
roll_high = df["high"].rolling(120).max().iloc[-1]
roll_low = df["low"].rolling(120).min().iloc[-1]

# Fix: compute range from first 120 days, simulating what you'd set at bot launch
warmup = df.iloc[:120]
upper = float(warmup["high"].max())
lower = float(warmup["low"].min())
```

Part B — Stop trading after a stop event (add a `stopped` flag to the simulation loop):
```python
# In GridBotSimulator.run(), after the stop block:
if self.stop_bot_price is not None:
    if low <= self.stop_bot_price:
        # ... close open buys at loss ...
        open_buys = {}
        break  # ← change continue to break; bot stops permanently after stop event
```

The `break` better reflects 3Commas behavior. It means the backtest measures one continuous grid deployment, not an infinite sequence of phantom restarts. The WFA already handles this correctly — each WFA window is a fresh deployment, which is why the WFA metrics may be more reliable than the single backtest.

**Until this is fixed, the S-B backtest results are unreliable and should not be used for deployment decisions.** The fact that S-B's backtest and MC are both failing is not evidence the strategy is bad — it's evidence the simulation is measuring the wrong thing.

---

## Problem 3: Three Tasks From the Tracker Are Not Actually Complete

### P4.4 — WFA EV Scoring (explicitly marked "deferred")

The tracker shows:
```
- [ ] 4.4 Update WFA scoring for DCA (deferred)
      [ ] Add --score-mode ev flag for EV-based optimization
```

The WFA in `run_wfa_dca.py` still uses the 2-combo --fast grid and the `WalkForwardAnalyzer.optimize()` still scores by Sharpe (inherited from `walk_forward_analysis.py`). Optuna was built as a standalone script (`optimize_dca_bayesian.py`) but was never wired into the WFA loop. This means every WFA run for DCA is still optimizing toward the wrong objective with a minimal parameter grid.

This matters because the WFA OOS return of 81.66% was produced by a Sharpe-optimized 2-combo grid. It may understate or misstate the true OOS performance of the best EV-optimized parameters.

### P4.5 — Optuna Has Never Been Run on Real Data

The tracker:
```
- [ ] 4.5 Run optimization and validate
      [ ] Run optimize_dca_bayesian.py on BTC/USDT (manual)
```

`optimize_dca_bayesian.py` exists and looks correct, but it has never been executed. There are no results files in `research/bot_optimization/` for Bayesian output. The best DCA parameters in use are still the fixed defaults (TP 2.5%, SL 15%) — not derived from any optimization process at all.

### P3.5 — Webhook End-to-End Test Not Done

```
- [ ] 3.5 (Optional) End-to-end test
      [ ] Run Freqtrade with FundingReversion + webhook in dry-run (manual)
```

The webhook config exists at `deploy/config-s2.json` with correct Freqtrade format. But without actually running it, you don't know if: (a) the webhook fires correctly on signal, (b) 3Commas receives and parses the payload format, or (c) the Signal Bot executes. This is the minimum required step before S2 → 3Commas can be treated as a valid paper trading setup.

---

## Problem 4: S-C BB+RSI Has Incomplete Data in the Results Table

From the report:
```
S-C BB+RSI | BTC | -0.21 | - | - | - | - | 113 | FAIL
```

MDD, Win Rate, and EV/Deal are all blank (`-`). S-C was evaluated with the old Sharpe gate and immediately failed. With the new DCA gate, whether it passes depends entirely on EV > 0 and Win Rate > 75% — neither of which has been computed.

With 113 deals over 2 years, S-C has a substantial sample. Given that BB lower band + RSI composite creates a more selective entry signal than RSI alone, there's a reasonable prior that win rate is comparable to S-A. This is worth a 30-minute re-run to get the full metrics before permanently listing it as FAIL.

---

## What the Updated Results Actually Tell Us

Stripping out the noise:

| Strategy | Real Status | Confidence | Action |
|---|---|---|---|
| S-A (no regime gate) | ✅ Paper trade ready | High — all gates pass | Deploy on 3Commas paper |
| S-A (regime gate) | ⚠️ Do not use yet | Medium — counterintuitive MC result | Investigate detector calibration |
| S-B Grid | 🔴 Simulation broken | High — methodology flaw confirmed | Fix backtest methodology, re-run |
| S-C BB+RSI | ❓ Unknown | Low — gate data missing | Re-run with new gate criteria |
| S-D EMA Signal | ❌ Retired | High | Done |
| S2 → Signal Bot | 🔄 Config ready, not tested | Medium | Run end-to-end test (P3.5) |

---

## The Concrete Next Steps

In priority order:

**1. Paper trade S-A (non-gated) immediately.** All gates pass. 81.66% WFA OOS, 2.1% MC ruin, EV +1.54%. This is the one validated strategy ready for live paper testing. Set up on 3Commas with BTC/USDT, TP 2.5%, SL 15%, $25 BO, $30 SO × 4, start with $200 capital.

**2. Fix S-B grid simulation (2 code changes, ~30 minutes).** Change the range computation to use the first 120 bars instead of the last. Change the stop event from `continue` to `break`. Re-run backtest and MC. The result may look completely different — possibly much better — because the simulation will finally be measuring what a real grid deployment looks like.

**3. Run P3.5 — the webhook test.** Start `freqtrade trade --config deploy/config-s2.json --strategy FundingReversion --dry-run`. Watch Freqtrade logs for the first webhook fire on ETH. Confirm it arrives at 3Commas with `action: enter_long`. This is 2 hours of actual work, mostly waiting.

**4. Run Optuna (P4.5) and wire it into WFA (P4.4).** Run `python research/bot_optimization/optimize_dca_bayesian.py --symbol BTC/USDT --trials 200`. Then add a `--score-mode ev` flag to `run_wfa_dca.py` that replaces the grid search in `WalkForwardAnalyzer.optimize()` with Optuna. The 81.66% WFA result may improve significantly once optimization targets EV instead of Sharpe.

**5. Re-run S-C with full metrics.** `python research/bot_backtests/backtest_dca_bb_rsi.py` — confirm EV and win rate are populated in the output. Add it to the results table properly and gate it against DCA criteria.

---

## One Structural Observation on the Regime Gate

The regime gate result exposes something worth tracking: the `CryptoRegimeDetector` may be miscalibrated for DCA's specific use case. DCA enters on sharp local drops (RSI-7 < 20), which systematically occur during the first phase of a dump — often labeled BEAR by the macro HMM because the macro trend is down. But this is precisely when RSI mean reversion has the highest success rate if the support holds.

The regime gate is blocking entries that look bearish on a daily HMM but are actually recoverable on a 1-4H timeframe. This is a known regime detection problem: macro and micro regime labels often disagree around turning points, and turning points are exactly when RSI DCA is most profitable.

A better approach for S-A: instead of blocking entries when HMM says BEAR, add a price-relative filter — e.g., only block entries when `close < close.rolling(200).mean()` on the **1H chart** (not the daily chart). This is a simpler and more locally relevant trend filter that doesn't depend on the HMM being correctly calibrated for DCA entry timing.

---

*Files requiring changes: `bots/grid_bot.py` (stop event), `research/bot_backtests/backtest_grid_eth.py` (range computation), `research/walk_forward/run_wfa_dca.py` (EV scoring), `research/reports/summary/BOT_STRATEGIES_SUMMARY.md` (regime gate MC row)*