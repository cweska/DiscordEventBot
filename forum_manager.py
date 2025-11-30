"""Manages forum post creation and updates for Discord events."""
import discord
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class ForumManager:
    """Handles creation and updates of forum posts for scheduled events."""
    
    def __init__(self, forum_channel_id: int, calendar_manager=None):
        """
        Initialize the ForumManager.
        
        Args:
            forum_channel_id: The ID of the forum channel where posts are created
            calendar_manager: Optional CalendarManager instance for calendar integration
        """
        self.forum_channel_id = forum_channel_id
        self.event_posts: Dict[int, discord.Thread] = {}  # event_id -> thread mapping
        self.calendar_manager = calendar_manager
        self.calendar_links: Dict[int, str] = {}  # event_id -> calendar_link mapping
        self.cached_participants: Dict[int, list] = {}  # event_id -> last known participants
    
    async def get_forum_channel(self, guild: discord.Guild) -> Optional[discord.ForumChannel]:
        """Get the forum channel from the guild."""
        try:
            channel = guild.get_channel(self.forum_channel_id)
            if isinstance(channel, discord.ForumChannel):
                return channel
            logger.error(f"Channel {self.forum_channel_id} is not a ForumChannel")
            return None
        except Exception as e:
            logger.error(f"Error getting forum channel: {e}")
            return None
    
    def format_event_content(self, event: discord.ScheduledEvent, participants: list, calendar_link: Optional[str] = None) -> str:
        """
        Format the content for a forum post.
        
        Args:
            event: The scheduled event
            participants: List of participant user objects
            calendar_link: Optional Google Calendar link to include
            
        Returns:
            Formatted string content for the forum post
        """
        content_parts = []
        
        # Event description
        if event.description:
            content_parts.append(f"**Event Description:**\n{event.description}\n")
        
        # Event timing
        start_time = f"<t:{int(event.start_time.timestamp())}:F>"
        content_parts.append(f"**Start Time:** {start_time}")
        
        if event.end_time:
            end_time = f"<t:{int(event.end_time.timestamp())}:F>"
            content_parts.append(f"**End Time:** {end_time}\n")
        else:
            content_parts.append("**End Time:** Not specified\n")
        
        # Calendar link (if available)
        if calendar_link:
            content_parts.append("📅 **Add to Calendar:**")
            content_parts.append(f"[Click here to add to Google Calendar]({calendar_link})\n")
        
        # Participant information
        participant_count = len(participants)
        content_parts.append(f"**Participants:** {participant_count}")
        
        if participants:
            participant_list = ", ".join([user.mention for user in participants[:20]])  # Limit to 20 mentions
            if len(participants) > 20:
                participant_list += f" and {len(participants) - 20} more"
            content_parts.append(participant_list)
        else:
            content_parts.append("No participants yet. Join the event to be added!")
        
        content_parts.append("\n---")
        content_parts.append("💬 **Use this space to:**")
        content_parts.append("• Share what you're planning to cook")
        content_parts.append("• Chat before the event starts")
        content_parts.append("• Post updates while cooking")
        content_parts.append("• Share photos of your finished meal")
        content_parts.append("• Give kudos to others!")
        
        return "\n".join(content_parts)
    
    async def create_forum_post(
        self, 
        event: discord.ScheduledEvent, 
        participants: list,
        calendar_link: Optional[str] = None
    ) -> Optional[discord.Thread]:
        """
        Create a forum post for a scheduled event.
        
        Args:
            event: The scheduled event
            participants: List of participant user objects
            calendar_link: Optional Google Calendar link to include
            
        Returns:
            The created thread, or None if creation failed
        """
        try:
            # Check if forum post already exists to prevent duplicates
            if event.id in self.event_posts:
                logger.warning(f"Forum post already exists for event {event.id}, skipping creation")
                return self.event_posts[event.id]
            
            forum_channel = await self.get_forum_channel(event.guild)
            if not forum_channel:
                return None
            
            # Store calendar link if provided
            if calendar_link:
                self.calendar_links[event.id] = calendar_link
            
            # Cache participants
            if participants:
                self.cached_participants[event.id] = participants
            
            # Format the content
            content = self.format_event_content(event, participants, calendar_link)
            
            # Create the forum post
            # Note: create_thread may return ThreadWithMessage (a named tuple) in some discord.py versions
            result = await forum_channel.create_thread(
                name=event.name,
                content=content,
                auto_archive_duration=1440,  # 24 hours
            )
            
            # Handle ThreadWithMessage (named tuple with .thread and .message attributes)
            # or regular Thread object
            if hasattr(result, 'thread'):
                # This is a ThreadWithMessage named tuple
                thread = result.thread
            else:
                # This is already a Thread object
                thread = result
            
            # Store the mapping
            self.event_posts[event.id] = thread
            
            logger.info(f"Created forum post for event '{event.name}' (ID: {event.id})")
            return thread
            
        except discord.Forbidden:
            logger.error(f"Bot lacks permissions to create forum posts in channel {self.forum_channel_id}")
            return None
        except discord.HTTPException as e:
            logger.error(f"HTTP error creating forum post: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating forum post: {e}")
            return None
    
    async def update_forum_post(
        self, 
        event: discord.ScheduledEvent, 
        participants: list,
        calendar_link: Optional[str] = None
    ) -> bool:
        """
        Update an existing forum post with new information.
        
        Args:
            event: The scheduled event
            participants: Updated list of participant user objects
            calendar_link: Optional updated Google Calendar link
            
        Returns:
            True if update was successful, False otherwise
        """
        try:
            thread = self.event_posts.get(event.id)
            if not thread:
                logger.warning(f"No forum post found for event {event.id}, creating new one")
                await self.create_forum_post(event, participants, calendar_link)
                return True
            
            # Update calendar link if provided
            if calendar_link:
                self.calendar_links[event.id] = calendar_link
            else:
                # Use existing calendar link if available
                calendar_link = self.calendar_links.get(event.id)
                # If no calendar link exists, generate one (shouldn't happen, but be safe)
                if not calendar_link and self.calendar_manager:
                    calendar_link = self.calendar_manager.generate_calendar_link(event)
                    if calendar_link:
                        self.calendar_links[event.id] = calendar_link
            
            # If participants list is empty but we have cached participants, use cached ones
            # This prevents clearing participants when event.users() fails
            if not participants and event.id in self.cached_participants:
                logger.warning(f"Participants list is empty for event {event.id}, using cached participants")
                participants = self.cached_participants[event.id]
            elif participants:
                # Update cache with new participants list
                self.cached_participants[event.id] = participants
            
            # Get the first message (the post content)
            # For forum posts, the starter message is the first message in the thread
            first_message = None
            async for message in thread.history(limit=1, oldest_first=True):
                first_message = message
                break
            
            if not first_message:
                logger.error(f"Could not find first message in thread {thread.id}")
                return False
            
            # Format updated content
            content = self.format_event_content(event, participants, calendar_link)
            
            # Update the message
            await first_message.edit(content=content)
            
            logger.info(f"Updated forum post for event '{event.name}' (ID: {event.id})")
            return True
            
        except discord.Forbidden:
            logger.error(f"Bot lacks permissions to update forum post for event {event.id}")
            return False
        except discord.HTTPException as e:
            logger.error(f"HTTP error updating forum post: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error updating forum post: {e}")
            return False
    
    async def update_thread_name(self, event_id: int, new_name: str) -> bool:
        """
        Update the name of a forum thread when the event name changes.
        
        Args:
            event_id: The ID of the scheduled event
            new_name: The new name for the thread
            
        Returns:
            True if update was successful, False otherwise
        """
        try:
            thread = self.event_posts.get(event_id)
            if not thread:
                logger.warning(f"No forum thread found for event {event_id}, cannot update thread name")
                return False
            
            # Discord has a 100 character limit for channel/thread names
            # Truncate if necessary
            if len(new_name) > 100:
                logger.warning(f"Thread name '{new_name}' exceeds 100 characters, truncating")
                new_name = new_name[:100]
            
            # Update the thread name
            await thread.edit(name=new_name)
            logger.info(f"Updated thread name for event {event_id} to '{new_name}'")
            return True
            
        except discord.Forbidden:
            logger.error(f"Bot lacks permissions to update thread name for event {event_id}")
            return False
        except discord.HTTPException as e:
            logger.error(f"HTTP error updating thread name: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error updating thread name: {e}")
            return False
    
    async def archive_forum_post(
        self, 
        event_id: int
    ) -> bool:
        """
        Close a forum post by archiving it.
        
        This closes the forum thread, which automatically moves it to Discord's
        "Older Posts" section. The post remains readable but is no longer active.
        
        Args:
            event_id: The ID of the event
            
        Returns:
            True if closing was successful, False otherwise
        """
        try:
            thread = self.event_posts.get(event_id)
            if not thread:
                logger.warning(f"No forum post found for event {event_id} to close")
                return False
            
            # Handle ThreadWithMessage objects - extract the thread if needed
            # ThreadWithMessage is a named tuple with .thread and .message attributes
            if hasattr(thread, 'thread') and not hasattr(thread, 'edit'):
                # This is a ThreadWithMessage named tuple, get the actual thread
                actual_thread = thread.thread
            else:
                # This is already a Thread object (or has edit method)
                actual_thread = thread
            
            # Close the thread (archive it) - this moves it to "Older Posts" section
            await actual_thread.edit(archived=True)
            
            # Remove from our tracking
            del self.event_posts[event_id]
            
            logger.info(f"Closed forum post for event {event_id}")
            return True
            
        except discord.Forbidden:
            logger.error(f"Bot lacks permissions to close forum post for event {event_id}")
            return False
        except discord.HTTPException as e:
            logger.error(f"HTTP error closing forum post: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error archiving forum post: {e}")
            return False
    
    def get_thread(self, event_id: int) -> Optional[discord.Thread]:
        """Get the thread associated with an event ID."""
        return self.event_posts.get(event_id)
    
    async def find_existing_thread(
        self, 
        guild: discord.Guild, 
        event_name: str
    ) -> Optional[discord.Thread]:
        """
        Try to find an existing forum thread by event name.
        Useful when bot restarts and needs to reconnect to existing threads.
        
        Args:
            guild: The guild to search in
            event_name: The name of the event to search for
            
        Returns:
            The thread if found, None otherwise
        """
        try:
            forum_channel = await self.get_forum_channel(guild)
            if not forum_channel:
                return None
            
            # Check active threads first (most common case)
            for thread in forum_channel.threads:
                if thread.name == event_name and not thread.archived:
                    return thread
            
            # Search through recently archived threads (within last 7 days)
            # Note: This is a best-effort search and may not find all threads
            try:
                async for thread in forum_channel.archived_threads(limit=50):
                    if thread.name == event_name:
                        return thread
            except discord.Forbidden:
                # Bot may not have permission to view archived threads
                logger.debug("Bot lacks permission to view archived threads")
            
            return None
        except Exception as e:
            logger.error(f"Error finding existing thread: {e}")
            return None

