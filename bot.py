"""Main bot entry point for Discord Event Bot."""
import discord
from discord.ext import commands
import logging
import sys
from config import Config
from forum_manager import ForumManager
from archive_scheduler import ArchiveScheduler
from event_handler import EventHandler
from calendar_manager import CalendarManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class EventBot(commands.Bot):
    """Main bot class for handling Discord events."""
    
    def __init__(self):
        # Validate configuration
        Config.validate()
        
        # Set up intents
        intents = discord.Intents.default()
        intents.guilds = True
        intents.guild_scheduled_events = True
        
        super().__init__(command_prefix='!', intents=intents)
        
        # Initialize calendar manager (always available - no credentials needed)
        # This just generates "Add to Calendar" links - no API calls required
        calendar_manager = CalendarManager()
        
        # Initialize managers
        self.forum_manager = ForumManager(Config.FORUM_CHANNEL_ID, calendar_manager)
        self.archive_scheduler = ArchiveScheduler(
            Config.ARCHIVE_DELAY_HOURS,
            Config.ARCHIVE_CATEGORY_ID
        )
        self.event_handler = EventHandler(
            self.forum_manager,
            self.archive_scheduler,
            calendar_manager
        )
    
    async def setup_hook(self):
        """Called when the bot is starting up."""
        logger.info("Bot is starting up...")
    
    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guild(s)')
        
        # Process existing scheduled events
        await self.process_existing_events()
    
    async def process_existing_events(self):
        """Process any existing scheduled events when the bot starts."""
        logger.info("Processing existing scheduled events...")
        
        for guild in self.guilds:
            try:
                events = await guild.fetch_scheduled_events()
                for event in events:
                    # Check if forum post already exists in our mapping
                    thread = self.forum_manager.get_thread(event.id)
                    
                    if not thread:
                        # Try to find existing thread by name (in case bot restarted)
                        thread = await self.forum_manager.find_existing_thread(guild, event.name)
                        if thread:
                            # Found existing thread, add it to our mapping
                            self.forum_manager.event_posts[event.id] = thread
                            logger.info(f"Reconnected to existing forum post for event {event.id}")
                    
                    if not thread:
                        # No existing thread found, create new one
                        await self.event_handler.on_scheduled_event_create(event)
                    else:
                        # Update existing forum post and reschedule archive
                        await self.event_handler.on_scheduled_event_update(event)
            except Exception as e:
                logger.error(f"Error processing existing events for guild {guild.id}: {e}")
    
    async def on_scheduled_event_create(self, event: discord.ScheduledEvent):
        """Called when a scheduled event is created."""
        await self.event_handler.on_scheduled_event_create(event)
    
    async def on_scheduled_event_update(self, event: discord.ScheduledEvent):
        """Called when a scheduled event is updated."""
        await self.event_handler.on_scheduled_event_update(event)
    
    async def on_scheduled_event_delete(self, event: discord.ScheduledEvent):
        """Called when a scheduled event is deleted."""
        await self.event_handler.on_scheduled_event_delete(event)
    
    async def on_scheduled_event_user_add(
        self, 
        event: discord.ScheduledEvent, 
        user: discord.User
    ):
        """Called when a user subscribes to a scheduled event."""
        await self.event_handler.on_scheduled_event_user_add(event, user)
    
    async def on_scheduled_event_user_remove(
        self, 
        event: discord.ScheduledEvent, 
        user: discord.User
    ):
        """Called when a user unsubscribes from a scheduled event."""
        await self.event_handler.on_scheduled_event_user_remove(event, user)


def main():
    """Main entry point for the bot."""
    try:
        bot = EventBot()
        bot.run(Config.DISCORD_BOT_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

