"""Tests for EventHandler."""
import pytest
import discord
from unittest.mock import AsyncMock, MagicMock
from event_handler import EventHandler


@pytest.mark.asyncio
async def test_get_event_participants_success(mock_scheduled_event, sample_participants):
    """Test getting event participants successfully."""
    handler = EventHandler(MagicMock(), MagicMock())
    
    # Mock the users iterator - make it an async iterator
    async def users_generator():
        for participant in sample_participants:
            yield participant
    
    # Set up the async iterator properly - users() should return the generator
    mock_scheduled_event.users = lambda: users_generator()
    
    result = await handler.get_event_participants(mock_scheduled_event)
    
    assert len(result) == 3
    assert result == sample_participants


@pytest.mark.asyncio
async def test_get_event_participants_empty(mock_scheduled_event):
    """Test getting participants when event has none."""
    handler = EventHandler(MagicMock(), MagicMock())
    
    async def empty_users():
        if False:
            yield
    
    mock_scheduled_event.users = lambda: empty_users()
    
    result = await handler.get_event_participants(mock_scheduled_event)
    
    assert result == []


@pytest.mark.asyncio
async def test_get_event_participants_error(mock_scheduled_event):
    """Test handling error when getting participants."""
    handler = EventHandler(MagicMock(), MagicMock())
    
    def error_users():
        raise Exception("API Error")
    
    mock_scheduled_event.users = error_users
    
    result = await handler.get_event_participants(mock_scheduled_event)
    
    assert result == []


@pytest.mark.asyncio
async def test_on_scheduled_event_create_success(mock_scheduled_event, sample_participants, mock_thread):
    """Test handling event creation successfully."""
    forum_manager = MagicMock()
    archive_scheduler = MagicMock()
    calendar_manager = MagicMock()
    handler = EventHandler(forum_manager, archive_scheduler, calendar_manager)
    
    # Mock getting participants
    async def users_generator():
        for participant in sample_participants:
            yield participant
    
    mock_scheduled_event.users = lambda: users_generator()
    
    forum_manager.get_thread = MagicMock(return_value=None)  # No existing thread
    forum_manager.create_forum_post = AsyncMock(return_value=mock_thread)
    calendar_manager.generate_calendar_link = MagicMock(return_value="https://calendar.google.com/link")
    
    await handler.on_scheduled_event_create(mock_scheduled_event)
    
    calendar_manager.generate_calendar_link.assert_called_once_with(mock_scheduled_event)
    forum_manager.create_forum_post.assert_called_once_with(
        mock_scheduled_event,
        sample_participants,
        "https://calendar.google.com/link"
    )
    archive_scheduler.schedule_archive.assert_called_once()


@pytest.mark.asyncio
async def test_on_scheduled_event_create_without_calendar(mock_scheduled_event, sample_participants, mock_thread):
    """Test handling event creation without calendar manager."""
    forum_manager = MagicMock()
    archive_scheduler = MagicMock()
    handler = EventHandler(forum_manager, archive_scheduler, None)
    
    async def users_generator():
        for participant in sample_participants:
            yield participant
    
    mock_scheduled_event.users = lambda: users_generator()
    
    forum_manager.get_thread = MagicMock(return_value=None)  # No existing thread
    forum_manager.create_forum_post = AsyncMock(return_value=mock_thread)
    
    await handler.on_scheduled_event_create(mock_scheduled_event)
    
    forum_manager.create_forum_post.assert_called_once_with(
        mock_scheduled_event,
        sample_participants,
        None
    )


@pytest.mark.asyncio
async def test_on_scheduled_event_create_forum_failure(mock_scheduled_event, sample_participants):
    """Test handling event creation when forum post creation fails."""
    forum_manager = MagicMock()
    archive_scheduler = MagicMock()
    handler = EventHandler(forum_manager, archive_scheduler, None)
    
    async def subscribers_generator():
        for participant in sample_participants:
            yield participant
    
    mock_scheduled_event.subscribers = lambda: subscribers_generator()
    
    forum_manager.get_thread = MagicMock(return_value=None)  # No existing thread
    forum_manager.create_forum_post = AsyncMock(return_value=None)
    
    await handler.on_scheduled_event_create(mock_scheduled_event)
    
    forum_manager.create_forum_post.assert_called_once()
    # Should not schedule archive if forum post creation failed
    archive_scheduler.schedule_archive.assert_not_called()


