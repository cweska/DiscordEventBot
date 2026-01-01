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
from reminder_scheduler import ReminderScheduler
from meal_cog import MealCog, HumorLoader, StatsManager
from food_fight_manager import FoodFightManager
from food_fight_cog import FoodFightCog
from pathlib import Path

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
        intents.message_content = True
        intents.reactions = True
        
        super().__init__(command_prefix='!', intents=intents)
        
        # Initialize calendar manager (always available - no credentials needed)
        # This just generates "Add to Calendar" links - no API calls required
        calendar_manager = CalendarManager()
        
        # Initialize managers
        self.forum_manager = ForumManager(Config.FORUM_CHANNEL_ID, calendar_manager)
        self.archive_scheduler = ArchiveScheduler(
            Config.ARCHIVE_DELAY_HOURS
        )
        
        # Initialize reminder scheduler if configured
        reminder_scheduler = None
        if Config.REMINDER_CHANNEL_ID:
            reminder_times = Config.parse_reminder_times()
            if reminder_times:
                reminder_scheduler = ReminderScheduler(Config.REMINDER_CHANNEL_ID, reminder_times)
                logger.info(f"Reminder system enabled: {len(reminder_times)} reminder time(s) configured")
            else:
                logger.warning("REMINDER_CHANNEL_ID is set but REMINDER_TIMES is empty or invalid. Reminders disabled.")
        
        self.event_handler = EventHandler(
            self.forum_manager,
            self.archive_scheduler,
            calendar_manager,
            reminder_scheduler
        )

        # Meal logging components (JSON persistence)
        self.meal_channel_id = 1440141058410283039
        self.humor_loader = HumorLoader(Path("data/humor.txt"))
        self.stats_manager = StatsManager(Path("data/stats.json"))
        
        # Food fight manager (JSON persistence)
        self.food_fight_manager = FoodFightManager(Path("data/food_fights.json"))
    
    async def setup_hook(self):
        """Called when the bot is starting up."""
        logger.info("Bot is starting up...")
        await self.stats_manager.load()
        await self.food_fight_manager.load()
        await self.add_cog(
            MealCog(
                self,
                humor_loader=self.humor_loader,
                stats_manager=self.stats_manager,
                meal_channel_id=self.meal_channel_id,
                food_fight_manager=self.food_fight_manager,
            )
        )
        await self.add_cog(
            FoodFightCog(
                self,
                food_fight_manager=self.food_fight_manager,
            )
        )
        # Sync application commands so slash commands like /cooked appear
        # Log commands in tree before syncing
        commands_in_tree = list(self.tree.walk_commands())
        logger.info(f"Commands in tree before sync: {len(commands_in_tree)}")
        for cmd in commands_in_tree:
            logger.info(f"  - {cmd.name}")
        
        if Config.COMMAND_GUILD_ID:
            guild = discord.Object(id=Config.COMMAND_GUILD_ID)
            synced = await self.tree.sync(guild=guild)
            logger.info(f"Synced {len(synced)} commands to guild {Config.COMMAND_GUILD_ID}")
        else:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} commands globally (may take up to an hour to propagate)")
    
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
                        # For existing events on startup, use the same event for both before and after
                        await self.event_handler.on_scheduled_event_update(event, event)
            except Exception as e:
                logger.error(f"Error processing existing events for guild {guild.id}: {e}")
    
    async def on_scheduled_event_create(self, event: discord.ScheduledEvent):
        """Called when a scheduled event is created."""
        await self.event_handler.on_scheduled_event_create(event)
    
    async def on_scheduled_event_update(self, before: discord.ScheduledEvent, after: discord.ScheduledEvent):
        """Called when a scheduled event is updated."""
        # Discord passes both 'before' and 'after' states, pass both to handler
        await self.event_handler.on_scheduled_event_update(before, after)
    
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

