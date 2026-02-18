# 3Commas Parameter Reference

## DCA Bot

| Parameter | Type | Range | Notes |
|-----------|------|-------|-------|
| base_order_volume | float | exchange min – ∞ | USDT |
| safety_order_volume | float | exchange min – ∞ | First SO size |
| max_safety_orders | int | 0–200 | Total SOs allowed |
| safety_order_step_percentage | float | 0.01–99.0 | % deviation to trigger SO |
| martingale_volume_coefficient | float | 1.0–10.0 | SO size multiplier |
| martingale_step_coefficient | float | 1.0–10.0 | Step deviation multiplier |
| take_profit_percentage | float | 0.01–999.0 | % from avg entry |
| trailing_take_profit | bool | | Trailing on TP |
| trailing_take_profit_deviation | float | 0.01–99.0 | Reversal % to close |
| stop_loss_percentage | float | 0.01–99.0 | Optional SL |
| max_active_deals | int | 1–200 | Per-pair limit |
| cooldown_between_deals | int | 0–N | Seconds between deals |
| fee | float | | e.g. 0.001 for Binance |

## Grid Bot

| Parameter | Type | Range | Notes |
|-----------|------|-------|-------|
| upper_price | float | > lower_price | Upper boundary |
| lower_price | float | > 0 | Lower boundary |
| investment_amount | float | | Total USDT |
| grid_lines_count | int | 2–150 | Number of levels |
| grid_type | enum | geometric, arithmetic | Spacing type |
| trailing_up | bool | | Extend upper on breakout |
| expansion_down | bool | | Extend lower on drop |
| stop_bot_price | float | | Hard stop |
| fee | float | | e.g. 0.001 |

## Signal Bot

| Parameter | Type | Notes |
|-----------|------|-------|
| position_size | float | USDT per signal |
| take_profit_percentage | float | % from entry |
| stop_loss_percentage | float | % from entry |
| trailing_stop_loss | bool | |
| trailing_stop_loss_percentage | float | Reversal % |
| fee | float | |
