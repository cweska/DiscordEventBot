"""Manages scheduling and execution of event reminders."""
import asyncio
import logging
from datetime import timedelta
from typing import Dict, List, Optional, Callable, Awaitable
import discord

logger = logging.getLogger(__name__)


class ReminderScheduler:
    """Handles scheduling reminder messages for scheduled events."""
    
    def __init__(self, reminder_channel_id: int, reminder_times: List[timedelta]):
        """
        Initialize the ReminderScheduler.
        
        Args:
            reminder_channel_id: The ID of the channel where reminders are sent
            reminder_times: List of timedelta objects representing when to send reminders before event start
        """
        self.reminder_channel_id = reminder_channel_id
        self.reminder_times = reminder_times
        self.scheduled_tasks: Dict[int, List[asyncio.Task]] = {}  # event_id -> list of reminder tasks
    
    def schedule_reminders(
        self,
        event: discord.ScheduledEvent,
        get_participants_func: Callable[[discord.ScheduledEvent], Awaitable[Optional[List]]]
    ):
        """
        Schedule all reminders for an event.
        
        Args:
            event: The scheduled event
            get_participants_func: Async function to get current participants for the event
        """
        # Cancel any existing reminders for this event
        self.cancel_reminders(event.id)
        
        # Cannot schedule reminders without a start time
        if not event.start_time:
            logger.warning(f"Event {event.id} has no start time, cannot schedule reminders")
            return
        
        now = discord.utils.utcnow()
        reminder_tasks = []
        
        for reminder_time in self.reminder_times:
            # Calculate when to send this reminder (start_time - reminder_time)
            reminder_datetime = event.start_time - reminder_time
            
            # Skip reminders that are in the past
            if reminder_datetime <= now:
                logger.debug(f"Skipping reminder for event {event.id} at {reminder_datetime} (already passed)")
                continue
            
            # Skip reminders for events that have already started
            if event.start_time <= now:
                logger.debug(f"Skipping reminders for event {event.id} (event already started)")
                continue
            
            delay_seconds = (reminder_datetime - now).total_seconds()
            
            # Schedule the reminder task
            task = asyncio.create_task(
                self._reminder_task_delayed(event, delay_seconds, reminder_time, get_participants_func)
            )
            reminder_tasks.append(task)
            logger.info(f"Scheduled reminder for event {event.id} ({event.name}) at {reminder_datetime} ({reminder_time} before start)")
        
        if reminder_tasks:
            self.scheduled_tasks[event.id] = reminder_tasks
        else:
            logger.info(f"No reminders scheduled for event {event.id} (all reminder times are in the past)")
    
    async def _reminder_task_delayed(
        self,
        event: discord.ScheduledEvent,
        delay_seconds: float,
        reminder_time: timedelta,
        get_participants_func: Callable[[discord.ScheduledEvent], Awaitable[Optional[List]]]
    ):
        """Wait for the delay, then send the reminder."""
        try:
            await asyncio.sleep(delay_seconds)
            await self._send_reminder(event, reminder_time, get_participants_func)
        except asyncio.CancelledError:
            logger.info(f"Reminder task for event {event.id} was cancelled")
        except Exception as e:
            logger.error(f"Error in reminder task for event {event.id}: {e}")
    
    async def _send_reminder(
        self,
        event: discord.ScheduledEvent,
        reminder_time: timedelta,
        get_participants_func: Callable[[discord.ScheduledEvent], Awaitable[Optional[List]]]
    ):
        """Send a reminder message to the configured channel."""
        try:
            # Get the reminder channel
            channel = event.guild.get_channel(self.reminder_channel_id)
            if not channel:
                logger.error(f"Reminder channel {self.reminder_channel_id} not found for event {event.id}")
                return
            
            # Check if event still exists and hasn't started
            if event.start_time and discord.utils.utcnow() >= event.start_time:
                logger.debug(f"Event {event.id} has already started, skipping reminder")
                return
            
            # Get current participants
            participants = await get_participants_func(event)
            if participants is None:
                # If fetch failed, use empty list
                participants = []
            
            # Format time until event
            time_until = self._format_time_until_event(event.start_time)
            
            # Format participant mentions
            participant_mentions = self._format_participants(participants)
            
            # Format reminder message
            message = (
                f"Reminder: **{event.name}** happening {time_until}. "
                f"Current participants: {participant_mentions}. "
                f"Sign up in the events tab!"
            )
            
            # Send the reminder
            await channel.send(message)
            logger.info(f"Sent reminder for event {event.id} ({event.name})")
            
        except discord.Forbidden:
            logger.error(f"Bot lacks permissions to send reminders in channel {self.reminder_channel_id}")
        except discord.HTTPException as e:
            logger.error(f"HTTP error sending reminder: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending reminder: {e}")
    
    def _format_time_until_event(self, start_time) -> str:
        """
        Format time until event in a human-readable way.
        
        Args:
            start_time: The event start time
            
        Returns:
            Formatted string like "in 2 hours" or "in 15 minutes"
        """
        now = discord.utils.utcnow()
        time_diff = start_time - now
        
        total_seconds = int(time_diff.total_seconds())
        
        if total_seconds < 60:
            return f"in {total_seconds} second{'s' if total_seconds != 1 else ''}"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            return f"in {minutes} minute{'s' if minutes != 1 else ''}"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            return f"in {hours} hour{'s' if hours != 1 else ''}"
        else:
            days = total_seconds // 86400
            return f"in {days} day{'s' if days != 1 else ''}"
    
    def _format_participants(self, participants: List) -> str:
        """
        Format participant list for reminder message.
        
        Args:
            participants: List of participant user objects
            
        Returns:
            Formatted string with participant mentions
        """
        if not participants:
            return "No participants yet"
        
        # Limit to 20 mentions to avoid message length issues
        participant_list = ", ".join([user.mention for user in participants[:20]])
        if len(participants) > 20:
            participant_list += f" and {len(participants) - 20} more"
        
        return participant_list
    
    def cancel_reminders(self, event_id: int):
        """Cancel all scheduled reminders for an event."""
        if event_id in self.scheduled_tasks:
            for task in self.scheduled_tasks[event_id]:
                task.cancel()
            del self.scheduled_tasks[event_id]
            logger.info(f"Cancelled all reminders for event {event_id}")

