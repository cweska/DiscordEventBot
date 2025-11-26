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
    
    # Archive Category/Channel ID where archived posts go
    ARCHIVE_CATEGORY_ID = int(os.getenv("ARCHIVE_CATEGORY_ID", "0")) or None
    
    # Archive delay in hours (default: 24)
    ARCHIVE_DELAY_HOURS = int(os.getenv("ARCHIVE_DELAY_HOURS", "24"))
    
    # Google Calendar Configuration (optional)
    GOOGLE_CALENDAR_CREDENTIALS_PATH = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_PATH")
    GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")
    
    @classmethod
    def validate(cls):
        """Validate that all required configuration is present."""
        errors = []
        
        if not cls.DISCORD_BOT_TOKEN:
            errors.append("DISCORD_BOT_TOKEN is required")
        
        if not cls.FORUM_CHANNEL_ID:
            errors.append("FORUM_CHANNEL_ID is required")
        
        if not cls.ARCHIVE_CATEGORY_ID:
            errors.append("ARCHIVE_CATEGORY_ID is required")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        return True

