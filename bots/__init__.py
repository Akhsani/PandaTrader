"""
PandaTrader Bot Simulators — Faithful 3Commas/Pionex/Bitsgap execution models.
Build locally, backtest, optimize, export to platform config.
"""
from bots.base_bot import load_ohlcv_for_bot, FeeEngine, compute_bot_metrics
from bots.dca_bot import DCABotSimulator
from bots.grid_bot import GridBotSimulator
from bots.signal_bot import SignalBotSimulator

__all__ = [
    "load_ohlcv_for_bot",
    "FeeEngine",
    "compute_bot_metrics",
    "DCABotSimulator",
    "GridBotSimulator",
    "SignalBotSimulator",
]
