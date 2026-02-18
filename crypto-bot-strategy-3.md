# 3Commas Local Simulation & Platform Expansion Playbook
## PandaTrader — Develop Locally, Deploy Anywhere

---

## Executive Summary

**Yes, this workflow is not only doable — it is the correct professional approach.** The core idea is to build a `bots/` simulation layer inside PandaTrader that faithfully replicates each platform's exact parameter logic in Python, so every backtest, WFA, and Monte Carlo run produces results that translate *directly* into platform config values with no guesswork.

The workflow:
```
Market Data → Python Bot Simulator → Backtest / WFA / Monte Carlo
                                           ↓
                              Optimized Parameter Dict
                                           ↓
                         Paste into 3Commas / Pionex / Bitsgap UI
```

This is essentially what PandaTrader already does for Freqtrade strategies. You are extending the same methodology to cover GUI-based platforms. The key discipline: **the simulator must be a faithful model of the platform's actual execution logic**, not a generic backtest engine.

---

## Implementation Status (February 2026)

| Strategy | Status | Sharpe | Win Rate | Gate |
|----------|--------|--------|----------|------|
| S-A RSI DCA | Realistic | 0.26 (BTC) | 95.1% | FAIL |
| S-B Grid ETH | Realistic | -0.06 | 97.4% | FAIL |
| S-C BB+RSI | Tested | -0.16 | - | FAIL |
| S-D EMA Signal | Gate Failed | -0.38 | 52.4% | FAIL |
| S-E Grid Reversal | Tested | -0.08 | - | FAIL |

*Realistic: DCA stop_loss 15%; Grid stop_bot 10% below lower. Win rates no longer 100% (was due to no SL).

**Full results:** [research/reports/BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md](research/reports/BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md)  
**Workflow:** [docs/BOT_WORKFLOW.md](docs/BOT_WORKFLOW.md)

---

## Part 1: Complete 3Commas Parameter Reference

### 1.1 DCA Bot — Full Parameter List

These are every parameter available in the 3Commas DCA bot as of 2025, organized by section.

#### Deal Start (Entry) Parameters
| Parameter | Type | Range / Options | Notes |
|---|---|---|---|
| `bot_name` | string | any | Label only |
| `strategy` | enum | `long`, `short` | Short requires futures |
| `pairs` | list[string] | e.g. `["USDT_BTC"]` | Multi-pair supported |
| `max_active_deals` | int | 1–200 | Per-pair deal limits apply |
| `deal_start_condition` | enum | `asap`, `manual`, `signal`, `indicator` | |
| `start_order_type` | enum | `limit`, `market` | |
| `indicator_name` | enum | `rsi`, `bb`, `macd`, `cci`, `stoch`, `ema_crossover`, `qfl`, `custom_signal`, `tv_screener` | When using built-in indicators |
| `indicator_period` | int | 7–200 | For RSI, BB, etc. |
| `indicator_value` | float | indicator-dependent | e.g. RSI threshold = 30 |
| `indicator_timeframe` | enum | `1m`,`3m`,`5m`,`15m`,`30m`,`1h`,`2h`,`4h`,`1d` | |
| `cooldown_between_deals` | int | 0–N seconds | Prevents rapid re-entry |
| `min_volume_btc_24h` | float | 0–∞ | Filter pairs by 24h volume |
| `deal_start_timeout_enabled` | bool | true/false | Auto-close if deal doesn't start |
| `deal_start_timeout_in_seconds` | int | 60–N | |

#### Base Order Parameters
| Parameter | Type | Range | Notes |
|---|---|---|---|
| `base_order_volume` | float | exchange min – ∞ | In quote currency (USDT) |
| `base_order_volume_type` | enum | `quote_currency`, `base_currency`, `percent_of_available_balance`, `xbt` | |

#### Safety Order Parameters
| Parameter | Type | Range | Notes |
|---|---|---|---|
| `safety_order_volume` | float | exchange min – ∞ | First SO size |
| `safety_order_volume_type` | enum | same as base order | |
| `max_safety_orders` | int | 0–200 | Total SOs allowed |
| `max_active_safety_trades_count` | int | 0–200 | SOs open simultaneously |
| `safety_order_step_percentage` | float | 0.01–99.0% | Price deviation to trigger first SO |
| `martingale_volume_coefficient` | float | 1.0–10.0 | Volume scale (SO multiplier) |
| `martingale_step_coefficient` | float | 1.0–10.0 | Step scale (deviation multiplier) |
| `use_stop_loss_order` | bool | | |
| `stop_loss_percentage` | float | 0.01–99.0% | % below avg price |
| `stop_loss_type` | enum | `stop_loss`, `stop_loss_and_cancel_bot` | |
| `sl_to_breakeven_enabled` | bool | | Move SL to entry after first TP hit |
| `trailing_stop_loss` | bool | | |
| `trailing_stop_loss_percentage` | float | 0.01–99.0% | |

