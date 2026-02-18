"""Shared funding-related utilities (S2, S6, S9)."""

# S6 Basis Harvest: single source of truth for entry threshold (Phase 3A)
ENTRY_THRESHOLD = 0.00005


def z_to_risk(z_score: float) -> float:
    """Map |Z-score| to risk per trade: Z=1.5->0.5%, Z=2.0->1.0%, Z=2.5+->1.5%"""
    if z_score is None:
        return 0.005
    try:
        z = abs(float(z_score))
    except (TypeError, ValueError):
        return 0.005
    if z >= 2.5:
        return 0.015
    if z >= 2.0:
        return 0.01
    if z >= 1.5:
        return 0.005
    return 0.005
