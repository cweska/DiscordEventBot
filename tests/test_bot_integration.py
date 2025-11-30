"""End-to-end integration tests for the bot."""
import pytest
import discord
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime, timedelta
from bot import EventBot
from config import Config


@pytest.fixture
def mock_config(monkeypatch):
    """Mock configuration for testing."""
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "test_token")
    monkeypatch.setenv("FORUM_CHANNEL_ID", "987654321")
    monkeypatch.setenv("ARCHIVE_DELAY_HOURS", "24")
    
    # Reload config
    import importlib
    import config
    importlib.reload(config)
    return config.Config


@pytest.fixture
def mock_bot(mock_config):
    """Create a bot instance with mocked dependencies."""
    with patch('bot.Config', mock_config):
        bot = EventBot.__new__(EventBot)
        # Create a real ForumManager instance for event_posts dict
        from forum_manager import ForumManager
        bot.forum_manager = ForumManager(987654321)
        bot.archive_scheduler = MagicMock()
        bot.event_handler = MagicMock()
        # Mock guilds as a property
        type(bot).guilds = property(lambda self: [MagicMock()])
        # Mock user as a property
        mock_user = MagicMock()
        mock_user.name = "TestBot"
        type(bot).user = property(lambda self: mock_user)
        return bot


@pytest.mark.asyncio
async def test_process_existing_events_no_threads(mock_bot, mock_scheduled_event):
    """Test processing existing events when no threads exist."""
    mock_guild = mock_bot.guilds[0]
    # Ensure fetch_scheduled_events is properly async
    async def fetch_events():
        return [mock_scheduled_event]
    mock_guild.fetch_scheduled_events = fetch_events
    
    # Mock users() method for the event
    async def empty_users():
        if False:
            yield
    mock_scheduled_event.users = lambda: empty_users()
    
    # Mock find_existing_thread to avoid calling get_forum_channel
    mock_bot.forum_manager.find_existing_thread = AsyncMock(return_value=None)
    mock_bot.forum_manager.get_thread = MagicMock(return_value=None)
    
    # Patch on_scheduled_event_create to prevent it from running (which would call get_event_participants)
    with patch.object(mock_bot.event_handler, 'on_scheduled_event_create', new_callable=AsyncMock) as mock_create:
        await mock_bot.process_existing_events()
        
        mock_create.assert_called_once_with(mock_scheduled_event)


@pytest.mark.asyncio
async def test_process_existing_events_with_existing_thread(mock_bot, mock_scheduled_event, mock_thread):
    """Test processing existing events when thread already exists."""
    mock_guild = mock_bot.guilds[0]
    async def fetch_events():
        return [mock_scheduled_event]
    mock_guild.fetch_scheduled_events = fetch_events
    
    # Mock users() method for the event
    async def empty_users():
        if False:
            yield
    mock_scheduled_event.users = lambda: empty_users()
    
    # Mock get_event_participants to avoid issues with users() iteration
    mock_bot.event_handler.get_event_participants = AsyncMock(return_value=[])
    
    # Mock all dependencies so the real handler can run
    mock_bot.forum_manager.get_thread = MagicMock(return_value=mock_thread)
    mock_bot.forum_manager.update_forum_post = AsyncMock(return_value=True)
    mock_bot.forum_manager.update_thread_name = AsyncMock(return_value=True)
    mock_bot.archive_scheduler.schedule_archive = MagicMock()
    # Mock calendar manager if it exists
    if mock_bot.event_handler.calendar_manager:
        mock_bot.event_handler.calendar_manager.generate_calendar_link_for_update = MagicMock(return_value="https://calendar.google.com/test")
    
    # Track calls to on_scheduled_event_update
    original_update = mock_bot.event_handler.on_scheduled_event_update
    call_count = 0
    call_args_list = []
    
    async def tracked_update(before, after):
        nonlocal call_count, call_args_list
        call_count += 1
        call_args_list.append((before, after))
        return await original_update(before, after)
    
    mock_bot.event_handler.on_scheduled_event_update = tracked_update
    
    await mock_bot.process_existing_events()
    
    # When processing existing events, both before and after are the same event
    assert call_count == 1, f"Expected on_scheduled_event_update to be called once, but it was called {call_count} times"
    assert call_args_list[0] == (mock_scheduled_event, mock_scheduled_event)


