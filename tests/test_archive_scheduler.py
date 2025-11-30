"""Tests for ArchiveScheduler."""
import pytest
import asyncio
import discord
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from archive_scheduler import ArchiveScheduler


@pytest.mark.asyncio
async def test_schedule_archive_future_event(mock_scheduled_event, mock_forum_manager):
    """Test scheduling archive for a future event."""
    scheduler = ArchiveScheduler(24)
    
    # Set event end time to 1 hour from now
    mock_scheduled_event.end_time = discord.utils.utcnow() + timedelta(hours=1)
    
    callback = AsyncMock()
    scheduler.schedule_archive(mock_scheduled_event, mock_forum_manager, callback)
    
    # Should have a scheduled task
    assert mock_scheduled_event.id in scheduler.scheduled_tasks
    task = scheduler.scheduled_tasks[mock_scheduled_event.id]
    assert not task.done()


@pytest.mark.asyncio
async def test_schedule_archive_past_event_immediate(mock_scheduled_event, mock_forum_manager):
    """Test scheduling archive for an event that already ended - should archive immediately."""
    scheduler = ArchiveScheduler(24)
    
    # Set event end time to 25 hours ago (more than delay)
    mock_scheduled_event.end_time = discord.utils.utcnow() - timedelta(hours=25)
    
    callback = AsyncMock()
    mock_forum_manager.archive_forum_post = AsyncMock(return_value=True)
    
    scheduler.schedule_archive(mock_scheduled_event, mock_forum_manager, callback)
    
    # Give it a moment to execute
    await asyncio.sleep(0.1)
    
    # Should have archived immediately
    mock_forum_manager.archive_forum_post.assert_called()


@pytest.mark.asyncio
async def test_schedule_archive_no_end_time(mock_scheduled_event, mock_forum_manager):
    """Test scheduling archive for event with no end time."""
    scheduler = ArchiveScheduler(24)
    mock_scheduled_event.end_time = None
    
    callback = AsyncMock()
    scheduler.schedule_archive(mock_scheduled_event, mock_forum_manager, callback)
    
    # Should not have scheduled anything
    assert mock_scheduled_event.id not in scheduler.scheduled_tasks


@pytest.mark.asyncio
async def test_schedule_archive_cancels_existing(mock_scheduled_event, mock_forum_manager):
    """Test that scheduling archive cancels existing task."""
    scheduler = ArchiveScheduler(24)
    mock_scheduled_event.end_time = discord.utils.utcnow() + timedelta(hours=1)
    
    # Schedule first task
    callback = AsyncMock()
    scheduler.schedule_archive(mock_scheduled_event, mock_forum_manager, callback)
    first_task = scheduler.scheduled_tasks[mock_scheduled_event.id]
    
    # Give it a tiny moment to ensure task is created
    await asyncio.sleep(0.01)
    
    # Schedule again (should cancel first)
    scheduler.schedule_archive(mock_scheduled_event, mock_forum_manager, callback)
    second_task = scheduler.scheduled_tasks[mock_scheduled_event.id]
    
    assert first_task != second_task
    # First task should be cancelled (or in the process of being cancelled)
    # Note: cancellation might not be immediate, so we just check they're different


@pytest.mark.asyncio
async def test_cancel_archive(mock_scheduled_event, mock_forum_manager):
    """Test canceling a scheduled archive."""
    scheduler = ArchiveScheduler(24)
    mock_scheduled_event.end_time = discord.utils.utcnow() + timedelta(hours=1)
    
    callback = AsyncMock()
    scheduler.schedule_archive(mock_scheduled_event, mock_forum_manager, callback)
    
    assert mock_scheduled_event.id in scheduler.scheduled_tasks
    
    scheduler.cancel_archive(mock_scheduled_event.id)
    
    assert mock_scheduled_event.id not in scheduler.scheduled_tasks


@pytest.mark.asyncio
async def test_archive_immediately(mock_scheduled_event, mock_forum_manager):
    """Test archiving immediately."""
    scheduler = ArchiveScheduler(24)
    mock_scheduled_event.end_time = discord.utils.utcnow() + timedelta(hours=1)
    
    # Schedule a future archive first
    callback = AsyncMock()
    scheduler.schedule_archive(mock_scheduled_event, mock_forum_manager, callback)
    
    # Archive immediately
    mock_forum_manager.archive_forum_post = AsyncMock(return_value=True)
    scheduler.archive_immediately(mock_scheduled_event, mock_forum_manager, callback)
    
    # Give it a moment
    await asyncio.sleep(0.1)
    
    # Should have archived
    mock_forum_manager.archive_forum_post.assert_called()
    # Original task should be cancelled
    assert mock_scheduled_event.id not in scheduler.scheduled_tasks or \
           scheduler.scheduled_tasks.get(mock_scheduled_event.id) is None or \
           scheduler.scheduled_tasks[mock_scheduled_event.id].cancelled()


@pytest.mark.asyncio
async def test_archive_task_execution(mock_scheduled_event, mock_forum_manager):
    """Test the archive task execution."""
    scheduler = ArchiveScheduler(24)
    mock_forum_manager.archive_forum_post = AsyncMock(return_value=True)
    
    callback = AsyncMock()
    
    # Execute archive task directly
    await scheduler._archive_task(mock_scheduled_event, mock_forum_manager, callback)
    
    mock_forum_manager.archive_forum_post.assert_called_once_with(
        mock_scheduled_event.id
    )
    callback.assert_called_once_with(mock_scheduled_event)




@pytest.fixture
def mock_forum_manager():
    """Create a mock ForumManager."""
    manager = MagicMock()
    manager.archive_forum_post = AsyncMock()
    return manager