#### Custom Safety Order Ladder (Beta — Price Ladder)
| Parameter | Type | Notes |
|---|---|---|
| `custom_price_deviation_levels` | list[float] | Manual deviation % per SO level |
| `custom_order_size_levels` | list[float] | Manual USDT size per SO level |

#### Take Profit Parameters
| Parameter | Type | Range | Notes |
|---|---|---|---|
| `take_profit_percentage` | float | 0.01–999.0% | From average entry price |
| `take_profit_steps` | list[dict] | up to 4 (web), 8 (JSON) | Multi-target TP |
| `take_profit_steps[].percentage` | float | | TP target level |
| `take_profit_steps[].volume_percentage` | float | sum must = 100 | % of position closed at this level |
| `trailing_take_profit` | bool | | Trailing on last TP step |
| `trailing_take_profit_deviation` | float | 0.01–99.0% | Reversal % to trigger trailing close |
| `close_deal_timeout_enabled` | bool | | Auto-close deal after time |
| `close_deal_timeout_in_seconds` | int | 60–N | |

#### Risk / Lifecycle Parameters
| Parameter | Type | Notes |
|---|---|---|
| `reinvesting_percentage` | float | 0–100% of profit auto-reinvested |
| `risk_reduction_percentage` | float | % of profit used to reduce SO volume |
| `stop_bot_after_deals_reached` | int | Bot auto-stops after N deals |
| `bot_status` | enum | `enabled`, `disabled` | |

#### Futures-specific Parameters
| Parameter | Type | Range | Notes |
|---|---|---|---|
| `leverage_type` | enum | `cross`, `isolated` | |
| `leverage_custom_value` | int | 1–125 | Set on Binance directly; 3C reads it |
| `strategy_list[short]` | bool | Enables short selling | Futures only |

---

### 1.2 Grid Bot — Full Parameter List

| Parameter | Type | Range / Options | Notes |
|---|---|---|---|
| `pair` | string | e.g. `BTC_USDT` | Single pair per bot |
| `account_id` | int | | Linked exchange account |
| `grid_type` | enum | `arithmetic`, `geometric` | |
| `strategy` | enum | `classic`, `reversal`, `rising`, `to_the_moon`, `falling` | |
| `upper_price` | float | > lower_price | Upper boundary of grid |
| `lower_price` | float | > 0 | Lower boundary |
| `quantity_per_grid_line` | float | exchange min | Per-level order size (arithmetic) |
| `investment_amount` | float | | Total USDT deployed (geometric) |
| `grid_lines_count` | int | 2–150 | Number of grid levels |
| `max_active_buy_lines` | int | 1–grid_lines | Open buy orders at once |
| `trailing_up` | bool | | Geometric only: extends upper bound |
| `expansion_down` | bool | | Extends lower bound on drop |
| `auto_adjust_size` | bool | | Rebalances order size at boundaries |
| `leverage` | int | 1–125 | Futures only |
| `margin_type` | enum | `cross`, `isolated` | Futures only |
| `stop_bot_price` | float | | Price at which bot stops (hard stop) |
| `close_all_orders_on_stop` | bool | | Whether to close positions on stop |
| `ai_range_detection` | bool | | AI-suggested price range (120-day) |
| `ai_step_optimization` | bool | | Requires 50+ grid lines |
| `profit_currency` | enum | `base_currency`, `quote_currency` | |

---

### 1.3 Signal Bot — Full Parameter List

