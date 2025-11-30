"""Tests for ReminderScheduler."""
import pytest
import asyncio
import discord
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone
from reminder_scheduler import ReminderScheduler


@pytest.fixture
def mock_guild():
    """Create a mock Discord guild."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = 123456789
    return guild


@pytest.fixture
def mock_scheduled_event(mock_guild):
    """Create a mock Discord scheduled event."""
    event = MagicMock(spec=discord.ScheduledEvent)
    event.id = 444555666
    event.name = "Kitchen Sync Event"
    event.description = "Let's cook together!"
    event.guild = mock_guild
    event.start_time = datetime.now(timezone.utc) + timedelta(hours=25)  # 25 hours from now
    event.end_time = datetime.now(timezone.utc) + timedelta(hours=26)
    return event


@pytest.fixture
def mock_channel():
    """Create a mock Discord channel."""
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 987654321
    channel.send = AsyncMock()
    return channel


@pytest.mark.asyncio
async def test_schedule_reminders_future_event(mock_scheduled_event, mock_channel):
    """Test scheduling reminders for a future event."""
    reminder_times = [timedelta(hours=24), timedelta(hours=12), timedelta(minutes=10)]
    scheduler = ReminderScheduler(987654321, reminder_times)
    mock_scheduled_event.guild.get_channel.return_value = mock_channel
    
    async def get_participants(event):
        return []
    
    scheduler.schedule_reminders(mock_scheduled_event, get_participants)
    
    # Should have scheduled reminders
    assert mock_scheduled_event.id in scheduler.scheduled_tasks
    assert len(scheduler.scheduled_tasks[mock_scheduled_event.id]) == 3


@pytest.mark.asyncio
async def test_schedule_reminders_past_event(mock_scheduled_event, mock_channel):
    """Test scheduling reminders for an event that already started."""
    reminder_times = [timedelta(hours=24), timedelta(hours=12)]
    scheduler = ReminderScheduler(987654321, reminder_times)
    
    # Set event start time to the past
    mock_scheduled_event.start_time = datetime.now(timezone.utc) - timedelta(hours=1)
    
    async def get_participants(event):
        return []
    
    scheduler.schedule_reminders(mock_scheduled_event, get_participants)
    
    # Should not have scheduled any reminders
    assert mock_scheduled_event.id not in scheduler.scheduled_tasks


@pytest.mark.asyncio
async def test_schedule_reminders_no_start_time(mock_scheduled_event):
    """Test scheduling reminders for event with no start time."""
    reminder_times = [timedelta(hours=24)]
    scheduler = ReminderScheduler(987654321, reminder_times)
    
    mock_scheduled_event.start_time = None
    
    async def get_participants(event):
        return []
    
    scheduler.schedule_reminders(mock_scheduled_event, get_participants)
    
    # Should not have scheduled any reminders
    assert mock_scheduled_event.id not in scheduler.scheduled_tasks


@pytest.mark.asyncio
async def test_schedule_reminders_cancels_existing(mock_scheduled_event, mock_channel):
    """Test that scheduling reminders cancels existing ones."""
    reminder_times = [timedelta(hours=24)]
    scheduler = ReminderScheduler(987654321, reminder_times)
    mock_scheduled_event.guild.get_channel.return_value = mock_channel
    
    async def get_participants(event):
        return []
    
    # Schedule first set
    scheduler.schedule_reminders(mock_scheduled_event, get_participants)
    first_tasks = scheduler.scheduled_tasks[mock_scheduled_event.id]
    
    # Schedule again (should cancel first)
    scheduler.schedule_reminders(mock_scheduled_event, get_participants)
    second_tasks = scheduler.scheduled_tasks[mock_scheduled_event.id]
    
    assert first_tasks != second_tasks


@pytest.mark.asyncio
async def test_cancel_reminders(mock_scheduled_event, mock_channel):
    """Test canceling reminders."""
    reminder_times = [timedelta(hours=24)]
    scheduler = ReminderScheduler(987654321, reminder_times)
    mock_scheduled_event.guild.get_channel.return_value = mock_channel
    
    async def get_participants(event):
        return []
    
    scheduler.schedule_reminders(mock_scheduled_event, get_participants)
    assert mock_scheduled_event.id in scheduler.scheduled_tasks
    
    scheduler.cancel_reminders(mock_scheduled_event.id)
    assert mock_scheduled_event.id not in scheduler.scheduled_tasks


@pytest.mark.asyncio
async def test_send_reminder_success(mock_scheduled_event, mock_channel):
    """Test successfully sending a reminder."""
    reminder_times = [timedelta(hours=24)]
    scheduler = ReminderScheduler(987654321, reminder_times)
    mock_scheduled_event.guild.get_channel.return_value = mock_channel
    
    mock_user1 = MagicMock(spec=discord.User)
    mock_user1.mention = "<@111>"
    mock_user2 = MagicMock(spec=discord.User)
    mock_user2.mention = "<@222>"
    
    async def get_participants(event):
        return [mock_user1, mock_user2]
    
    await scheduler._send_reminder(mock_scheduled_event, timedelta(hours=24), get_participants)
    
    mock_channel.send.assert_called_once()
    message = mock_channel.send.call_args[0][0]
    assert "Reminder:" in message
    assert mock_scheduled_event.name in message
    assert "<@111>" in message
    assert "<@222>" in message
    assert "Sign up in the events tab!" in message


@pytest.mark.asyncio
async def test_send_reminder_no_participants(mock_scheduled_event, mock_channel):
    """Test sending reminder with no participants."""
    reminder_times = [timedelta(hours=24)]
    scheduler = ReminderScheduler(987654321, reminder_times)
    mock_scheduled_event.guild.get_channel.return_value = mock_channel
    
    async def get_participants(event):
        return []
    
    await scheduler._send_reminder(mock_scheduled_event, timedelta(hours=24), get_participants)
    
    mock_channel.send.assert_called_once()
    message = mock_channel.send.call_args[0][0]
    assert "No participants yet" in message


@pytest.mark.asyncio
async def test_send_reminder_channel_not_found(mock_scheduled_event):
    """Test sending reminder when channel doesn't exist."""
    reminder_times = [timedelta(hours=24)]
    scheduler = ReminderScheduler(987654321, reminder_times)
    mock_scheduled_event.guild.get_channel.return_value = None
    
    async def get_participants(event):
        return []
    
    await scheduler._send_reminder(mock_scheduled_event, timedelta(hours=24), get_participants)
    
    # Should not raise, just log error


