"""Tests for ForumManager."""
import pytest
import discord
from unittest.mock import AsyncMock, MagicMock, patch
from forum_manager import ForumManager


@pytest.mark.asyncio
async def test_get_forum_channel_success(mock_guild, mock_forum_channel):
    """Test successfully getting a forum channel."""
    manager = ForumManager(987654321)
    mock_guild.get_channel.return_value = mock_forum_channel
    
    result = await manager.get_forum_channel(mock_guild)
    
    assert result == mock_forum_channel
    mock_guild.get_channel.assert_called_once_with(987654321)


@pytest.mark.asyncio
async def test_get_forum_channel_not_found(mock_guild):
    """Test when forum channel is not found."""
    manager = ForumManager(987654321)
    mock_guild.get_channel.return_value = None
    
    result = await manager.get_forum_channel(mock_guild)
    
    assert result is None


@pytest.mark.asyncio
async def test_get_forum_channel_wrong_type(mock_guild):
    """Test when channel exists but is not a ForumChannel."""
    manager = ForumManager(987654321)
    wrong_channel = MagicMock()
    wrong_channel.id = 987654321
    mock_guild.get_channel.return_value = wrong_channel
    
    result = await manager.get_forum_channel(mock_guild)
    
    assert result is None


@pytest.mark.asyncio
async def test_format_event_content(mock_scheduled_event, sample_participants):
    """Test formatting event content."""
    manager = ForumManager(987654321)
    
    content = manager.format_event_content(mock_scheduled_event, sample_participants)
    
    assert "Kitchen Sync Event" not in content  # Name is used as title, not in content
    assert "Let's cook together!" in content
    assert "Participants:" in content
    assert "3" in content
    assert "TestUser" in content or "<@777888999>" in content
    assert "💬" in content


@pytest.mark.asyncio
async def test_format_event_content_with_calendar_link(mock_scheduled_event, sample_participants):
    """Test formatting event content with calendar link."""
    manager = ForumManager(987654321)
    calendar_link = "https://calendar.google.com/calendar/render?action=TEMPLATE&text=Test"
    
    content = manager.format_event_content(mock_scheduled_event, sample_participants, calendar_link)
    
    assert "📅" in content
    assert "Add to Calendar" in content
    assert calendar_link in content


@pytest.mark.asyncio
async def test_format_event_content_no_participants(mock_scheduled_event):
    """Test formatting event content with no participants."""
    manager = ForumManager(987654321)
    
    content = manager.format_event_content(mock_scheduled_event, [])
    
    assert "Participants:" in content
    assert "0" in content
    assert "No participants yet" in content


@pytest.mark.asyncio
async def test_format_event_content_many_participants(mock_scheduled_event):
    """Test formatting event content with many participants."""
    manager = ForumManager(987654321)
    
    # Create 25 participants
    participants = []
    for i in range(25):
        user = MagicMock(spec=discord.User)
        user.mention = f"<@{i}>"
        participants.append(user)
    
    content = manager.format_event_content(mock_scheduled_event, participants)
    
    assert "Participants:" in content
    assert "25" in content
    assert "and 5 more" in content  # Should show first 20 + "and X more"


@pytest.mark.asyncio
async def test_create_forum_post_success(mock_scheduled_event, mock_forum_channel, mock_thread, sample_participants):
    """Test successfully creating a forum post."""
    manager = ForumManager(987654321)
    mock_scheduled_event.guild.get_channel.return_value = mock_forum_channel
    mock_forum_channel.create_thread.return_value = mock_thread
    
    result = await manager.create_forum_post(mock_scheduled_event, sample_participants)
    
    assert result == mock_thread
    assert manager.event_posts[mock_scheduled_event.id] == mock_thread
    mock_forum_channel.create_thread.assert_called_once()
    call_args = mock_forum_channel.create_thread.call_args
    assert call_args.kwargs['name'] == "Kitchen Sync Event"
    assert call_args.kwargs['auto_archive_duration'] == 1440


@pytest.mark.asyncio
async def test_create_forum_post_with_calendar_link(mock_scheduled_event, mock_forum_channel, mock_thread, sample_participants):
    """Test creating a forum post with calendar link."""
    manager = ForumManager(987654321)
    mock_scheduled_event.guild.get_channel.return_value = mock_forum_channel
    mock_forum_channel.create_thread.return_value = mock_thread
    calendar_link = "https://calendar.google.com/calendar/render?action=TEMPLATE&text=Test"
    
    result = await manager.create_forum_post(mock_scheduled_event, sample_participants, calendar_link)
    
    assert result == mock_thread
    assert manager.calendar_links[mock_scheduled_event.id] == calendar_link


