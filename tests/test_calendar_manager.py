"""Tests for CalendarManager."""
import pytest
import discord
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime, timedelta
from calendar_manager import CalendarManager


@pytest.fixture
def mock_google_service():
    """Create a mock Google Calendar service."""
    service = MagicMock()
    events = MagicMock()
    service.events.return_value = events
    return service, events


@pytest.fixture
def mock_credentials_file(tmp_path):
    """Create a temporary mock credentials file."""
    creds_file = tmp_path / "test-credentials.json"
    creds_file.write_text('{"type": "service_account", "project_id": "test"}')
    return str(creds_file)


def test_calendar_manager_init_without_credentials():
    """Test CalendarManager initialization without credentials."""
    manager = CalendarManager()
    
    assert manager.service is None
    assert manager.calendar_id == 'primary'
    assert manager.event_mappings == {}


def test_calendar_manager_init_with_nonexistent_credentials():
    """Test CalendarManager initialization with non-existent credentials file."""
    manager = CalendarManager(credentials_path="nonexistent.json")
    
    assert manager.service is None


@patch('calendar_manager.service_account.Credentials.from_service_account_file')
@patch('calendar_manager.build')
def test_calendar_manager_init_with_credentials(mock_build, mock_creds, mock_credentials_file):
    """Test CalendarManager initialization with valid credentials."""
    mock_creds.return_value = MagicMock()
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    
    manager = CalendarManager(credentials_path=mock_credentials_file)
    
    assert manager.service == mock_service
    mock_creds.assert_called_once()
    mock_build.assert_called_once()


@patch('calendar_manager.service_account.Credentials.from_service_account_file')
@patch('calendar_manager.build')
def test_calendar_manager_init_with_custom_calendar_id(mock_build, mock_creds, mock_credentials_file):
    """Test CalendarManager initialization with custom calendar ID."""
    mock_creds.return_value = MagicMock()
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    
    manager = CalendarManager(
        credentials_path=mock_credentials_file,
        calendar_id="custom@group.calendar.google.com"
    )
    
    assert manager.calendar_id == "custom@group.calendar.google.com"


@pytest.mark.asyncio
async def test_create_calendar_event_success(mock_scheduled_event, mock_google_service):
    """Test successfully creating a calendar event."""
    service, events = mock_google_service
    manager = CalendarManager()
    manager.service = service
    manager.calendar_id = 'primary'
    
    # Mock the insert operation
    created_event = {
        'id': 'google_event_123',
        'summary': 'Test Event',
        'htmlLink': 'https://calendar.google.com/event?eid=123'
    }
    events.insert.return_value.execute.return_value = created_event
    
    result = await manager.create_calendar_event(mock_scheduled_event)
    
    assert result is not None
    assert 'calendar.google.com' in result
    assert manager.event_mappings[mock_scheduled_event.id] == 'google_event_123'
    events.insert.assert_called_once()


@pytest.mark.asyncio
async def test_create_calendar_event_no_service(mock_scheduled_event):
    """Test creating calendar event when service is not initialized."""
    manager = CalendarManager()
    manager.service = None
    
    result = await manager.create_calendar_event(mock_scheduled_event)
    
    assert result is None


@pytest.mark.asyncio
async def test_create_calendar_event_api_error(mock_scheduled_event, mock_google_service):
    """Test handling API error when creating calendar event."""
    from googleapiclient.errors import HttpError
    from unittest.mock import Mock as MockObj
    
    service, events = mock_google_service
    manager = CalendarManager()
    manager.service = service
    
    # Mock HTTP error
    error_response = MockObj()
    error_response.status = 400
    error = HttpError(MockObj(), b'{"error": "Bad Request"}')
    error.resp = error_response
    
    events.insert.return_value.execute.side_effect = error
    
    result = await manager.create_calendar_event(mock_scheduled_event)
    
    assert result is None


@pytest.mark.asyncio
async def test_update_calendar_event_success(mock_scheduled_event, mock_google_service):
    """Test successfully updating a calendar event."""
    service, events = mock_google_service
    manager = CalendarManager()
    manager.service = service
    manager.event_mappings[mock_scheduled_event.id] = 'existing_event_123'
    
    # Mock get and update operations
    existing_event = {
        'id': 'existing_event_123',
        'summary': 'Old Event',
        'description': 'Old description',
        'start': {'dateTime': '2024-01-01T10:00:00Z', 'timeZone': 'UTC'},
        'end': {'dateTime': '2024-01-01T11:00:00Z', 'timeZone': 'UTC'}
    }
    events.get.return_value.execute.return_value = existing_event
    events.update.return_value.execute.return_value = existing_event
    
    result = await manager.update_calendar_event(mock_scheduled_event)
    
    assert result is not None
    assert 'calendar.google.com' in result
    events.get.assert_called_once()
    events.update.assert_called_once()


