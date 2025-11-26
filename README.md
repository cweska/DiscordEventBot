# Discord Event Bot

A Discord bot that automatically creates forum posts for scheduled events, updates participant lists, and archives posts after events complete.

## Features

- **Automatic Forum Post Creation**: Creates a forum post whenever a Discord scheduled event is created
- **Dynamic Participant Updates**: Automatically updates the forum post when users join or leave events
- **Smart Archiving**: Archives forum posts 24 hours after events complete (configurable)
- **Event Lifecycle Management**: Handles event creation, updates, deletion, and participant changes

## Setup

### Prerequisites

- Python 3.8 or higher
- A Discord bot token
- A Discord server with:
  - A forum channel (where posts will be created)
  - An archive category/channel (where archived posts will be moved)

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
   ARCHIVE_CATEGORY_ID=your_archive_category_id_here
   ARCHIVE_DELAY_HOURS=24
   
   # Optional: Google Calendar Integration
   GOOGLE_CALENDAR_CREDENTIALS_PATH=path/to/service-account-credentials.json
   GOOGLE_CALENDAR_ID=primary
   ```

4. Get your Discord bot token:
   - Go to https://discord.com/developers/applications
   - Create a new application or select an existing one
   - Go to the "Bot" section
   - Copy the token and add it to your `.env` file

5. Get channel IDs:
   - Enable Developer Mode in Discord (User Settings > Advanced > Developer Mode)
   - Right-click on your forum channel and select "Copy ID"
   - Right-click on your archive category/channel and select "Copy ID"
   - Add these IDs to your `.env` file

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
- `ARCHIVE_CATEGORY_ID`: The ID of the category/channel for archived posts (required)
- `ARCHIVE_DELAY_HOURS`: Hours to wait after event completion before archiving (default: 24)
- `GOOGLE_CALENDAR_CREDENTIALS_PATH`: Path to Google service account JSON credentials file (optional)
- `GOOGLE_CALENDAR_ID`: Google Calendar ID to create events in (optional, defaults to "primary")

### Google Calendar Setup (Optional)

To enable calendar invite functionality:

1. **Create a Google Cloud Project:**
   - Go to https://console.cloud.google.com/
   - Create a new project or select an existing one

2. **Enable Google Calendar API:**
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Calendar API"
   - Click "Enable"

3. **Create a Service Account:**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Give it a name (e.g., "discord-bot-calendar")
   - Click "Create and Continue"
   - Skip role assignment (or add "Editor" if needed)
   - Click "Done"

4. **Create and Download Service Account Key:**
   - Click on the service account you just created
   - Go to "Keys" tab
   - Click "Add Key" > "Create new key"
   - Choose "JSON" format
   - Download the JSON file
   - Save it in your project directory (e.g., `google-credentials.json`)

5. **Share Calendar with Service Account:**
   - Open Google Calendar
   - Go to Settings > Settings for my calendars
   - Select the calendar you want to use (or create a new one)
   - Under "Share with specific people", add the service account email (found in the JSON file as `client_email`)
   - Give it "Make changes to events" permission

6. **Add to `.env` file:**
   ```env
   GOOGLE_CALENDAR_CREDENTIALS_PATH=google-credentials.json
   GOOGLE_CALENDAR_ID=your-calendar-id@group.calendar.google.com
   ```
   (To find your calendar ID, go to Calendar Settings > Integrate calendar > Calendar ID)

## How It Works

1. **Event Creation**: When a scheduled event is created, the bot automatically creates a forum post with:
   - Event name as the post title
   - Event description
   - Start and end times
   - **Google Calendar link** (if configured) - clickable link to add event to calendar
   - Initial participant list
   - Encouragement message for interaction

2. **Participant Updates**: When users join or leave an event, the bot updates the forum post with the current participant list.

3. **Event Updates**: If event details change, the forum post is updated accordingly.

4. **Archiving**: 
   - If an event is deleted, the forum post is archived immediately
   - Otherwise, the forum post is archived 24 hours after the event ends (configurable)

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

### Forum posts aren't being archived
- Verify the `ARCHIVE_CATEGORY_ID` is correct
- Check that the bot has permission to manage threads
- Review logs for any errors during archiving

### Participant list not updating
- Ensure the bot has permission to view scheduled event subscribers
- Check that the bot has the `guild_scheduled_events` intent enabled

## License

This project is open source and available for use.