@pytest.mark.asyncio
async def test_on_scheduled_event_update(mock_scheduled_event, sample_participants):
    """Test handling event update."""
    forum_manager = MagicMock()
    archive_scheduler = MagicMock()
    calendar_manager = MagicMock()
    handler = EventHandler(forum_manager, archive_scheduler, calendar_manager)
    
    async def users_generator():
        for participant in sample_participants:
            yield participant
    
    mock_scheduled_event.users = lambda: users_generator()
    
    forum_manager.update_forum_post = AsyncMock(return_value=True)
    calendar_manager.generate_calendar_link_for_update = MagicMock(return_value="https://calendar.google.com/updated")
    
    await handler.on_scheduled_event_update(mock_scheduled_event)
    
    calendar_manager.generate_calendar_link_for_update.assert_called_once_with(mock_scheduled_event)
    forum_manager.update_forum_post.assert_called_once_with(
        mock_scheduled_event,
        sample_participants,
        "https://calendar.google.com/updated"
    )
    archive_scheduler.schedule_archive.assert_called_once()


@pytest.mark.asyncio
async def test_on_scheduled_event_delete(mock_scheduled_event):
    """Test handling event deletion."""
    forum_manager = MagicMock()
    archive_scheduler = MagicMock()
    calendar_manager = MagicMock()
    handler = EventHandler(forum_manager, archive_scheduler, calendar_manager)
    
    archive_scheduler.archive_immediately = MagicMock()
    
    await handler.on_scheduled_event_delete(mock_scheduled_event)
    
    # Calendar manager no longer needs to delete events (we just generate links)
    archive_scheduler.archive_immediately.assert_called_once_with(
        mock_scheduled_event,
        forum_manager,
        handler._on_archive_complete
    )


@pytest.mark.asyncio
async def test_on_scheduled_event_user_add(mock_scheduled_event, sample_participants, mock_user):
    """Test handling user joining an event."""
    forum_manager = MagicMock()
    archive_scheduler = MagicMock()
    handler = EventHandler(forum_manager, archive_scheduler)
    
    # Add the new user to participants
    updated_participants = sample_participants + [mock_user]
    
    async def users_generator():
        for participant in updated_participants:
            yield participant
    
    mock_scheduled_event.users = lambda: users_generator()
    
    forum_manager.calendar_links = {}  # Initialize calendar_links dict
    forum_manager.update_forum_post = AsyncMock(return_value=True)
    
    await handler.on_scheduled_event_user_add(mock_scheduled_event, mock_user)
    
    # Should preserve calendar link (None in this case since none exists)
    forum_manager.update_forum_post.assert_called_once()
    call_args = forum_manager.update_forum_post.call_args
    assert call_args[0][0] == mock_scheduled_event
    assert call_args[0][1] == updated_participants
    # calendar_link should be None or a generated link
    assert call_args[0][2] is None or isinstance(call_args[0][2], str)


@pytest.mark.asyncio
async def test_on_scheduled_event_user_remove(mock_scheduled_event, sample_participants, mock_user):
    """Test handling user leaving an event."""
    forum_manager = MagicMock()
    archive_scheduler = MagicMock()
    handler = EventHandler(forum_manager, archive_scheduler)
    
    # Remove one user from participants
    updated_participants = sample_participants[1:]  # Remove first participant
    
    async def users_generator():
        for participant in updated_participants:
            yield participant
    
    mock_scheduled_event.users = lambda: users_generator()
    
    forum_manager.calendar_links = {}  # Initialize calendar_links dict
    forum_manager.update_forum_post = AsyncMock(return_value=True)
    
    await handler.on_scheduled_event_user_remove(mock_scheduled_event, mock_user)
    
    # Should preserve calendar link (None in this case since none exists)
    forum_manager.update_forum_post.assert_called_once()
    call_args = forum_manager.update_forum_post.call_args
    assert call_args[0][0] == mock_scheduled_event
    assert call_args[0][1] == updated_participants
    # calendar_link should be None or a generated link
    assert call_args[0][2] is None or isinstance(call_args[0][2], str)


@pytest.mark.asyncio
async def test_on_archive_complete(mock_scheduled_event, mock_archive_category):
    """Test archive completion callback."""
    handler = EventHandler(MagicMock(), MagicMock())
    
    # This should just log, so we just verify it doesn't raise
    await handler._on_archive_complete(mock_scheduled_event, mock_archive_category)

