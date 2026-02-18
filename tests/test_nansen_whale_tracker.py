"""Unit tests for utils/nansen_whale_tracker.py (Strategy 8)"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch

from utils.nansen_whale_tracker import (
    NansenWhaleTracker, TOKEN_MAP, SYMBOL_TO_PAIR,
)


def test_token_map_has_btc_eth_sol():
    assert 'BTC' in TOKEN_MAP
    assert 'ETH' in TOKEN_MAP
    assert 'SOL' in TOKEN_MAP
    assert TOKEN_MAP['BTC'][0] == 'ethereum'
    assert TOKEN_MAP['BTC'][1].startswith('0x')


def test_symbol_to_pair():
    assert SYMBOL_TO_PAIR.get('BTC') == 'BTC/USDT'
    assert SYMBOL_TO_PAIR.get('ETH') == 'ETH/USDT'


def test_compute_accumulation_score_positive_flow():
    tracker = NansenWhaleTracker(api_key='')
    score = tracker.compute_accumulation_score(500_000, 1_000_000, min_flow_24h=100_000)
    assert score > 0


def test_compute_accumulation_score_zero_flow():
    tracker = NansenWhaleTracker(api_key='')
    score = tracker.compute_accumulation_score(0, 0, min_flow_24h=100_000)
    assert score == 0


def test_compute_accumulation_score_negative_flow():
    tracker = NansenWhaleTracker(api_key='')
    score = tracker.compute_accumulation_score(-100_000, -500_000, min_flow_24h=100_000)
    assert score == 0


def test_get_accumulation_scores_empty_without_api_key():
    tracker = NansenWhaleTracker(api_key='')
    scores = tracker.get_accumulation_scores(['BTC', 'ETH'])
    assert scores == {}


@patch('utils.nansen_whale_tracker.requests.post')
def test_get_smart_money_netflow_returns_none_on_failure(mock_post):
    import requests
    mock_post.side_effect = requests.RequestException("API Error")
    tracker = NansenWhaleTracker(api_key='test-key')
    result = tracker.get_smart_money_netflow(chains=['ethereum'])
    assert result is None


@patch('utils.nansen_whale_tracker.requests.post')
def test_get_smart_money_netflow_returns_df_on_success(mock_post):
    mock_post.return_value.json.return_value = {
        'data': [
            {
                'token_address': '0x2260fac5e5542a773aa44fbcfedf7c193bc2c599',
                'token_symbol': 'WBTC',
                'net_flow_24h_usd': 100000,
                'net_flow_7d_usd': 500000,
                'chain': 'ethereum',
            }
        ]
    }
    mock_post.return_value.raise_for_status = Mock()
    tracker = NansenWhaleTracker(api_key='test-key')
    result = tracker.get_smart_money_netflow(chains=['ethereum'])
    assert result is not None
    assert not result.empty
    assert 'token_symbol' in result.columns or 'symbol' in result.columns
