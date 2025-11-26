"""Manages Google Calendar integration for Discord events."""
import os
import logging
from typing import Optional, Dict
from datetime import datetime
import discord
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class CalendarManager:
    """Handles Google Calendar event creation and management."""
    
    def __init__(self, credentials_path: Optional[str] = None, calendar_id: Optional[str] = None):
        """
        Initialize the CalendarManager.
        
        Args:
            credentials_path: Path to Google service account JSON credentials file
            calendar_id: Google Calendar ID to create events in (defaults to primary calendar)
        """
        self.credentials_path = credentials_path
        self.calendar_id = calendar_id or 'primary'
        self.service = None
        self.event_mappings: Dict[int, str] = {}  # discord_event_id -> google_calendar_event_id
        
        if credentials_path and os.path.exists(credentials_path):
            self._initialize_service()
        elif credentials_path:
            logger.warning(f"Google Calendar credentials file not found: {credentials_path}")
    
    def _initialize_service(self):
        """Initialize the Google Calendar API service."""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=['https://www.googleapis.com/auth/calendar']
            )
            self.service = build('calendar', 'v3', credentials=credentials)
            logger.info("Google Calendar service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Calendar service: {e}")
            self.service = None
    
    def _format_datetime_for_google(self, dt: datetime) -> str:
        """Format datetime for Google Calendar API (RFC3339 format)."""
        # Ensure timezone-aware datetime
        if dt.tzinfo is None:
            # If no timezone, assume UTC
            dt = dt.replace(tzinfo=discord.utils.UTC)
        
        # Format as RFC3339
        return dt.isoformat()
    
    def _get_calendar_link(self, event_id: str) -> str:
        """
        Generate a shareable calendar link for an event.
        
        Args:
            event_id: Google Calendar event ID
            
        Returns:
            Shareable link to add the event to calendar
        """
        # Google Calendar event link format
        return f"https://calendar.google.com/calendar/render?action=TEMPLATE&text=Event&dates=START/END&details=Event"
    
    async def create_calendar_event(
        self, 
        event: discord.ScheduledEvent
    ) -> Optional[str]:
        """
        Create a Google Calendar event from a Discord scheduled event.
        
        Args:
            event: The Discord scheduled event
            
        Returns:
            Shareable calendar link if successful, None otherwise
        """
        if not self.service:
            logger.warning("Google Calendar service not initialized, skipping calendar event creation")
            return None
        
        try:
            # Format event details
            summary = event.name
            description = event.description or f"Discord event: {event.name}"
            
            # Add Discord event link if available
            if hasattr(event, 'url'):
                description += f"\n\nDiscord Event: {event.url}"
            
            # Format times
            start_time = self._format_datetime_for_google(event.start_time)
            end_time = self._format_datetime_for_google(event.end_time) if event.end_time else start_time
            
            # Create calendar event
            calendar_event = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': start_time,
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_time,
                    'timeZone': 'UTC',
                },
                'visibility': 'public',
                'guestsCanModify': False,
                'guestsCanInviteOthers': False,
            }
            
            # Insert event into calendar
            created_event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=calendar_event
            ).execute()
            
            calendar_event_id = created_event.get('id')
            self.event_mappings[event.id] = calendar_event_id
            
            # Generate shareable link
            # Google Calendar HTML link format
            start_iso = event.start_time.strftime('%Y%m%dT%H%M%S')
            end_iso = (event.end_time or event.start_time).strftime('%Y%m%dT%H%M%S')
            
            # URL encode the event details
            import urllib.parse
            title_encoded = urllib.parse.quote(summary)
            details_encoded = urllib.parse.quote(description)
            
            calendar_link = (
                f"https://calendar.google.com/calendar/render?"
                f"action=TEMPLATE&"
                f"text={title_encoded}&"
                f"dates={start_iso}/{end_iso}&"
                f"details={details_encoded}"
            )
            
            logger.info(f"Created Google Calendar event for Discord event {event.id}: {calendar_event_id}")
            return calendar_link
            
        except HttpError as e:
            logger.error(f"Google Calendar API error creating event: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating calendar event: {e}")
            return None
    
    async def update_calendar_event(
        self, 
        event: discord.ScheduledEvent
    ) -> Optional[str]:
        """
        Update an existing Google Calendar event.
        
        Args:
            event: The updated Discord scheduled event
            
        Returns:
            Updated shareable calendar link if successful, None otherwise
        """
        if not self.service:
            return None
        
        calendar_event_id = self.event_mappings.get(event.id)
        if not calendar_event_id:
            # Event doesn't exist, create it
            return await self.create_calendar_event(event)
        
        try:
            # Get existing event
            existing_event = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=calendar_event_id
            ).execute()
            
            # Update event details
            existing_event['summary'] = event.name
            existing_event['description'] = event.description or f"Discord event: {event.name}"
            
            # Update times
            start_time = self._format_datetime_for_google(event.start_time)
            end_time = self._format_datetime_for_google(event.end_time) if event.end_time else start_time
            
            existing_event['start'] = {
                'dateTime': start_time,
                'timeZone': 'UTC',
            }
            existing_event['end'] = {
                'dateTime': end_time,
                'timeZone': 'UTC',
            }
            
            # Update event
            updated_event = self.service.events().update(
                calendarId=self.calendar_id,
                eventId=calendar_event_id,
                body=existing_event
            ).execute()
            
            # Generate updated shareable link
            start_iso = event.start_time.strftime('%Y%m%dT%H%M%S')
            end_iso = (event.end_time or event.start_time).strftime('%Y%m%dT%H%M%S')
            
            import urllib.parse
            title_encoded = urllib.parse.quote(event.name)
            details_encoded = urllib.parse.quote(existing_event['description'])
            
            calendar_link = (
                f"https://calendar.google.com/calendar/render?"
                f"action=TEMPLATE&"
                f"text={title_encoded}&"
                f"dates={start_iso}/{end_iso}&"
                f"details={details_encoded}"
            )
            
            logger.info(f"Updated Google Calendar event for Discord event {event.id}")
            return calendar_link
            
        except HttpError as e:
            if e.resp.status == 404:
                # Event was deleted, create new one
                del self.event_mappings[event.id]
                return await self.create_calendar_event(event)
            logger.error(f"Google Calendar API error updating event: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error updating calendar event: {e}")
            return None
    
    async def delete_calendar_event(self, event_id: int) -> bool:
        """
        Delete a Google Calendar event.
        
        Args:
            event_id: The Discord event ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self.service:
            return False
        
        calendar_event_id = self.event_mappings.get(event_id)
        if not calendar_event_id:
            logger.warning(f"No calendar event found for Discord event {event_id}")
            return False
        
        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=calendar_event_id
            ).execute()
            
            del self.event_mappings[event_id]
            logger.info(f"Deleted Google Calendar event for Discord event {event_id}")
            return True
            
        except HttpError as e:
            if e.resp.status == 404:
                # Event already deleted
                logger.info(f"Calendar event already deleted for Discord event {event_id}")
                if event_id in self.event_mappings:
                    del self.event_mappings[event_id]
                return True
            logger.error(f"Google Calendar API error deleting event: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting calendar event: {e}")
            return False
    
    def get_calendar_link(self, event_id: int) -> Optional[str]:
        """
        Get the calendar link for a Discord event (if it exists).
        
        Args:
            event_id: The Discord event ID
            
        Returns:
            Calendar link if event exists, None otherwise
        """
        # This is a simplified version - in practice, you'd store the link
        # For now, we'll regenerate it when needed
        return None

