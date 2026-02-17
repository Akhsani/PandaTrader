import pandas as pd
import requests
from datetime import datetime

def get_upcoming_unlocks():
    """
    Returns a DataFrame of upcoming token unlocks.
    Currently uses a hardcoded list for demonstration/backtesting purposes as per the playbook,
    but structures it to easily swap with an API call (e.g., DeFiLlama) in the future.
    """
    
    # We will use a list of dictionaries for better safety and accuracy.
    # These are illustrative major unlock events for backtesting.
    events = [
        # ARB
        {'token': 'ARB', 'symbol': 'ARB/USDT', 'unlock_date': '2024-03-16', 'pct_supply': 87.2, 'recipient_type': 'team'}, # The big "Cliff" unlock
        {'token': 'ARB', 'symbol': 'ARB/USDT', 'unlock_date': '2023-03-23', 'pct_supply': 11.6, 'recipient_type': 'airdrop'},
        
        # OP
        {'token': 'OP', 'symbol': 'OP/USDT', 'unlock_date': '2023-05-31', 'pct_supply': 3.6, 'recipient_type': 'investor'},
        {'token': 'OP', 'symbol': 'OP/USDT', 'unlock_date': '2024-03-29', 'pct_supply': 2.4, 'recipient_type': 'investor'},
        
        # APT
        {'token': 'APT', 'symbol': 'APT/USDT', 'unlock_date': '2023-11-12', 'pct_supply': 2.0, 'recipient_type': 'investor'},
        {'token': 'APT', 'symbol': 'APT/USDT', 'unlock_date': '2024-04-12', 'pct_supply': 5.8, 'recipient_type': 'investor'},
        
        # SUI
        {'token': 'SUI', 'symbol': 'SUI/USDT', 'unlock_date': '2024-05-03', 'pct_supply': 4.1, 'recipient_type': 'team'},
        
        # TIA
        {'token': 'TIA', 'symbol': 'TIA/USDT', 'unlock_date': '2024-02-28', 'pct_supply': 16.3, 'recipient_type': 'investor'}, # TIA unlock in Feb 2024
        {'token': 'TIA', 'symbol': 'TIA/USDT', 'unlock_date': '2024-10-31', 'pct_supply': 16.3, 'recipient_type': 'investor'},
    ]
    
    unlocks = pd.DataFrame(events)
    unlocks['unlock_date'] = pd.to_datetime(unlocks['unlock_date'])
    return unlocks

def score_unlock_impact(row):
    """Score expected impact based on tokenomics research"""
    score = 0
    
    # Size impact (larger = more negative)
    if row['pct_supply'] > 5:
        score -= 3
    elif row['pct_supply'] > 2:
        score -= 2
    else:
        score -= 1
    
    # Recipient type impact
    type_impact = {
        'team': -3,       # Worst: sell as compensation
        'investor': -2,   # Bad: VC selling via OTC
        'ecosystem': +1,  # Slightly positive: growth spend
        'community': 0,   # Neutral
        'airdrop': -2     # Usually immediate dump
    }
    score += type_impact.get(row['recipient_type'], -1)
    
    return score
