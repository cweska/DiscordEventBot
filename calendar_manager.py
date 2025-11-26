"""Manages Google Calendar link generation for Discord events."""
import logging
from typing import Optional
from datetime import datetime, timezone
import discord
import urllib.parse

logger = logging.getLogger(__name__)


class CalendarManager:
    """Generates Google Calendar "Add to Calendar" links for Discord events."""
    
    def __init__(self):
        """
        Initialize the CalendarManager.
        
        No credentials needed - this just generates template URLs that users
        can use to add events to their own personal calendars.
        """
        pass
    
    def generate_calendar_link(self, event: discord.ScheduledEvent) -> str:
        """
        Generate a Google Calendar "Add to Calendar" link for a Discord event.
        
        This link opens Google Calendar with event details pre-filled, allowing
        each user to add it to their own personal calendar. Each user gets their
        own private calendar entry - they cannot see other participants.
        
        Args:
            event: The Discord scheduled event
            
        Returns:
            Google Calendar template URL
        """
        try:
            # Format event details
            summary = event.name
            description = event.description or f"Discord event: {event.name}"
            
            # Format times in Google Calendar format (YYYYMMDDTHHMMSSZ for UTC)
            # Discord events are timezone-aware, convert to UTC if needed
            start_dt = event.start_time
            if start_dt.tzinfo is None:
                # If no timezone info, assume UTC
                start_dt = start_dt.replace(tzinfo=timezone.utc)
            else:
                # Convert to UTC if not already
                start_dt = start_dt.astimezone(timezone.utc)
            
            end_dt = event.end_time if event.end_time else start_dt
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)
            else:
                end_dt = end_dt.astimezone(timezone.utc)
            
            # Format as YYYYMMDDTHHMMSSZ (Google Calendar format with Z suffix for UTC)
            # The 'Z' suffix tells Google Calendar this is UTC time
            start_iso = start_dt.strftime('%Y%m%dT%H%M%SZ')
            end_iso = end_dt.strftime('%Y%m%dT%H%M%SZ')
            
            # URL encode the event details
            title_encoded = urllib.parse.quote(summary)
            details_encoded = urllib.parse.quote(description)
            
            # Generate Google Calendar template URL
            # This opens Google Calendar with the event pre-filled for the user to add
            calendar_link = (
                f"https://calendar.google.com/calendar/render?"
                f"action=TEMPLATE&"
                f"text={title_encoded}&"
                f"dates={start_iso}/{end_iso}&"
                f"details={details_encoded}"
            )
            
            logger.info(f"Generated Google Calendar link for Discord event {event.id}")
            return calendar_link
            
        except Exception as e:
            logger.error(f"Error generating calendar link: {e}")
            return ""
    
    def generate_calendar_link_for_update(self, event: discord.ScheduledEvent) -> str:
        """
        Generate an updated Google Calendar link when event details change.
        
        Args:
            event: The updated Discord scheduled event
            
        Returns:
            Updated Google Calendar template URL
        """
        # Same as generate_calendar_link - just regenerates with new details
        return self.generate_calendar_link(event)

