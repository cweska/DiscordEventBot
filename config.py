"""Configuration management for the Discord Event Bot."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Bot configuration loaded from environment variables."""
    
    # Discord Bot Token
    DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    
    # Forum Channel ID where posts are created
    FORUM_CHANNEL_ID = int(os.getenv("FORUM_CHANNEL_ID", "0")) or None
    
    # Archive Category/Channel ID (deprecated - no longer used, kept for backward compatibility)
    ARCHIVE_CATEGORY_ID = int(os.getenv("ARCHIVE_CATEGORY_ID", "0")) or None
    
    # Archive delay in hours (default: 24)
    ARCHIVE_DELAY_HOURS = int(os.getenv("ARCHIVE_DELAY_HOURS", "24"))
    
    # Reminder Channel ID (optional - reminders disabled if not set)
    REMINDER_CHANNEL_ID = int(os.getenv("REMINDER_CHANNEL_ID", "0")) or None
    
    # Reminder times before event start (comma-separated, e.g., "10m,12h,24h")
    # Supported formats: "m" for minutes, "h" for hours, "d" for days
    REMINDER_TIMES = os.getenv("REMINDER_TIMES", "").strip()

    # Optional guild ID for command sync (fast propagation for testing)
    COMMAND_GUILD_ID = int(os.getenv("COMMAND_GUILD_ID", "0")) or None
    
    @classmethod
    def parse_reminder_times(cls):
        """
        Parse REMINDER_TIMES string into list of timedelta objects.
        
        Returns:
            List of timedelta objects representing when to send reminders before event start
        """
        from datetime import timedelta
        import re
        
        if not cls.REMINDER_TIMES:
            return []
        
        reminders = []
        for time_str in cls.REMINDER_TIMES.split(','):
            time_str = time_str.strip()
            if not time_str:
                continue
            
            # Parse format like "10m", "12h", "24h", "1d"
            # Match number followed by unit (m, h, or d)
            match = re.match(r'^(\d+)([mhd])$', time_str, re.IGNORECASE)
            if not match:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Invalid reminder time format: '{time_str}'. Skipping. Use format like '10m', '12h', or '1d'")
                continue
            
            value = int(match.group(1))
            unit = match.group(2).lower()
            
            if unit == 'm':
                reminders.append(timedelta(minutes=value))
            elif unit == 'h':
                reminders.append(timedelta(hours=value))
            elif unit == 'd':
                reminders.append(timedelta(days=value))
        
        # Sort in descending order (longest time first) for easier processing
        reminders.sort(reverse=True)
        return reminders
    
    @classmethod
    def validate(cls):
        """Validate that all required configuration is present."""
        errors = []
        
        if not cls.DISCORD_BOT_TOKEN:
            errors.append("DISCORD_BOT_TOKEN is required")
        
        if not cls.FORUM_CHANNEL_ID:
            errors.append("FORUM_CHANNEL_ID is required")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        return True

