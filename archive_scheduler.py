"""Manages scheduling and execution of forum post archiving."""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import discord

logger = logging.getLogger(__name__)


class ArchiveScheduler:
    """Handles scheduling archive tasks for forum posts."""
    
    def __init__(self, archive_delay_hours: int, archive_category_id: int):
        """
        Initialize the ArchiveScheduler.
        
        Args:
            archive_delay_hours: Hours to wait after event completion before archiving
            archive_category_id: ID of the category/channel for archived posts
        """
        self.archive_delay_hours = archive_delay_hours
        self.archive_category_id = archive_category_id
        self.scheduled_tasks: Dict[int, asyncio.Task] = {}  # event_id -> task mapping
    
    async def get_archive_category(self, guild: discord.Guild) -> Optional[discord.CategoryChannel]:
        """Get the archive category from the guild."""
        try:
            category = guild.get_channel(self.archive_category_id)
            if isinstance(category, discord.CategoryChannel):
                return category
            # Could also be a channel, which is fine
            if category:
                return category
            logger.error(f"Archive category/channel {self.archive_category_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error getting archive category: {e}")
            return None
    
    def schedule_archive(
        self, 
        event: discord.ScheduledEvent, 
        forum_manager,
        callback
    ):
        """
        Schedule an archive task for an event.
        
        Args:
            event: The scheduled event to archive
            forum_manager: The ForumManager instance
            callback: Callback function to call when archiving
        """
        # Cancel any existing task for this event
        if event.id in self.scheduled_tasks:
            self.scheduled_tasks[event.id].cancel()
        
        # Calculate when to archive
        if not event.end_time:
            logger.warning(f"Event {event.id} has no end time, cannot schedule archive")
            return
        
        archive_time = event.end_time + timedelta(hours=self.archive_delay_hours)
        delay_seconds = (archive_time - discord.utils.utcnow()).total_seconds()
        
        # If the delay is negative (event already ended more than delay_hours ago), archive immediately
        if delay_seconds <= 0:
            logger.info(f"Event {event.id} ended more than {self.archive_delay_hours} hours ago, archiving immediately")
            asyncio.create_task(self._archive_task(event, forum_manager, callback))
            return
        
        # Schedule the archive task
        task = asyncio.create_task(
            self._archive_task_delayed(event, forum_manager, callback, delay_seconds)
        )
        self.scheduled_tasks[event.id] = task
        
        logger.info(f"Scheduled archive for event {event.id} at {archive_time}")
    
    async def _archive_task_delayed(
        self, 
        event: discord.ScheduledEvent, 
        forum_manager, 
        callback, 
        delay_seconds: float
    ):
        """Wait for the delay, then execute the archive task."""
        try:
            await asyncio.sleep(delay_seconds)
            await self._archive_task(event, forum_manager, callback)
        except asyncio.CancelledError:
            logger.info(f"Archive task for event {event.id} was cancelled")
        except Exception as e:
            logger.error(f"Error in archive task for event {event.id}: {e}")
    
    async def _archive_task(
        self, 
        event: discord.ScheduledEvent, 
        forum_manager, 
        callback
    ):
        """Execute the archive task."""
        try:
            archive_category = await self.get_archive_category(event.guild)
            if not archive_category:
                logger.error(f"Cannot archive event {event.id}: archive category not found")
                return
            
            success = await forum_manager.archive_forum_post(event.id, archive_category)
            if success and callback:
                await callback(event, archive_category)
            
            # Remove the task from tracking
            if event.id in self.scheduled_tasks:
                del self.scheduled_tasks[event.id]
                
        except Exception as e:
            logger.error(f"Error executing archive task for event {event.id}: {e}")
    
    def cancel_archive(self, event_id: int):
        """Cancel a scheduled archive task."""
        if event_id in self.scheduled_tasks:
            self.scheduled_tasks[event_id].cancel()
            del self.scheduled_tasks[event_id]
            logger.info(f"Cancelled archive task for event {event_id}")
    
    def archive_immediately(
        self, 
        event: discord.ScheduledEvent, 
        forum_manager, 
        callback
    ):
        """Archive a forum post immediately (e.g., when event is deleted)."""
        # Cancel any scheduled task
        self.cancel_archive(event.id)
        
        # Archive immediately
        asyncio.create_task(self._archive_task(event, forum_manager, callback))
        logger.info(f"Archiving event {event.id} immediately")