| Parameter | Type | Options | Notes |
|---|---|---|---|
| `bot_name` | string | any | |
| `account_id` | int | | Linked exchange |
| `exchange` | string | e.g. `Binance Spot` | Must match TV alert |
| `pairs` | list[string] | | Subscribed pairs |
| `position_size` | float | USDT | Per-signal position size |
| `position_size_type` | enum | `quote_currency`, `percent_balance` | |
| `leverage` | int | 1–125 | Futures only |
| `margin_type` | enum | `cross`, `isolated` | Futures only |
| `take_profit_steps` | list[dict] | up to 8 via JSON | |
| `stop_loss_percentage` | float | 0.01–99% | |
| `trailing_stop_loss` | bool | | |
| `trailing_stop_loss_percentage` | float | | |
| `signal_type` | enum | `tradingview`, `custom` | |
| `webhook_url` | string | 3C-generated | Paste into TradingView |
| `secret` | string | 3C-generated | Included in webhook JSON payload |
| `max_lag_seconds` | int | 0–N | Drops signal if latency exceeded |
| `delay_seconds` | int | 0–60 | Wait before executing (prevents conflicts) |
| `close_on_opposite_signal` | bool | | Auto-close long on short signal |

#### Signal Bot Webhook JSON Schema
```json
{
  "secret": "{{YOUR_SECRET}}",
  "bot_uuid": "{{YOUR_BOT_UUID}}",
  "action": "enter_long",         // enter_long | enter_short | exit_long | exit_short | panic_sell
  "trigger_price": "{{close}}",   // TradingView placeholder
  "timestamp": "{{timenow}}",
  "pair": "USDT_BTC",
  "base": "BTC",
  "quote": "USDT",
  "order_size": "100",            // optional: overrides default
  "max_lag": "60",                // optional: max acceptable delay (seconds)
  "take_profit": [                // optional: override TP for this signal
    {"volume_percentage": 50, "percentage": 1.5},
    {"volume_percentage": 50, "percentage": 3.0}
  ]
}
```

---

## Part 2: Strategy Ideas to Test

Organized from highest to lowest local simulation priority.

### Tier 1 — High Evidence, Build First

| # | Strategy Name | Bot Type | Pairs | Hypothesis |
|---|---|---|---|---|
| S-A | RSI Oversold DCA | DCA | BTC, ETH, SOL | RSI-7 < 20 triggers entry; mean reversion to TP 2.5% |
| S-B | Geometric Sideways Grid | Grid (geometric) | ETH/USDT | Oscillation harvesting in 20% range |
| S-C | BB Lower Band + RSI Composite DCA | DCA + TV Signal | BTC, ETH | Dual-confirmation entry; lower false signal rate |
| S-D | EMA 12/26 Trend DCA | DCA + TV Signal | BTC | Long only when EMA12 > EMA26 on 1H; DCA on pullbacks |

### Tier 2 — Moderate Evidence, Build Second

| # | Strategy Name | Bot Type | Pairs | Hypothesis |
|---|---|---|---|---|
| S-E | Futures Grid BTC 2x Reversal | Grid (reversal) | BTC/USDT perp | Both directions within range; 2x leverage amplification |
| S-F | Heikin Ashi DCA Entry | DCA | ETH | HA candle color change signals exhaustion; smoother entries |
| S-G | ATR Volatility Breakout | Signal Bot + TV | BTC, ETH | ATR > 1.5×ATR_SMA20 + directional EMA filter triggers entry |
| S-H | QFL Base Break DCA | DCA (QFL mode) | BTC, ETH | Quick Fingers Luc: buys 5% below historical support clusters |
| S-I | MACD Histogram Flip DCA | DCA | ETH, SOL | MACD histogram crosses zero from below; momentum entry |

### Tier 3 — Exploratory, Build Third

| # | Strategy Name | Bot Type | Pairs | Hypothesis |
|---|---|---|---|---|
| S-J | Stochastic Oversold Multi-SO | DCA | ALTs | Stochastic < 20 entry; deeper SO ladder for ALT volatility |
| S-K | Parabolic SAR Reversal | Signal Bot | BTC | SAR flip below price = entry; above price = exit |
| S-L | Multi-Timeframe RSI Pyramid | DCA | BTC | RSI oversold on 4H + 15m double confirmation; aggressive SO pyramid |
| S-M | Grid on ETH with Trailing Up | Grid (geometric) | ETH/USDT | Trailing Up enabled to ride uptrend while grid profits from swings |

### Cross-referencing with Existing PandaTrader Strategies

| PandaTrader Strategy | Closest 3Commas Equivalent | Synergy Notes |
|---|---|---|
| S1 Weekend Momentum | S-D EMA DCA (signal bot) | S1 fires Fri entry; DCA averages in on Sat dips |
| S2 Funding Reversion | S-C BB+RSI DCA | Both are mean reversion; run when funding extreme |
| S5 RegimeGrid | S-B / S-E Grid bots | Regime detection layer → enable/disable grid manually |
| S4 CascadeBounce | S-H QFL DCA | QFL is the closest native 3C approximation |
| S6 BasisHarvest | Not feasible in 3C | Keep in Freqtrade |

