"""Pytest configuration and shared fixtures."""
import pytest
import discord
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone


@pytest.fixture
def mock_guild():
    """Create a mock Discord guild."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = 123456789
    guild.name = "Test Guild"
    return guild


@pytest.fixture
def mock_forum_channel(mock_guild):
    """Create a mock Discord forum channel."""
    channel = MagicMock(spec=discord.ForumChannel)
    channel.id = 987654321
    channel.guild = mock_guild
    channel.name = "Test Forum"
    channel.threads = []
    channel.create_thread = AsyncMock()
    channel.archived_threads = AsyncMock()
    return channel


@pytest.fixture
def mock_thread(mock_forum_channel):
    """Create a mock Discord thread."""
    thread = MagicMock(spec=discord.Thread)
    thread.id = 111222333
    thread.name = "Test Event"
    thread.archived = False
    thread.locked = False
    thread.parent = mock_forum_channel
    thread.edit = AsyncMock()
    thread.fetch_message = AsyncMock()
    thread.history = AsyncMock()
    return thread


@pytest.fixture
def mock_scheduled_event(mock_guild):
    """Create a mock Discord scheduled event."""
    event = MagicMock(spec=discord.ScheduledEvent)
    event.id = 444555666
    event.name = "Kitchen Sync Event"
    event.description = "Let's cook together!"
    event.guild = mock_guild
    event.start_time = discord.utils.utcnow() + timedelta(hours=1)
    event.end_time = discord.utils.utcnow() + timedelta(hours=2)
    event.subscribers = AsyncMock()
    return event


@pytest.fixture
def mock_user():
    """Create a mock Discord user."""
    user = MagicMock(spec=discord.User)
    user.id = 777888999
    user.name = "TestUser"
    user.mention = "<@777888999>"
    return user


@pytest.fixture
def mock_message(mock_thread):
    """Create a mock Discord message."""
    message = MagicMock(spec=discord.Message)
    message.id = 999888777
    message.content = "Test message content"
    message.edit = AsyncMock()
    message.channel = mock_thread
    return message


@pytest.fixture
def mock_archive_category(mock_guild):
    """Create a mock archive category."""
    category = MagicMock(spec=discord.CategoryChannel)
    category.id = 555666777
    category.name = "Archive"
    category.guild = mock_guild
    return category


@pytest.fixture
def sample_participants(mock_user):
    """Create a list of mock participants."""
    user2 = MagicMock(spec=discord.User)
    user2.id = 111222333
    user2.name = "TestUser2"
    user2.mention = "<@111222333>"
    
    user3 = MagicMock(spec=discord.User)
    user3.id = 333444555
    user3.name = "TestUser3"
    user3.mention = "<@333444555>"
    
    return [mock_user, user2, user3]

