"""
Export optimized params to 3Commas / Pionex / Bitsgap API format.
"""
from typing import Optional

PLATFORM_CONFIGS = {
    "3commas": {
        "fee": 0.001,
        "futures_fee": 0.0005,
        "min_order": 10,
        "trailing_up_supported": True,
        "max_safety_orders": 200,
    },
    "pionex": {
        "fee": 0.0005,
        "min_order": 1,
        "trailing_up_supported": False,
        "max_grid_lines": 200,
    },
    "bitsgap": {
        "fee": 0.001,
        "platform_fee_pct": 0.003,
        "trailing_up_supported": True,
        "expiry_date_supported": True,
    },
    "cryptohopper": {
        "fee": 0.001,
        "allocation_mode": "percentage",
        "max_buy_count": 8,
    },
}


def export_to_3commas(optimized_params: dict, bot_type: str) -> dict:
    """
    Convert local simulator output to 3Commas API-compatible JSON.
    """
    if bot_type == "dca":
        return {
            "name": optimized_params.get("name", "PandaTrader DCA Bot"),
            "base_order_volume": str(optimized_params.get("base_order_volume", 25)),
            "safety_order_volume": str(optimized_params.get("safety_order_volume", 30)),
            "take_profit": str(optimized_params.get("take_profit_percentage", 2.5)),
            "safety_order_step_percentage": str(
                optimized_params.get("safety_order_step_percentage", 0.75)
            ),
            "martingale_volume_coefficient": str(
                optimized_params.get("martingale_volume_coefficient", 2.0)
            ),
            "martingale_step_coefficient": str(
                optimized_params.get("martingale_step_coefficient", 1.5)
            ),
            "max_safety_orders": str(optimized_params.get("max_safety_orders", 4)),
            "active_safety_orders_count": str(
                optimized_params.get("max_active_safety_trades_count", 4)
            ),
            "trailing_enabled": str(
                optimized_params.get("trailing_take_profit", False)
            ).lower(),
            "trailing_deviation": str(
                optimized_params.get("trailing_take_profit_deviation", 0.5)
            ),
            "stop_loss_percentage": str(
                optimized_params.get("stop_loss_percentage", 0)
            ),
        }
    elif bot_type == "grid":
        return {
            "upper_price": str(optimized_params.get("upper_price", "")),
            "lower_price": str(optimized_params.get("lower_price", "")),
            "quantity_per_grid_line": str(
                optimized_params.get("quantity_per_grid_line", "")
            ),
            "grids_quantity": str(optimized_params.get("grid_lines_count", 20)),
            "investment": str(optimized_params.get("investment_amount", 1000)),
            "grid_type": optimized_params.get("grid_type", "geometric"),
            "trailing_enabled": str(
                optimized_params.get("trailing_up", False)
            ).lower(),
        }
    return {}


def export_to_platform(
    optimized_params: dict,
    bot_type: str,
    platform: str = "3commas",
) -> dict:
    """Export for specified platform."""
    if platform == "3commas":
        return export_to_3commas(optimized_params, bot_type)
    # Pionex/Bitsgap use similar structure; platform-specific tweaks
    base = export_to_3commas(optimized_params, bot_type)
    config = PLATFORM_CONFIGS.get(platform, PLATFORM_CONFIGS["3commas"])
    return {**base, "_platform_fee": config.get("fee", 0.001)}