---

## Part 3: Local Simulation Architecture

### 3.1 New Directory Structure

Add a `bots/` directory to PandaTrader alongside existing `strategies/`:

```
~/crypto-bot/
├── bots/                          ← NEW: 3Commas bot simulators
│   ├── base_bot.py                ← Shared: OHLCV feed, fee engine, position tracker
│   ├── dca_bot.py                 ← DCA Bot simulator (faithful 3C parameter model)
│   ├── grid_bot.py                ← Grid Bot simulator
│   ├── signal_bot.py              ← Signal Bot simulator (consumes TV-like signals)
│   └── export_config.py           ← Converts optimized params → 3Commas JSON
├── research/
│   ├── backtests/                 ← Existing strategy backtests
│   ├── bot_backtests/             ← NEW: bot simulation backtests
│   │   ├── backtest_dca_rsi.py
│   │   ├── backtest_grid_eth.py
│   │   └── backtest_signal_ema.py
│   ├── bot_optimization/          ← NEW: parameter sweeps
│   │   ├── optimize_dca_params.py
│   │   └── optimize_grid_range.py
│   ├── walk_forward/              ← Existing WFA (extend for bots)
│   └── monte_carlo/               ← Existing MC (extend for bots)
├── strategies/                    ← Existing Freqtrade strategies (untouched)
└── utils/
    └── regime_detector.py         ← Existing (used as gate for bot activation)
```

### 3.2 DCA Bot Simulator Core Design

```python
# bots/dca_bot.py

class DCABotSimulator:
    """
    Faithful simulation of 3Commas DCA Bot logic.
    All parameter names match 3Commas API exactly for direct export.
    """
    def __init__(self, params: dict):
        # --- Entry ---
        self.base_order_volume = params['base_order_volume']              # USDT
        self.safety_order_volume = params['safety_order_volume']          # USDT (first SO)
        self.max_safety_orders = params['max_safety_orders']              # int
        self.safety_order_step_percentage = params['safety_order_step_percentage']  # % deviation
        self.martingale_volume_coefficient = params['martingale_volume_coefficient']  # SO size multiplier
        self.martingale_step_coefficient = params['martingale_step_coefficient']      # SO step multiplier
        # --- Exit ---
        self.take_profit_percentage = params['take_profit_percentage']    # % from avg entry
        self.trailing_take_profit = params.get('trailing_take_profit', False)
        self.trailing_take_profit_deviation = params.get('trailing_take_profit_deviation', 0.5)
        self.stop_loss_percentage = params.get('stop_loss_percentage', None)
        # --- Deal management ---
        self.max_active_deals = params.get('max_active_deals', 1)
        self.cooldown_between_deals = params.get('cooldown_between_deals', 0)
        # --- Fees ---
        self.fee = params.get('fee', 0.001)   # 0.1% Binance Spot default
        # --- State ---
        self.active_deals = []
        self.closed_deals = []
        self.equity_curve = []

    def _calculate_so_levels(self, entry_price):
        """Pre-compute all safety order trigger prices and sizes."""
        levels = []
        deviation = self.safety_order_step_percentage / 100
        size = self.safety_order_volume
        cumulative_deviation = 0
        for i in range(self.max_safety_orders):
            cumulative_deviation += deviation * (self.martingale_step_coefficient ** i)
            trigger = entry_price * (1 - cumulative_deviation)
            levels.append({'trigger': trigger, 'size': size, 'index': i})
            size *= self.martingale_volume_coefficient
        return levels

    def _calculate_tp_price(self, avg_price):
        return avg_price * (1 + self.take_profit_percentage / 100)

    def run(self, ohlcv: pd.DataFrame, signal_series: pd.Series = None) -> dict:
        """
        ohlcv: DataFrame with columns [open, high, low, close, volume]
        signal_series: boolean Series aligned to ohlcv index (True = open new deal)
        Returns: performance metrics dict matching 3Commas display format
        """
        capital = sum(
            self.base_order_volume +
            sum(l['size'] for l in self._calculate_so_levels(1.0))
            for _ in range(self.max_active_deals)
        )  # Capital reservation estimate
        
        # ... simulation loop ...
        # Key fidelity points:
        # - Limit orders fill at next-candle open (not current close)
        # - SO triggers checked against candle LOW (conservative)
        # - TP triggers checked against candle HIGH
        # - Trailing TP: track highest high after TP level hit; close on reversal
        # - Fee applied to each fill (buy and sell separately)
        # - Cooldown: block new deal opening for N seconds after close
        
        return {
            'total_profit_pct': ...,
            'max_drawdown': ...,
            'sharpe_ratio': ...,
            'win_rate': ...,
            'total_deals': ...,
            'avg_deal_duration_hours': ...,
            'max_capital_deployed': ...,
            # Export-ready params:
            'optimized_params': {k: v for k, v in self.__dict__.items()
                                if not k.startswith('_') and 
                                k not in ['active_deals', 'closed_deals', 'equity_curve']}
        }
```

