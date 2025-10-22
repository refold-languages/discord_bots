# Refold Coaching Bot

A Discord bot for managing intensive language learning programs with ChatGPT integration, attendance tracking, and automated coaching features.

## Features

- **User Onboarding**: Thread-based onboarding with SMART goals validation
- **ChatGPT Integration**: AI-powered conversations with concise, helpful responses
- **Attendance Tracking**: Monitors messages, voice activity, and app progress
- **Coach Tools**: Commands for coaches to view user info and activity summaries
- **Automated Reachouts**: Sends DMs to inactive users with personalized messages
- **Daily Reports**: Automated summaries for coaches with activity insights
- **Message Splitting**: Automatically handles Discord's 2000 character limit
- **Typing Indicators**: Persistent visual feedback during AI processing

## Commands

### User Commands
- `&update_goals` - Update your intensive goals

### Coach Commands (Requires Coach Role & Coach Channel)
- `&coach_help` - List all available coach commands
- `&user_info @username` - Get detailed information about a user
- `&all_users` - Get summary of all users in the intensive
- `&remove @username` - Remove a user from the intensive program
- `&trigger_reachout @username` - Manually trigger a reachout to a user (for testing)
- `&report @username` - Get comprehensive user report with goals, attendance, and activity
- `&userlist` - List all users in the intensive with Discord and app usernames

**Note**: All coach commands must be used in the coach channel (`COACH_CHANNEL_ID`)

**Note**: The bot uses `&` as the command prefix (not `!`)

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configuration

Create an `openaiapi.txt` file with your OpenAI API key, or set the `OPENAI_API_KEY` environment variable.

### 3. Environment Variables (Optional)

```bash
export BOT_TOKEN="your_discord_bot_token"
export INTENSIVE_ROLE_ID="role_id_for_intensive_participants"
export COACH_ROLE_ID="role_id_for_coaches"
export COACH_CHANNEL_ID="channel_id_for_coach_reports"
export BOT_CHAT_CHANNEL_ID="channel_id_for_bot_conversations"
export INTENSIVE_JOIN_CHANNEL_ID="channel_id_for_initial_plans"
export INTENSIVE_CHAT_ROOM_ID="channel_id_for_participant_chat"
export DAILY_SUMMARY_HOUR="20"  # 8 PM Pacific Time
export TIMEZONE="America/Los_Angeles"  # Pacific Time
export REACHOUT_THRESHOLD_DAYS="3"
export REACHOUT_THRESHOLD_MESSAGES="5"
```

### 4. Run the Bot

```bash
python coaching_bot.py YOUR_BOT_TOKEN
```

Or with environment variable:
```bash
export BOT_TOKEN="your_token"
python coaching_bot.py
```

## Usage

### For Users

- `!join_intensive` - Register for the intensive program
- `!update_goals` - Update your learning goals
- Chat with the bot in the designated bot chat channel or via DMs

### For Coaches

- `!user_info @user` - View detailed user information
- `!all_users` - Get summary of all participants
- Receive daily reports in the coach channel
- Get notifications when users are reached out to

## Data Storage

The bot stores data in JSON files in the `data/` directory:

- `users.json` - User profiles with goals, attendance, and conversation history
- `conversations.json` - Chat conversation summaries
- `activity_feed.json` - Parsed activity from the app feed

## Architecture

- `coaching_bot.py` - Main bot with commands and event handlers
- `config.py` - Configuration management
- `data_manager.py` - JSON data storage and retrieval
- `gpt_handler.py` - OpenAI API integration
- `attendance_tracker.py` - Activity tracking and parsing

## Notes

- The bot tracks activity from channel ID `1280352810118025278` for app progress
- Uses GPT-5-mini for conversations and GPT-5-nano for summaries
- Automated tasks run every 6 hours for reachouts and daily for reports
- All conversation data is stored locally in JSON format
