"""Tests for CalendarManager."""
import pytest
import discord
from unittest.mock import MagicMock
from datetime import datetime, timedelta, timezone
from calendar_manager import CalendarManager


def test_calendar_manager_init():
    """Test CalendarManager initialization."""
    manager = CalendarManager()
    
    # Should initialize without any issues
    assert manager is not None


def test_generate_calendar_link_success(mock_scheduled_event):
    """Test successfully generating a calendar link."""
    manager = CalendarManager()
    
    result = manager.generate_calendar_link(mock_scheduled_event)
    
    assert result is not None
    assert result != ""
    assert "calendar.google.com" in result
    assert "action=TEMPLATE" in result
    assert "text=" in result
    assert "dates=" in result


def test_generate_calendar_link_includes_event_name(mock_scheduled_event):
    """Test that calendar link includes event name."""
    manager = CalendarManager()
    mock_scheduled_event.name = "Kitchen Sync Event"
    
    result = manager.generate_calendar_link(mock_scheduled_event)
    
    assert "Kitchen%20Sync%20Event" in result or "Kitchen+Sync+Event" in result


def test_generate_calendar_link_includes_description(mock_scheduled_event):
    """Test that calendar link includes event description."""
    manager = CalendarManager()
    mock_scheduled_event.description = "Let's cook together!"
    
    result = manager.generate_calendar_link(mock_scheduled_event)
    
    assert "Let" in result  # URL encoded description


def test_generate_calendar_link_no_end_time(mock_scheduled_event):
    """Test generating calendar link when event has no end time."""
    manager = CalendarManager()
    mock_scheduled_event.end_time = None
    
    result = manager.generate_calendar_link(mock_scheduled_event)
    
    assert result is not None
    assert "calendar.google.com" in result


def test_generate_calendar_link_timezone_handling(mock_scheduled_event):
    """Test that timezone-aware datetimes are handled correctly."""
    manager = CalendarManager()
    
    # Set timezone-aware times
    mock_scheduled_event.start_time = datetime.now(timezone.utc)
    mock_scheduled_event.end_time = datetime.now(timezone.utc) + timedelta(hours=1)
    
    result = manager.generate_calendar_link(mock_scheduled_event)
    
    assert result is not None
    assert "calendar.google.com" in result


def test_generate_calendar_link_timezone_naive(mock_scheduled_event):
    """Test that timezone-naive datetimes are converted to UTC."""
    manager = CalendarManager()
    
    # Set timezone-naive times
    mock_scheduled_event.start_time = datetime.now()
    mock_scheduled_event.end_time = datetime.now() + timedelta(hours=1)
    
    result = manager.generate_calendar_link(mock_scheduled_event)
    
    assert result is not None
    assert "calendar.google.com" in result


def test_generate_calendar_link_for_update(mock_scheduled_event):
    """Test generating updated calendar link."""
    manager = CalendarManager()
    
    result = manager.generate_calendar_link_for_update(mock_scheduled_event)
    
    assert result is not None
    assert "calendar.google.com" in result
    # Should be the same as generate_calendar_link
    assert result == manager.generate_calendar_link(mock_scheduled_event)


def test_generate_calendar_link_error_handling():
    """Test error handling when generating calendar link."""
    manager = CalendarManager()
    
    # Create a mock event that will cause an error
    bad_event = MagicMock()
    bad_event.name = "Test"
    bad_event.description = None
    bad_event.start_time = None  # This will cause an error
    
    result = manager.generate_calendar_link(bad_event)
    
    # Should return empty string on error
    assert result == ""


def test_generate_calendar_link_special_characters(mock_scheduled_event):
    """Test that special characters in event name are URL encoded."""
    manager = CalendarManager()
    mock_scheduled_event.name = "Event with & special chars!"
    
    result = manager.generate_calendar_link(mock_scheduled_event)
    
    assert "calendar.google.com" in result
    # Special characters should be URL encoded
    assert "%26" in result or "&" not in result  # & should be encoded


def test_generate_calendar_link_long_description(mock_scheduled_event):
    """Test handling of long event descriptions."""
    manager = CalendarManager()
    mock_scheduled_event.description = "A" * 1000  # Very long description
    
    result = manager.generate_calendar_link(mock_scheduled_event)
    
    assert result is not None
    assert "calendar.google.com" in result