@pytest.mark.asyncio
async def test_update_calendar_event_not_found_creates_new(mock_scheduled_event, mock_google_service):
    """Test updating calendar event that doesn't exist creates a new one."""
    service, events = mock_google_service
    manager = CalendarManager()
    manager.service = service
    manager.event_mappings[mock_scheduled_event.id] = 'missing_event_123'
    
    # Mock 404 error on get
    from googleapiclient.errors import HttpError
    from unittest.mock import Mock as MockObj
    
    error_response = MockObj()
    error_response.status = 404
    error = HttpError(MockObj(), b'{"error": "Not Found"}')
    error.resp = error_response
    
    events.get.return_value.execute.side_effect = error
    
    # Mock successful creation
    created_event = {'id': 'new_event_456'}
    events.insert.return_value.execute.return_value = created_event
    
    result = await manager.update_calendar_event(mock_scheduled_event)
    
    assert result is not None
    # Should have created new event
    assert manager.event_mappings[mock_scheduled_event.id] == 'new_event_456'


@pytest.mark.asyncio
async def test_update_calendar_event_no_mapping_creates_new(mock_scheduled_event, mock_google_service):
    """Test updating calendar event with no existing mapping creates new event."""
    service, events = mock_google_service
    manager = CalendarManager()
    manager.service = service
    
    # Mock successful creation
    created_event = {'id': 'new_event_789'}
    events.insert.return_value.execute.return_value = created_event
    
    result = await manager.update_calendar_event(mock_scheduled_event)
    
    assert result is not None
    assert manager.event_mappings[mock_scheduled_event.id] == 'new_event_789'


@pytest.mark.asyncio
async def test_delete_calendar_event_success(mock_google_service):
    """Test successfully deleting a calendar event."""
    service, events = mock_google_service
    manager = CalendarManager()
    manager.service = service
    event_id = 123456
    manager.event_mappings[event_id] = 'google_event_123'
    
    events.delete.return_value.execute.return_value = None
    
    result = await manager.delete_calendar_event(event_id)
    
    assert result is True
    assert event_id not in manager.event_mappings
    events.delete.assert_called_once()


@pytest.mark.asyncio
async def test_delete_calendar_event_not_found(mock_google_service):
    """Test deleting calendar event that doesn't exist in mapping."""
    service, events = mock_google_service
    manager = CalendarManager()
    manager.service = service
    
    result = await manager.delete_calendar_event(999999)
    
    assert result is False


@pytest.mark.asyncio
async def test_delete_calendar_event_already_deleted(mock_google_service):
    """Test deleting calendar event that was already deleted."""
    from googleapiclient.errors import HttpError
    from unittest.mock import Mock as MockObj
    
    service, events = mock_google_service
    manager = CalendarManager()
    manager.service = service
    event_id = 123456
    manager.event_mappings[event_id] = 'google_event_123'
    
    # Mock 404 error (already deleted)
    error_response = MockObj()
    error_response.status = 404
    error = HttpError(MockObj(), b'{"error": "Not Found"}')
    error.resp = error_response
    
    events.delete.return_value.execute.side_effect = error
    
    result = await manager.delete_calendar_event(event_id)
    
    assert result is True
    assert event_id not in manager.event_mappings


@pytest.mark.asyncio
async def test_delete_calendar_event_no_service():
    """Test deleting calendar event when service is not initialized."""
    manager = CalendarManager()
    manager.service = None
    
    result = await manager.delete_calendar_event(123456)
    
    assert result is False


def test_format_datetime_for_google():
    """Test datetime formatting for Google Calendar API."""
    manager = CalendarManager()
    
    # Test with timezone-aware datetime
    dt = discord.utils.utcnow()
    formatted = manager._format_datetime_for_google(dt)
    
    assert 'T' in formatted
    assert '+' in formatted or 'Z' in formatted or formatted.endswith('+00:00')


def test_get_calendar_link():
    """Test getting calendar link (returns None for now)."""
    manager = CalendarManager()
    
    result = manager.get_calendar_link(123456)
    
    assert result is None

