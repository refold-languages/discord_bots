# Refold Coaching Bot - Setup Instructions

## Quick Start

1. **Install dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

2. **Set up your OpenAI API key:**
   - Edit `openaiapi.txt` and replace the dummy key with your real OpenAI API key
   - Or set the `OPENAI_API_KEY` environment variable

3. **Configure Discord settings (optional):**
   ```bash
   export INTENSIVE_ROLE_ID="your_role_id"
   export COACH_ROLE_ID="your_coach_role_id" 
   export COACH_CHANNEL_ID="your_coach_channel_id"
   export BOT_CHAT_CHANNEL_ID="your_bot_chat_channel_id"
   export INTENSIVE_JOIN_CHANNEL_ID="your_join_channel_id"
   ```

4. **Start the bot:**
   ```bash
   ./start_bot.sh YOUR_DISCORD_BOT_TOKEN
   ```
   Or:
   ```bash
   python3 coaching_bot.py YOUR_DISCORD_BOT_TOKEN
   ```

## Features Implemented

✅ **Core Infrastructure**
- Project structure with 5 main Python files
- JSON data storage system
- Configuration management
- Error handling and logging

✅ **User Management**
- `!join_intensive` command for user onboarding
- DM conversation flow to collect goals and app username
- User profile storage with attendance tracking
- Role assignment (if configured)

✅ **ChatGPT Integration**
- GPT-5-mini for conversations
- GPT-5-nano for summaries and reports
- Bot chat channel with threading
- DM conversation support
- Conversation summarization

✅ **Attendance Tracking**
- Message counting per user per day
- Voice channel join tracking
- Activity feed parsing from channel 1280352810118025278
- App progress tracking via username matching

✅ **Coach Features**
- `!user_info @user` command for detailed user profiles
- `!all_users` command for summary statistics
- Daily automated reports to coach channel
- Activity insights and user status

✅ **Automated Features**
- Daily summary generation at 8 PM
- Automated reachouts to inactive users (every 6 hours)
- Conversation tracking and summarization
- Coach notifications for reachouts

## Data Storage

The bot stores all data in JSON files in the `data/` directory:
- `users.json` - User profiles with goals, attendance, conversations
- `conversations.json` - Chat conversation summaries  
- `activity_feed.json` - Parsed activity from app feed

## Testing

Run the test script to verify everything works:
```bash
python3 test_bot.py
```

## Next Steps

The bot is ready to run! Just add your real Discord bot token and OpenAI API key, then start it up. All the core features from your requirements are implemented and working.
