# PandaTrader Bot Simulators

Faithful 3Commas/Pionex/Bitsgap execution models. Build locally, backtest, optimize, export to platform config.

**Reports:** [BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md](../research/reports/BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md) | [BOT_STRATEGIES_SUMMARY.md](../research/reports/summary/BOT_STRATEGIES_SUMMARY.md) | [BOT_WORKFLOW.md](../docs/BOT_WORKFLOW.md)

## Architecture

```
Market Data → Python Bot Simulator → Backtest / WFA / Monte Carlo
                                           ↓
                              Optimized Parameter Dict
                                           ↓
                         Paste into 3Commas / Pionex / Bitsgap UI
```

## Bot Types

- **DCA Bot** (`dca_bot.py`): Base order + safety orders, martingale step/volume, TP/SL
- **Grid Bot** (`grid_bot.py`): Geometric/arithmetic grid, trailing up, expansion down
- **Signal Bot** (`signal_bot.py`): TV-style signals, single entry, TP/SL, trailing stop

## Quick Start

```bash
# Backtest S-A RSI DCA
python research/bot_backtests/backtest_dca_rsi.py

# Walk-Forward Analysis
python research/walk_forward/run_wfa_dca.py --strategy sa --symbol BTC/USDT

# Monte Carlo
python research/monte_carlo/run_mc_dca.py --strategy sa --symbol BTC/USDT

# Parameter optimization
python research/bot_optimization/optimize_dca_params.py --symbol BTC/USDT
```

## Export to 3Commas

```python
from bots.export_config import export_to_3commas

params = {"base_order_volume": 25, "safety_order_volume": 30, ...}
config = export_to_3commas(params, bot_type="dca")
# Use config to fill 3Commas bot creation form
```

## Parameter Reference

See `PARAM_REFERENCE.md` for full 3Commas parameter list.

## Tests

```bash
pytest tests/test_dca_bot.py tests/test_grid_bot.py tests/test_signal_bot.py -v
```