@pytest.mark.asyncio
async def test_create_forum_post_no_channel(mock_scheduled_event, sample_participants):
    """Test creating forum post when channel doesn't exist."""
    manager = ForumManager(987654321)
    mock_scheduled_event.guild.get_channel.return_value = None
    
    result = await manager.create_forum_post(mock_scheduled_event, sample_participants)
    
    assert result is None
    assert mock_scheduled_event.id not in manager.event_posts


@pytest.mark.asyncio
async def test_create_forum_post_permission_error(mock_scheduled_event, mock_forum_channel, sample_participants):
    """Test creating forum post with permission error."""
    manager = ForumManager(987654321)
    mock_scheduled_event.guild.get_channel.return_value = mock_forum_channel
    mock_forum_channel.create_thread.side_effect = discord.Forbidden(MagicMock(), "No permission")
    
    result = await manager.create_forum_post(mock_scheduled_event, sample_participants)
    
    assert result is None


@pytest.mark.asyncio
async def test_update_forum_post_success(mock_scheduled_event, mock_thread, mock_message, sample_participants):
    """Test successfully updating a forum post."""
    manager = ForumManager(987654321)
    manager.event_posts[mock_scheduled_event.id] = mock_thread
    
    # Mock the history iterator - history() should return an async iterator
    async def history_generator():
        yield mock_message
    
    mock_thread.history = lambda limit=100, oldest_first=True: history_generator()
    
    result = await manager.update_forum_post(mock_scheduled_event, sample_participants)
    
    assert result is True
    mock_message.edit.assert_called_once()


@pytest.mark.asyncio
async def test_update_forum_post_with_calendar_link(mock_scheduled_event, mock_thread, mock_message, sample_participants):
    """Test updating a forum post with calendar link."""
    manager = ForumManager(987654321)
    manager.event_posts[mock_scheduled_event.id] = mock_thread
    calendar_link = "https://calendar.google.com/calendar/render?action=TEMPLATE&text=Updated"
    
    async def history_generator():
        yield mock_message
    
    mock_thread.history = lambda limit=100, oldest_first=True: history_generator()
    
    result = await manager.update_forum_post(mock_scheduled_event, sample_participants, calendar_link)
    
    assert result is True
    assert manager.calendar_links[mock_scheduled_event.id] == calendar_link
    mock_message.edit.assert_called_once()


@pytest.mark.asyncio
async def test_update_forum_post_not_found_creates_new(mock_scheduled_event, mock_forum_channel, mock_thread, sample_participants):
    """Test updating a forum post that doesn't exist creates a new one."""
    manager = ForumManager(987654321)
    mock_scheduled_event.guild.get_channel.return_value = mock_forum_channel
    mock_forum_channel.create_thread.return_value = mock_thread
    
    result = await manager.update_forum_post(mock_scheduled_event, sample_participants)
    
    assert result is True
    assert manager.event_posts[mock_scheduled_event.id] == mock_thread


@pytest.mark.asyncio
async def test_update_forum_post_no_message(mock_scheduled_event, mock_thread):
    """Test updating forum post when first message can't be found."""
    manager = ForumManager(987654321)
    manager.event_posts[mock_scheduled_event.id] = mock_thread
    
    # Mock empty history
    async def empty_history():
        if False:
            yield  # Make it an async generator
    
    mock_thread.history = lambda limit=100, oldest_first=True: empty_history()
    
    result = await manager.update_forum_post(mock_scheduled_event, [])
    
    assert result is False


@pytest.mark.asyncio
async def test_archive_forum_post_success(mock_thread, mock_archive_category):
    """Test successfully archiving a forum post."""
    manager = ForumManager(987654321)
    event_id = 444555666
    manager.event_posts[event_id] = mock_thread
    
    result = await manager.archive_forum_post(event_id, mock_archive_category)
    
    assert result is True
    assert event_id not in manager.event_posts
    mock_thread.edit.assert_called_once_with(archived=True, locked=True)


@pytest.mark.asyncio
async def test_archive_forum_post_not_found():
    """Test archiving a forum post that doesn't exist."""
    manager = ForumManager(987654321)
    mock_archive_category = MagicMock()
    
    result = await manager.archive_forum_post(999999999, mock_archive_category)
    
    assert result is False