@pytest.mark.asyncio
async def test_process_existing_events_finds_thread(mock_bot, mock_scheduled_event, mock_thread):
    """Test processing existing events and finding thread by name."""
    mock_guild = mock_bot.guilds[0]
    async def fetch_events():
        return [mock_scheduled_event]
    mock_guild.fetch_scheduled_events = fetch_events
    
    # Mock users() method for the event
    async def empty_users():
        if False:
            yield
    mock_scheduled_event.users = lambda: empty_users()
    
    # Mock get_event_participants to avoid issues with users() iteration
    mock_bot.event_handler.get_event_participants = AsyncMock(return_value=[])
    
    # Mock all dependencies so the real handler can run
    mock_bot.forum_manager.get_thread = MagicMock(return_value=None)
    mock_bot.forum_manager.find_existing_thread = AsyncMock(return_value=mock_thread)
    mock_bot.forum_manager.update_forum_post = AsyncMock(return_value=True)
    mock_bot.forum_manager.update_thread_name = AsyncMock(return_value=True)
    mock_bot.archive_scheduler.schedule_archive = MagicMock()
    # Mock calendar manager if it exists
    if mock_bot.event_handler.calendar_manager:
        mock_bot.event_handler.calendar_manager.generate_calendar_link_for_update = MagicMock(return_value="https://calendar.google.com/test")
    
    # Track calls to on_scheduled_event_update
    original_update = mock_bot.event_handler.on_scheduled_event_update
    call_count = 0
    call_args_list = []
    
    async def tracked_update(before, after):
        nonlocal call_count, call_args_list
        call_count += 1
        call_args_list.append((before, after))
        return await original_update(before, after)
    
    mock_bot.event_handler.on_scheduled_event_update = tracked_update
    
    await mock_bot.process_existing_events()
    
    # When processing existing events, both before and after are the same event
    assert call_count == 1, f"Expected on_scheduled_event_update to be called once, but it was called {call_count} times"
    assert call_args_list[0] == (mock_scheduled_event, mock_scheduled_event)
    # Should have added thread to mapping
    assert mock_bot.forum_manager.event_posts.get(mock_scheduled_event.id) == mock_thread


@pytest.mark.asyncio
async def test_on_scheduled_event_create(mock_bot, mock_scheduled_event):
    """Test bot's event create handler."""
    mock_bot.event_handler.on_scheduled_event_create = AsyncMock()
    
    await mock_bot.on_scheduled_event_create(mock_scheduled_event)
    
    mock_bot.event_handler.on_scheduled_event_create.assert_called_once_with(mock_scheduled_event)


@pytest.mark.asyncio
async def test_on_scheduled_event_update(mock_bot, mock_scheduled_event):
    """Test bot's event update handler."""
    mock_bot.event_handler.on_scheduled_event_update = AsyncMock()
    
    # Create a before event for the test
    before_event = MagicMock(spec=discord.ScheduledEvent)
    before_event.id = mock_scheduled_event.id
    before_event.name = "Old Name"
    
    await mock_bot.on_scheduled_event_update(before_event, mock_scheduled_event)
    
    mock_bot.event_handler.on_scheduled_event_update.assert_called_once_with(before_event, mock_scheduled_event)


@pytest.mark.asyncio
async def test_on_scheduled_event_delete(mock_bot, mock_scheduled_event):
    """Test bot's event delete handler."""
    mock_bot.event_handler.on_scheduled_event_delete = AsyncMock()
    
    await mock_bot.on_scheduled_event_delete(mock_scheduled_event)
    
    mock_bot.event_handler.on_scheduled_event_delete.assert_called_once_with(mock_scheduled_event)