@pytest.mark.asyncio
async def test_send_reminder_event_already_started(mock_scheduled_event, mock_channel):
    """Test skipping reminder if event already started."""
    reminder_times = [timedelta(hours=24)]
    scheduler = ReminderScheduler(987654321, reminder_times)
    mock_scheduled_event.guild.get_channel.return_value = mock_channel
    
    # Set start time to the past
    mock_scheduled_event.start_time = datetime.now(timezone.utc) - timedelta(hours=1)
    
    async def get_participants(event):
        return []
    
    await scheduler._send_reminder(mock_scheduled_event, timedelta(hours=24), get_participants)
    
    # Should not send reminder
    mock_channel.send.assert_not_called()


@pytest.mark.asyncio
async def test_format_time_until_event(mock_scheduled_event):
    """Test formatting time until event."""
    scheduler = ReminderScheduler(987654321, [])
    
    # Test minutes
    future_time = datetime.now(timezone.utc) + timedelta(minutes=15)
    result = scheduler._format_time_until_event(future_time)
    assert "minute" in result.lower()
    
    # Test hours
    future_time = datetime.now(timezone.utc) + timedelta(hours=2)
    result = scheduler._format_time_until_event(future_time)
    assert "hour" in result.lower()
    
    # Test days (use 2 days to ensure it's formatted as days)
    future_time = datetime.now(timezone.utc) + timedelta(days=2)
    result = scheduler._format_time_until_event(future_time)
    assert "day" in result.lower()


@pytest.mark.asyncio
async def test_format_participants(mock_scheduled_event):
    """Test formatting participant list."""
    scheduler = ReminderScheduler(987654321, [])
    
    # No participants
    result = scheduler._format_participants([])
    assert result == "No participants yet"
    
    # With participants
    mock_user1 = MagicMock(spec=discord.User)
    mock_user1.mention = "<@111>"
    mock_user2 = MagicMock(spec=discord.User)
    mock_user2.mention = "<@222>"
    
    result = scheduler._format_participants([mock_user1, mock_user2])
    assert "<@111>" in result
    assert "<@222>" in result
    
    # Many participants (test truncation)
    many_users = [MagicMock(spec=discord.User) for _ in range(25)]
    for i, user in enumerate(many_users):
        user.mention = f"<@{i}>"
    
    result = scheduler._format_participants(many_users)
    assert "and 5 more" in result

