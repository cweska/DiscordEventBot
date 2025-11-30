# Discord Event Bot

A Discord bot that automatically creates forum posts for scheduled events, updates participant lists, and closes posts after events complete.

## Features

- **Automatic Forum Post Creation**: Creates a forum post whenever a Discord scheduled event is created
- **Dynamic Participant Updates**: Automatically updates the forum post when users join or leave events
- **Automatic Post Closure**: Closes forum posts 24 hours after events complete (configurable), moving them to "Older Posts"
- **Event Reminders**: Sends reminder messages at configurable times before events start (optional)
- **Event Lifecycle Management**: Handles event creation, updates, deletion, and participant changes

## Setup

### Prerequisites

- Python 3.8 or higher
- A Discord bot token
- A Discord server with:
  - A forum channel (where posts will be created)

### Installation

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd DiscordEventBot
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root:
   ```env
   DISCORD_BOT_TOKEN=your_bot_token_here
   FORUM_CHANNEL_ID=your_forum_channel_id_here
   ARCHIVE_DELAY_HOURS=24
   REMINDER_CHANNEL_ID=your_reminder_channel_id_here
   REMINDER_TIMES=10m,12h,24h
   ```
   
   **Note:** Google Calendar links are automatically generated - no additional setup needed!

4. Get your Discord bot token:
   - Go to https://discord.com/developers/applications
   - Create a new application or select an existing one
   - Go to the "Bot" section
   - Copy the token and add it to your `.env` file

5. Get channel ID:
   - Enable Developer Mode in Discord (User Settings > Advanced > Developer Mode)
   - Right-click on your forum channel and select "Copy ID"
   - Add this ID to your `.env` file

6. Invite the bot to your server:
   - In the Discord Developer Portal, go to OAuth2 > URL Generator
   - Select the `bot` scope
   - Select the following bot permissions:
     - View Channels
     - Send Messages
     - Manage Messages
     - Manage Threads
     - Read Message History
   - Copy the generated URL and open it in your browser to invite the bot

### Running the Bot

```bash
python bot.py
```

The bot will:
- Connect to Discord
- Process any existing scheduled events
- Start monitoring for new events and updates

## Configuration

All configuration is done through environment variables in the `.env` file:

- `DISCORD_BOT_TOKEN`: Your Discord bot token (required)
- `FORUM_CHANNEL_ID`: The ID of the forum channel where posts are created (required)
- `ARCHIVE_DELAY_HOURS`: Hours to wait after event completion before closing the post (default: 24)
- `REMINDER_CHANNEL_ID`: The ID of the channel where reminders are sent (optional)
- `REMINDER_TIMES`: Comma-separated list of times before event start to send reminders (optional)
  - Format: Use "m" for minutes, "h" for hours, "d" for days
  - Example: `REMINDER_TIMES=10m,12h,24h` sends reminders 10 minutes, 12 hours, and 24 hours before event start
  - Example: `REMINDER_TIMES=1h,1d` sends reminders 1 hour and 1 day before event start

### Google Calendar Links

The bot automatically generates "Add to Calendar" links for all events. **No setup required!** 

When users click the calendar link in a forum post, it opens Google Calendar with the event details pre-filled. Each user adds the event to their own personal calendar - they cannot see other participants. This is perfect for privacy and ensures everyone has their own calendar entry.

### Event Reminders

The bot can send reminder messages before events start. To enable reminders:

1. Set `REMINDER_CHANNEL_ID` to the channel where you want reminders sent
2. Set `REMINDER_TIMES` to a comma-separated list of times before the event start

**Example Configuration:**
```env
REMINDER_CHANNEL_ID=123456789012345678
REMINDER_TIMES=10m,12h,24h
```

This will send reminders:
- 24 hours before the event starts
- 12 hours before the event starts  
- 10 minutes before the event starts

**Reminder Format:**
Reminders include:
- Event name
- Time until event (e.g., "in 2 hours", "in 15 minutes")
- Current participant list (mentions)
- Call to action to sign up

**Example Reminder Message:**
```
Reminder: Kitchen Sync Event happening in 2 hours. Current participants: @user1, @user2, @user3. Sign up in the events tab!
```

**Time Format Options:**
- `10m` = 10 minutes before
- `1h` = 1 hour before
- `12h` = 12 hours before
- `1d` = 1 day before
- `2d` = 2 days before

You can combine multiple times: `REMINDER_TIMES=10m,1h,12h,24h,1d`

**Note:** Reminders are optional. If `REMINDER_CHANNEL_ID` is not set, reminders are disabled. If `REMINDER_CHANNEL_ID` is set but `REMINDER_TIMES` is empty or invalid, reminders will be disabled and a warning will be logged.

## How It Works

1. **Event Creation**: When a scheduled event is created, the bot automatically creates a forum post with:
   - Event name as the post title
   - Event description
   - Start and end times
   - **Google Calendar link** - clickable link that opens Google Calendar with event details pre-filled (each user adds it to their own personal calendar)
   - Initial participant list
   - Encouragement message for interaction

2. **Participant Updates**: When users join or leave an event, the bot updates the forum post with the current participant list.

3. **Event Updates**: If event details change, the forum post is updated accordingly.

4. **Post Closure**: 
   - If an event is deleted, the forum post is closed immediately
   - Otherwise, the forum post is closed 24 hours after the event ends (configurable)
   - Closed posts automatically move to the "Older Posts" section in Discord

5. **Reminders**: If configured, the bot sends reminder messages to a specified channel at configured times before events start (e.g., 24 hours, 12 hours, 10 minutes before). Reminders include the event name, time until event, and current participants.

## Project Structure

```
DiscordEventBot/
├── bot.py                 # Main bot entry point
├── config.py              # Configuration management
├── event_handler.py       # Scheduled event listeners
├── forum_manager.py       # Forum post creation/updates
├── archive_scheduler.py   # Archive timing logic
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (not in git)
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## Logging

The bot logs all operations to both `bot.log` and the console. Logs include:
- Event creation, updates, and deletions
- Forum post creation and updates
- Participant changes
- Archive operations
- Errors and warnings

## Troubleshooting

### Bot doesn't create forum posts
- Check that the bot has the required permissions in the forum channel
- Verify the `FORUM_CHANNEL_ID` is correct
- Check the bot logs for error messages

### Forum posts aren't being closed
- Check that the bot has permission to manage threads
- Review logs for any errors during post closure

### Participant list not updating
- Ensure the bot has permission to view scheduled event subscribers
- Check that the bot has the `guild_scheduled_events` intent enabled

## License

This project is open source and available for use.