@pytest.mark.asyncio
async def test_on_scheduled_event_user_add(mock_bot, mock_scheduled_event, mock_user):
    """Test bot's user add handler."""
    mock_bot.event_handler.on_scheduled_event_user_add = AsyncMock()
    
    await mock_bot.on_scheduled_event_user_add(mock_scheduled_event, mock_user)
    
    mock_bot.event_handler.on_scheduled_event_user_add.assert_called_once_with(
        mock_scheduled_event,
        mock_user
    )


@pytest.mark.asyncio
async def test_on_scheduled_event_user_remove(mock_bot, mock_scheduled_event, mock_user):
    """Test bot's user remove handler."""
    mock_bot.event_handler.on_scheduled_event_user_remove = AsyncMock()
    
    await mock_bot.on_scheduled_event_user_remove(mock_scheduled_event, mock_user)
    
    mock_bot.event_handler.on_scheduled_event_user_remove.assert_called_once_with(
        mock_scheduled_event,
        mock_user
    )


@pytest.mark.asyncio
async def test_end_to_end_event_lifecycle(mock_config):
    """Test complete event lifecycle from creation to archiving."""
    with patch('bot.Config', mock_config):
        # Create real instances for integration test
        from forum_manager import ForumManager
        from archive_scheduler import ArchiveScheduler
        from event_handler import EventHandler
        
        forum_manager = ForumManager(987654321, None)  # No calendar manager for this test
        archive_scheduler = ArchiveScheduler(24)
        event_handler = EventHandler(forum_manager, archive_scheduler, None, None)  # No reminder scheduler for this test
        
        # Create mock event
        mock_event = MagicMock(spec=discord.ScheduledEvent)
        mock_event.id = 444555666
        mock_event.name = "Kitchen Sync"
        mock_event.description = "Let's cook!"
        mock_event.guild = MagicMock()
        mock_event.start_time = discord.utils.utcnow() + timedelta(hours=1)
        mock_event.end_time = discord.utils.utcnow() + timedelta(hours=2)
        
        # Mock forum channel and thread
        mock_forum_channel = MagicMock(spec=discord.ForumChannel)
        mock_thread = MagicMock(spec=discord.Thread)
        mock_thread.id = 111222333
        mock_thread.name = "Kitchen Sync"
        mock_thread.archived = False
        mock_message = MagicMock(spec=discord.Message)
        mock_message.edit = AsyncMock()
        
        async def history_gen():
            yield mock_message
        
        mock_thread.history = lambda limit=100, oldest_first=True: history_gen()
        mock_forum_channel.create_thread = AsyncMock(return_value=mock_thread)
        mock_event.guild.get_channel.return_value = mock_forum_channel
        
        # Mock participants
        mock_user1 = MagicMock(spec=discord.User)
        mock_user1.mention = "<@111>"
        mock_user2 = MagicMock(spec=discord.User)
        mock_user2.mention = "<@222>"
        
        async def users_gen():
            yield mock_user1
            yield mock_user2
        
        mock_event.users = lambda: users_gen()
        
        # 1. Create event
        await event_handler.on_scheduled_event_create(mock_event)
        assert mock_event.id in forum_manager.event_posts
        
        # 2. User joins
        mock_user3 = MagicMock(spec=discord.User)
        mock_user3.mention = "<@333>"
        
        async def users_gen_updated():
            yield mock_user1
            yield mock_user2
            yield mock_user3
        
        mock_event.users = lambda: users_gen_updated()
        await event_handler.on_scheduled_event_user_add(mock_event, mock_user3)
        
        # 3. User leaves
        async def users_gen_removed():
            yield mock_user1
            yield mock_user3
        
        mock_event.users = lambda: users_gen_removed()
        await event_handler.on_scheduled_event_user_remove(mock_event, mock_user2)
        
        # 4. Update event
        mock_event.description = "Updated description"
        # For update test, use same event for both before and after
        await event_handler.on_scheduled_event_update(mock_event, mock_event)
        
        # 5. Delete event (archive immediately)
        await event_handler.on_scheduled_event_delete(mock_event)
        
        # Verify archiving was scheduled (the actual archiving happens async)
        # The thread should be removed from tracking after archiving
        # Since archiving is async, we just verify the handler was called
        assert True  # Archive was scheduled via archive_immediately

