"""Tests for Config."""
import pytest
import os
from unittest.mock import patch
from config import Config


def test_parse_reminder_times_valid():
    """Test parsing valid reminder time strings."""
    with patch.dict(os.environ, {'REMINDER_TIMES': '10m,12h,24h,1d'}):
        import importlib
        import config
        importlib.reload(config)
        times = config.Config.parse_reminder_times()
        
        assert len(times) == 4
        assert times[0].days == 1  # 1d should be first (sorted descending)
        assert times[1].total_seconds() == 24 * 3600  # 24h
        assert times[2].total_seconds() == 12 * 3600  # 12h
        assert times[3].total_seconds() == 10 * 60  # 10m


def test_parse_reminder_times_empty():
    """Test parsing empty reminder times."""
    with patch.dict(os.environ, {'REMINDER_TIMES': ''}):
        import importlib
        import config
        importlib.reload(config)
        times = config.Config.parse_reminder_times()
        assert times == []


def test_parse_reminder_times_not_set():
    """Test parsing when REMINDER_TIMES is not set."""
    if 'REMINDER_TIMES' in os.environ:
        del os.environ['REMINDER_TIMES']
    with patch.object(Config, 'REMINDER_TIMES', ''):
        times = Config.parse_reminder_times()
        assert times == []


def test_parse_reminder_times_invalid_format():
    """Test parsing invalid reminder time formats."""
    with patch.dict(os.environ, {'REMINDER_TIMES': '10m,invalid,12h,xyz'}):
        import importlib
        import config
        importlib.reload(config)
        times = config.Config.parse_reminder_times()
        
        # Should parse valid ones and skip invalid
        assert len(times) == 2
        assert times[0].total_seconds() == 12 * 3600  # 12h
        assert times[1].total_seconds() == 10 * 60  # 10m


def test_parse_reminder_times_with_spaces():
    """Test parsing reminder times with spaces."""
    with patch.dict(os.environ, {'REMINDER_TIMES': '10m, 12h , 24h'}):
        import importlib
        import config
        importlib.reload(config)
        times = config.Config.parse_reminder_times()
        
        assert len(times) == 3