### 3.3 Grid Bot Simulator Core Design

```python
# bots/grid_bot.py

class GridBotSimulator:
    """
    Faithful simulation of 3Commas Geometric Grid Bot.
    """
    def __init__(self, params: dict):
        self.upper_price = params['upper_price']
        self.lower_price = params['lower_price']
        self.investment_amount = params['investment_amount']   # Total USDT (geometric)
        self.grid_lines_count = params['grid_lines_count']
        self.grid_type = params.get('grid_type', 'geometric') # arithmetic | geometric
        self.trailing_up = params.get('trailing_up', False)
        self.expansion_down = params.get('expansion_down', False)
        self.stop_bot_price = params.get('stop_bot_price', None)
        self.fee = params.get('fee', 0.001)
        self.leverage = params.get('leverage', 1)
        
    def _build_grid(self):
        """Build price levels. Geometric: equal % spacing. Arithmetic: equal $ spacing."""
        if self.grid_type == 'geometric':
            ratio = (self.upper_price / self.lower_price) ** (1 / self.grid_lines_count)
            levels = [self.lower_price * (ratio ** i) for i in range(self.grid_lines_count + 1)]
        else:
            step = (self.upper_price - self.lower_price) / self.grid_lines_count
            levels = [self.lower_price + step * i for i in range(self.grid_lines_count + 1)]
        return sorted(levels)

    def _profit_per_grid(self, level_low, level_high):
        """Profit per completed buy-sell cycle at adjacent grid levels."""
        order_size = self.investment_amount / self.grid_lines_count
        buy_cost = order_size * (1 + self.fee)
        sell_proceeds = order_size * (level_high / level_low) * (1 - self.fee)
        return sell_proceeds - buy_cost

    def run(self, ohlcv: pd.DataFrame) -> dict:
        """
        Simulates grid fills bar by bar.
        - Each bar: check if price crossed any grid level (both up and down)
        - Profit locked on each complete buy→sell cycle
        - Trailing Up: when price closes above upper_price, extend grid upward
        - Stop: if price crosses stop_bot_price, close all open buy positions at loss
        """
        # ... simulation loop ...
        pass
```

### 3.4 Parameter Optimization Loop

```python
# research/bot_optimization/optimize_dca_params.py

from bots.dca_bot import DCABotSimulator
from itertools import product
import pandas as pd

def grid_search_dca(ohlcv, signal_series, param_grid):
    """
    Exhaustive grid search over DCA parameters.
    Returns sorted results DataFrame.
    """
    results = []
    keys = list(param_grid.keys())
    for combo in product(*param_grid.values()):
        params = dict(zip(keys, combo))
        bot = DCABotSimulator(params)
        metrics = bot.run(ohlcv, signal_series)
        results.append({**params, **metrics})
    
    df = pd.DataFrame(results)
    df = df.sort_values('sharpe_ratio', ascending=False)
    return df

# Example param grid for RSI DCA strategy
PARAM_GRID = {
    'base_order_volume': [20, 25, 30],
    'safety_order_volume': [25, 30, 40],
    'max_safety_orders': [3, 4, 5],
    'safety_order_step_percentage': [0.5, 0.75, 1.0, 1.5],
    'martingale_volume_coefficient': [1.5, 2.0, 2.25, 2.5],
    'martingale_step_coefficient': [1.0, 1.5, 2.0],
    'take_profit_percentage': [1.5, 2.0, 2.5, 3.0],
    'trailing_take_profit': [True, False],
    'trailing_take_profit_deviation': [0.3, 0.5],
    'fee': [0.001]
}
```

### 3.5 Walk-Forward Analysis for Bots

Extend the existing WFA framework:

```python
# research/walk_forward/run_wfa_dca.py
# Same structure as run_wfa_strategy_1.py but uses DCABotSimulator

def run_wfa_dca(ohlcv, signal_series, param_grid,
                train_periods=60, test_periods=20, step=10):
    """
    Rolling window: optimize params on train window, test on next window.
    Identical methodology to existing strategy WFAs.
    """
    windows = []
    for start in range(0, len(ohlcv) - train_periods - test_periods, step):
        train = ohlcv.iloc[start:start + train_periods]
        test = ohlcv.iloc[start + train_periods:start + train_periods + test_periods]
        
        # Optimize on train
        best_params = grid_search_dca(train, signal_series[train.index], param_grid).iloc[0]
        
        # Test on OOS
        bot = DCABotSimulator(best_params.to_dict())
        oos_metrics = bot.run(test, signal_series[test.index])
        windows.append({'train_sharpe': best_params['sharpe_ratio'], **oos_metrics})
    
    return pd.DataFrame(windows)
```

### 3.6 Config Export to 3Commas

```python
# bots/export_config.py

def export_to_3commas(optimized_params: dict, bot_type: str) -> dict:
    """
    Convert local simulator output → 3Commas API-compatible JSON.
    Use this output to fill the 3Commas bot creation form.
    """
    if bot_type == 'dca':
        return {
            "name": optimized_params.get('name', 'PandaTrader DCA Bot'),
            "strategy_list": [{"options": {}, "strategy": optimized_params['strategy']}],
            "base_order_volume": str(optimized_params['base_order_volume']),
            "safety_order_volume": str(optimized_params['safety_order_volume']),
            "take_profit": str(optimized_params['take_profit_percentage']),
            "safety_order_step_percentage": str(optimized_params['safety_order_step_percentage']),
            "martingale_volume_coefficient": str(optimized_params['martingale_volume_coefficient']),
            "martingale_step_coefficient": str(optimized_params['martingale_step_coefficient']),
            "max_safety_orders": str(optimized_params['max_safety_orders']),
            "active_safety_orders_count": str(optimized_params.get('max_active_safety_trades_count', optimized_params['max_safety_orders'])),
            "trailing_enabled": str(optimized_params.get('trailing_take_profit', False)).lower(),
            "trailing_deviation": str(optimized_params.get('trailing_take_profit_deviation', 0.5)),
            "stop_loss_percentage": str(optimized_params.get('stop_loss_percentage', 0)),
        }
    elif bot_type == 'grid':
        return {
            "upper_price": str(optimized_params['upper_price']),
            "lower_price": str(optimized_params['lower_price']),
            "quantity_per_grid_line": str(optimized_params.get('quantity_per_grid_line', '')),
            "grids_quantity": str(optimized_params['grid_lines_count']),
            "investment": str(optimized_params['investment_amount']),
            "grid_type": optimized_params.get('grid_type', 'geometric'),
            "trailing_enabled": str(optimized_params.get('trailing_up', False)).lower(),
        }
```

---

## Part 4: Validated Build Sequence

### Phase A: Foundation (Week 1–2)

1. Build `bots/base_bot.py` — OHLCV loader, fee engine, equity tracker, performance metrics (Sharpe, MDD, Sortino, Win Rate, Avg Duration). Reuse `utils/data_loader.py` and `utils/risk_manager.py`.
2. Build `bots/dca_bot.py` — full parameter fidelity test against 3Commas backtester. Run the same pair/period on both and verify results within 20%.
3. Build `research/bot_backtests/backtest_dca_rsi.py` — S-A: RSI DCA on BTC/ETH/SOL.
4. Run WFA on S-A using existing WFA framework adapted for DCABotSimulator.

### Phase B: Grid Simulator (Week 2–3)

1. Build `bots/grid_bot.py` — geometric and arithmetic modes, Trailing Up, Expansion Down.
2. Build `research/bot_backtests/backtest_grid_eth.py` — S-B: ETH geometric grid.
3. Optimize grid range: sweep upper/lower price relative to current price (±10%, ±15%, ±20%, ±25%) and grid count (10, 15, 20, 30).

### Phase C: Signal Bot Bridge (Week 3–4)

1. Build `bots/signal_bot.py` — consumes indicator signals (same RSI/BB signals PandaTrader generates) and executes SmartTrade-style entries with TP/SL.
2. Connect existing PandaTrader indicator outputs as signal feeds.
3. Build `research/bot_backtests/backtest_signal_ema.py` — S-D: EMA crossover.

