# EXP_003_v2: Token Unlock Refined

## 1. Hypothesis (Iteration 1)
**Observation:** Blindly shorting unlocks in a bull market is dangerous (Shorting the Trend).
**Hypothesis:** Adding a Trend Filter (ADX > 25 & Price > SMA200) to *skip* Short signals during strong uptrends will improve risk-adjusted returns by avoiding "stepping in front of a steamroller."
**Changes:**
- **Code:** `strategies/UnlockTrader.py` updated with `use_trend_filter`.
- **Logic:** If `ADX > 25` AND `Price > SMA200`, the Short signal is suppressed. Long signal (post-unlock) is taken regardless.
- **Selection:** Attempted to exclude 'ecosystem' unlocks, though in this dataset most were labeled 'investor'/'team'.

## 2. Results Comparison

| Token | V1 Return | V2 Return (Trend Filter) | Delta | Observation |
|-------|-----------|--------------------------|-------|-------------|
| **OP/USDT** | +64.85% | **+66.13%** | +1.28% | **Success.** Filter likely avoided a losing short during an uptrend. |
| **SUI/USDT** | +34.22% | +34.22% | 0.00% | No change. Trend filter not triggered. |
| **ARB/USDT** | +16.45% | +16.45% | 0.00% | No change. |
| **TIA/USDT** | -1.78% | -1.78% | 0.00% | No change. |
| **APT/USDT** | -27.15% | **-39.07%** | -11.9% | **Failure.** Filter suppressed a *profitable* short. APT was in a "technical bull trend" before crashing on the unlock. |

## 3. Analysis
1.  **The "Lagging Filter" Problem**: The APT failure highlights a critical flaw. Unlocks can *end* a bull trend. By filtering shorts based on the existing bull trend, we miss the exact pivot point we are trying to trade. When the "Cliff" arrives, the trend breaks violently. The filter kept us out of the Short, so we only took the Long (or part of the trade), resulting in worse performance.
2.  **The "Steamroller" Protection**: For OP, the filter worked as intended, slightly improving returns by avoiding a short in a strong market that didn't crash as hard.
3.  **Net Result**: Mixed. The filter adds safety but removes "top-ticking" alpha.

## 4. Conclusion
**STATUS: INCONCLUSIVE / REQUIRES TUNING**

The boolean Trend Filter (`Price > SMA200`) is too blunt.
**Recommendation:**
- Instead of completely skipping the Short, **reduce position size** by 50% when in a Bull Trend.
- Use a tighter trend invalidation (e.g., Price breaking below EMA20) as a trigger to enter the short *late* rather than skipping it entirely.

## 5. Next Steps
- Revert to V1 for now as the primary strategy (higher potential alpha).
- explore `Relative Strength` scaling rather than binary on/off filters.
