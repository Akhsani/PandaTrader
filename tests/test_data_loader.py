"""Unit tests for utils/data_loader.py"""
import sys
import os
import tempfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import pytest
from utils.data_loader import load_ohlcv, find_funding_path


def test_load_ohlcv_datetime_column():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("datetime,open,high,low,close,volume\n")
        f.write("2024-01-01 00:00:00,100,101,99,100.5,1000\n")
        f.write("2024-01-02 00:00:00,100.5,102,100,101,1100\n")
        f.close()
        df = load_ohlcv(f.name)
        assert isinstance(df.index, pd.DatetimeIndex)
        assert len(df) == 2
        os.unlink(f.name)


def test_load_ohlcv_date_column():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("date,open,high,low,close,volume\n")
        f.write("2024-01-01,100,101,99,100.5,1000\n")
        f.close()
        df = load_ohlcv(f.name)
        assert isinstance(df.index, pd.DatetimeIndex)
        os.unlink(f.name)


def test_load_ohlcv_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_ohlcv("nonexistent/path.csv")


def test_find_funding_path_returns_none_when_missing():
    assert find_funding_path("FAKE/USDT") is None