### Phase D: Optimization & Export (Ongoing)

1. Run full parameter grid search across S-A through S-D.
2. WFA each surviving strategy.
3. Monte Carlo each WFA-validated strategy (reuse `research/monte_carlo/`).
4. Export optimized params via `export_config.py`.
5. Set up in 3Commas paper mode and compare live vs simulated results.

---

## Part 5: Platform Comparison — Extend the Same Workflow

### Decision Framework

| Dimension | 3Commas | Pionex | Bitsgap | Cryptohopper | Gunbot |
|---|---|---|---|---|---|
| **Monthly cost** | $20–$140 | Free (0.05% fee) | $29–$99 | $19–$107 | One-time ~$200 |
| **Hosting** | Cloud | Cloud | Cloud | Cloud | Self-hosted |
| **Grid Bot** | ✅ Advanced | ✅ Excellent | ✅ Good | ✅ Basic | ✅ |
| **DCA Bot** | ✅ Deepest | ✅ Basic | ✅ Good | ✅ Good | ✅ |
| **Signal/Webhook** | ✅ TV webhook | ❌ | ✅ TV webhook | ✅ TV webhook | ✅ |
| **Futures** | ✅ Pro+ only | ✅ | ✅ | ✅ | ✅ |
| **Backtesting** | ✅ Built-in | ❌ | ✅ Built-in | ✅ Built-in | ❌ |
| **Multi-pair DCA** | ✅ | ❌ | ✅ | ✅ | ✅ |
| **Binance support** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Open API** | ✅ REST API | ❌ | ❌ | ✅ | Local only |
| **Best for** | DCA depth | Grid efficiency | Mid-complexity | Marketplace | Max control |

### Pionex — Best for Grid Bots at Zero Subscription Cost