@pytest.mark.asyncio
async def test_archive_forum_post_permission_error(mock_thread, mock_archive_category):
    """Test archiving forum post with permission error."""
    manager = ForumManager(987654321)
    event_id = 444555666
    manager.event_posts[event_id] = mock_thread
    mock_thread.edit.side_effect = discord.Forbidden(MagicMock(), "No permission")
    
    result = await manager.archive_forum_post(event_id, mock_archive_category)
    
    assert result is False
    # On permission error, the thread should still be removed from tracking
    # (the actual implementation removes it before the error, so this is expected)


@pytest.mark.asyncio
async def test_update_thread_name_success(mock_thread):
    """Test successfully updating thread name."""
    manager = ForumManager(987654321)
    event_id = 444555666
    manager.event_posts[event_id] = mock_thread
    mock_thread.edit = AsyncMock()
    
    result = await manager.update_thread_name(event_id, "New Event Name")
    
    assert result is True
    mock_thread.edit.assert_called_once_with(name="New Event Name")


@pytest.mark.asyncio
async def test_update_thread_name_not_found():
    """Test updating thread name when thread doesn't exist."""
    manager = ForumManager(987654321)
    
    result = await manager.update_thread_name(999999999, "New Event Name")
    
    assert result is False


@pytest.mark.asyncio
async def test_update_thread_name_permission_error(mock_thread):
    """Test updating thread name with permission error."""
    manager = ForumManager(987654321)
    event_id = 444555666
    manager.event_posts[event_id] = mock_thread
    mock_thread.edit = AsyncMock(side_effect=discord.Forbidden(MagicMock(), "No permission"))
    
    result = await manager.update_thread_name(event_id, "New Event Name")
    
    assert result is False


@pytest.mark.asyncio
async def test_update_thread_name_http_error(mock_thread):
    """Test updating thread name with HTTP error."""
    manager = ForumManager(987654321)
    event_id = 444555666
    manager.event_posts[event_id] = mock_thread
    mock_thread.edit = AsyncMock(side_effect=discord.HTTPException(MagicMock(), "HTTP error"))
    
    result = await manager.update_thread_name(event_id, "New Event Name")
    
    assert result is False


@pytest.mark.asyncio
async def test_update_thread_name_truncation(mock_thread):
    """Test updating thread name with name that exceeds 100 characters."""
    manager = ForumManager(987654321)
    event_id = 444555666
    manager.event_posts[event_id] = mock_thread
    mock_thread.edit = AsyncMock()
    
    # Create a name longer than 100 characters
    long_name = "A" * 150
    result = await manager.update_thread_name(event_id, long_name)
    
    assert result is True
    # Should truncate to 100 characters
    mock_thread.edit.assert_called_once_with(name="A" * 100)


@pytest.mark.asyncio
async def test_find_existing_thread_success(mock_guild, mock_forum_channel, mock_thread):
    """Test finding an existing thread."""
    manager = ForumManager(987654321)
    mock_guild.get_channel.return_value = mock_forum_channel
    mock_forum_channel.threads = [mock_thread]
    mock_thread.name = "Kitchen Sync Event"
    
    result = await manager.find_existing_thread(mock_guild, "Kitchen Sync Event")
    
    assert result == mock_thread


@pytest.mark.asyncio
async def test_find_existing_thread_not_found(mock_guild, mock_forum_channel):
    """Test finding a thread that doesn't exist."""
    manager = ForumManager(987654321)
    mock_guild.get_channel.return_value = mock_forum_channel
    mock_forum_channel.threads = []
    
    # Mock archived_threads to return empty
    async def empty_archived():
        return
        yield
    mock_forum_channel.archived_threads = lambda limit=50: empty_archived()
    
    result = await manager.find_existing_thread(mock_guild, "Non-existent Event")
    
    assert result is None


@pytest.mark.asyncio
async def test_get_thread(mock_thread):
    """Test getting a thread from the mapping."""
    manager = ForumManager(987654321)
    event_id = 444555666
    manager.event_posts[event_id] = mock_thread
    
    result = manager.get_thread(event_id)
    
    assert result == mock_thread


@pytest.mark.asyncio
async def test_get_thread_not_found():
    """Test getting a thread that doesn't exist."""
    manager = ForumManager(987654321)
    
    result = manager.get_thread(999999999)
    
    assert result is None

