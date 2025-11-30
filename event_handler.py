"""Event handlers for Discord scheduled events."""
import discord
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class EventHandler:
    """Handles Discord scheduled event lifecycle events."""
    
    def __init__(self, forum_manager, archive_scheduler, calendar_manager=None):
        """
        Initialize the EventHandler.
        
        Args:
            forum_manager: ForumManager instance
            archive_scheduler: ArchiveScheduler instance
            calendar_manager: Optional CalendarManager instance
        """
        self.forum_manager = forum_manager
        self.archive_scheduler = archive_scheduler
        self.calendar_manager = calendar_manager
    
    async def get_event_participants(self, event: discord.ScheduledEvent) -> Optional[list]:
        """
        Get the list of users subscribed to an event.
        
        Args:
            event: The scheduled event
            
        Returns:
            List of user objects who are subscribed to the event, or None if fetching failed
            (None allows the caller to decide whether to use cached values)
        """
        try:
            participants = []
            async for user in event.users():
                participants.append(user)
            return participants
        except Exception as e:
            logger.error(f"Error getting participants for event {event.id}: {e}")
            # Return None instead of empty list to indicate failure
            # This allows callers to distinguish between "no participants" and "fetch failed"
            return None
    
    async def on_scheduled_event_create(self, event: discord.ScheduledEvent):
        """
        Handle when a scheduled event is created.
        
        Args:
            event: The created scheduled event
        """
        try:
            logger.info(f"Event created: {event.name} (ID: {event.id})")
            
            # Check if forum post already exists to prevent duplicates
            if self.forum_manager.get_thread(event.id):
                logger.info(f"Forum post already exists for event {event.id}, skipping creation")
                return
            
            # Get initial participants
            participants = await self.get_event_participants(event)
            
            # Generate calendar link if calendar manager is available
            calendar_link = None
            if self.calendar_manager:
                calendar_link = self.calendar_manager.generate_calendar_link(event)
            
            # Create forum post
            thread = await self.forum_manager.create_forum_post(event, participants, calendar_link)
            
            if thread:
                # Schedule archive task
                self.archive_scheduler.schedule_archive(
                    event, 
                    self.forum_manager, 
                    self._on_archive_complete
                )
                logger.info(f"Successfully set up forum post for event {event.id}")
            else:
                logger.error(f"Failed to create forum post for event {event.id}")
                
        except Exception as e:
            logger.error(f"Error handling event creation: {e}")
    
    async def on_scheduled_event_update(self, event: discord.ScheduledEvent):
        """
        Handle when a scheduled event is updated.
        
        Args:
            event: The updated scheduled event
        """
        try:
            logger.info(f"Event updated: {event.name} (ID: {event.id})")
            
            # Get current participants (may return None if fetch fails)
            participants = await self.get_event_participants(event)
            
            # If fetching participants failed, use empty list and let update_forum_post use cached values
            if participants is None:
                participants = []
            
            # Regenerate calendar link if calendar manager is available
            calendar_link = None
            if self.calendar_manager:
                calendar_link = self.calendar_manager.generate_calendar_link_for_update(event)
            
            # Update forum post (will use cached participants if participants list is empty)
            await self.forum_manager.update_forum_post(event, participants, calendar_link)
            
            # Reschedule archive if end time changed
            self.archive_scheduler.schedule_archive(
                event, 
                self.forum_manager, 
                self._on_archive_complete
            )
            
        except Exception as e:
            logger.error(f"Error handling event update: {e}")
    
    async def on_scheduled_event_delete(self, event: discord.ScheduledEvent):
        """
        Handle when a scheduled event is deleted.
        
        Args:
            event: The deleted scheduled event
        """
        try:
            logger.info(f"Event deleted: {event.name} (ID: {event.id})")
            
            # Archive immediately
            self.archive_scheduler.archive_immediately(
                event, 
                self.forum_manager, 
                self._on_archive_complete
            )
            
        except Exception as e:
            logger.error(f"Error handling event deletion: {e}")
    
    async def on_scheduled_event_user_add(
        self, 
        event: discord.ScheduledEvent, 
        user: discord.User
    ):
        """
        Handle when a user subscribes to a scheduled event.
        
        Args:
            event: The scheduled event
            user: The user who subscribed
        """
        try:
            logger.info(f"User {user.name} subscribed to event {event.name} (ID: {event.id})")
            
            # Get updated participants (must succeed for user add/remove events)
            participants = await self.get_event_participants(event)
            if participants is None:
                # If fetch failed, log error but try to continue with cached participants
                logger.warning(f"Failed to fetch participants for event {event.id} after user add, using cached")
                participants = self.forum_manager.cached_participants.get(event.id, [])
            
            # Preserve existing calendar link (don't regenerate, just use existing)
            calendar_link = self.forum_manager.calendar_links.get(event.id)
            if not calendar_link and self.calendar_manager:
                # Generate if missing (shouldn't happen, but be safe)
                calendar_link = self.calendar_manager.generate_calendar_link(event)
            
            # Update forum post
            await self.forum_manager.update_forum_post(event, participants, calendar_link)
            
        except Exception as e:
            logger.error(f"Error handling user subscription: {e}")
    
    async def on_scheduled_event_user_remove(
        self, 
        event: discord.ScheduledEvent, 
        user: discord.User
    ):
        """
        Handle when a user unsubscribes from a scheduled event.
        
        Args:
            event: The scheduled event
            user: The user who unsubscribed
        """
        try:
            logger.info(f"User {user.name} unsubscribed from event {event.name} (ID: {event.id})")
            
            # Get updated participants (must succeed for user add/remove events)
            participants = await self.get_event_participants(event)
            if participants is None:
                # If fetch failed, log error but try to continue with cached participants
                logger.warning(f"Failed to fetch participants for event {event.id} after user remove, using cached")
                participants = self.forum_manager.cached_participants.get(event.id, [])
            
            # Preserve existing calendar link (don't regenerate, just use existing)
            calendar_link = self.forum_manager.calendar_links.get(event.id)
            if not calendar_link and self.calendar_manager:
                # Generate if missing (shouldn't happen, but be safe)
                calendar_link = self.calendar_manager.generate_calendar_link(event)
            
            # Update forum post
            await self.forum_manager.update_forum_post(event, participants, calendar_link)
            
        except Exception as e:
            logger.error(f"Error handling user unsubscription: {e}")
    
    async def _on_archive_complete(
        self, 
        event: discord.ScheduledEvent, 
        archive_category: discord.CategoryChannel
    ):
        """
        Callback when archiving is complete.
        
        Args:
            event: The archived event
            archive_category: The category where it was archived
        """
        logger.info(f"Successfully archived forum post for event {event.name} (ID: {event.id})")