Pionex charges no subscription fee — only a flat 0.05% trading fee (half of Binance's 0.1%). This fundamentally changes the profitability math for grid bots at small capital. A $500 grid bot needs to return 0% to cover platform cost (versus 10% on 3Commas Pro).

**Simulating Pionex parameters locally:**
Pionex grid bots are simpler than 3Commas — no trailing up, no geometric vs arithmetic choice exposed at the same depth. Key parameters:

| Parameter | Pionex Name | Notes |
|---|---|---|
| `upper_price` | Upper Limit | |
| `lower_price` | Lower Limit | |
| `grid_count` | Grid Number | 2–200 |
| `total_investment` | Investment | |
| `trigger_price` | Trigger Price | Optional: start when price hits trigger |
| `stop_loss` | Stop-Loss | |
| `take_profit` | Take-Profit | Bot stops and sells if price exceeds this |
| `leverage` | Leverage | Futures version only |

**Workflow:** Use the same `GridBotSimulator` with a `platform='pionex'` flag that sets fee to 0.0005 and disables trailing_up. Same backtest, same WFA, same MC — just different config export.

### Bitsgap — Best Middle Ground with Built-in Backtesting

Bitsgap supports 25+ exchanges, has a backtester for DCA and Grid bots, and costs $29–$99/month. Its COMBO bot combines DCA + Grid logic. Relevant for cross-platform comparison because it generates backtest data you can validate your local simulator against.

**Key Bitsgap-specific parameters:**
- `expiry_date` — bot auto-stops on a date (useful for event-driven strategies like token unlocks)
- `take_profit_type` — can be set to a fixed price rather than percentage
- COMBO bot: grid in a lower zone + DCA accumulation above

**Workflow:** Export same optimized params from local simulator, translate to Bitsgap's interface via their parameter naming map.

### Cryptohopper — Best Marketplace + TradingView Integration

$19/month (Pioneer) gets TradingView webhook access. Strategy Marketplace has copier bots. Best for Signal Bot strategies since the TV integration is polished.

**Key Cryptohopper-specific parameters:**
- `allocation_percentage` — % of available balance per signal (vs fixed USDT in 3C)
- `dollar_cost_avg` — separate DCA module with fixed-interval (time-based) or dip-based modes
- `trailing_stop_loss` — built-in native support (3Commas added this later)
- `max_buy_count` — equivalent to max_safety_orders

**Workflow:** Signal bot simulator output translates well. Key difference: Cryptohopper uses allocation_percentage by default, so convert fixed USDT sizes to % of balance before exporting.

### Platform-Specific Simulation Flags

```python
# bots/export_config.py (extended)

PLATFORM_CONFIGS = {
    '3commas': {
        'fee': 0.001,           # Binance Spot with BNB discount
        'futures_fee': 0.0005,  # Binance Futures maker
        'min_order': 10,        # USDT
        'trailing_up_supported': True,
        'max_safety_orders': 200,
    },
    'pionex': {
        'fee': 0.0005,          # Pionex flat fee
        'min_order': 1,
        'trailing_up_supported': False,
        'max_grid_lines': 200,
    },
    'bitsgap': {
        'fee': 0.001,           # Exchange fee (Bitsgap charges 0.3% on top)
        'platform_fee_pct': 0.003,
        'trailing_up_supported': True,
        'expiry_date_supported': True,
    },
    'cryptohopper': {
        'fee': 0.001,
        'allocation_mode': 'percentage',  # vs 3commas 'fixed_usdt'
        'max_buy_count': 8,
    }
}
```

---

## Part 6: Recommended Master Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: Define strategy hypothesis and parameter grid          │
│  (strategy_ideas.md, this document)                             │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: Run backtest with DCABotSimulator / GridBotSimulator   │
│  python research/bot_backtests/backtest_dca_rsi.py              │
│  → Sharpe, MDD, Win Rate, Avg Duration                          │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓ (only if Sharpe > 1.0)
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: Parameter optimization (grid search)                   │
│  python research/bot_optimization/optimize_dca_params.py        │
│  → Top 10 param combos ranked by Sharpe                         │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 4: Walk-Forward Analysis                                  │
│  python research/walk_forward/run_wfa_dca.py                    │
│  → OOS Sharpe, Degradation Ratio, Stability Score              │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓ (only if OOS Sharpe > 0.8)
┌─────────────────────────────────────────────────────────────────┐
│  STEP 5: Monte Carlo Validation                                 │
│  python research/monte_carlo/run_monte_carlo.py (adapted)       │
│  → Prob of ruin, 95% VaR, worst-case drawdown                  │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 6: Export optimized params                                │
│  python bots/export_config.py --platform 3commas --bot dca      │
│  → 3Commas-ready JSON + human-readable config card             │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 7: Paper trade on platform (3Commas / Pionex / Bitsgap)  │
│  Minimum 4 weeks. Compare live vs simulated metrics weekly.    │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓ (if live within 70% of simulated)
┌─────────────────────────────────────────────────────────────────┐
│  STEP 8: Live micro-deploy ($100–200 per bot)                  │
│  Monitor. Re-optimize monthly. Re-WFA quarterly.               │
└─────────────────────────────────────────────────────────────────┘
```

### Gate Criteria Summary

| Gate | Criterion | Action if Failed |
|---|---|---|
| Post-backtest | Sharpe > 1.0, MDD < 25% | Iterate parameters or drop strategy |
| Post-optimization | Top params stable across multiple combos | Flag overfit risk |
| Post-WFA | OOS Sharpe > 0.8, degradation < 40% | More data or wider param search |
| Post-Monte Carlo | Prob of ruin < 20%, 95% VaR acceptable | Reduce position size or SOs |
| Post-paper | Live results within 70% of simulated | Investigate slippage / market change |

---

## Part 7: Implementation Priority

| Priority | Task | Est. Effort |
|---|---|---|
| 🔴 **P1** | Build `bots/dca_bot.py` with full parameter fidelity | 2–3 days |
| 🔴 **P1** | Backtest S-A (RSI DCA) and validate against 3Commas backtester | 1 day |
| 🟡 **P2** | Build `bots/grid_bot.py` (geometric mode first) | 2 days |
| 🟡 **P2** | Backtest S-B (ETH Grid) | 1 day |
| 🟡 **P2** | Extend WFA framework for bot simulators | 1–2 days |
| 🟢 **P3** | Build `bots/signal_bot.py` | 2 days |
| 🟢 **P3** | Parameter optimizer (grid search) for DCA | 1 day |
| 🟢 **P3** | Build `bots/export_config.py` with multi-platform support | 1 day |
| ⚪ **P4** | Pionex parameter mapping + fee model | 1 day |
| ⚪ **P4** | Bitsgap parameter mapping | 1 day |
| ⚪ **P4** | Cryptohopper parameter mapping | 1 day |

Total to first deployable bot (S-A on 3Commas): **~1 week of focused work.**
Total to full multi-platform framework: **3–4 weeks.**

---

*Generated: February 2026 | PandaTrader Project*