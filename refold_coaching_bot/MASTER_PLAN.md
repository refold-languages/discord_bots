# Refold Coaching Bot - Master Development Plan

## Project Overview

A Discord bot for managing intensive language learning programs with ChatGPT integration, attendance tracking, and automated coaching features. Built as a temporary solution before migrating to a web application.

## Current Status: FUNCTIONAL with Known Issues

The bot is operational and can handle the core intensive management workflow, but has several bugs and missing features that need attention.

---

## ✅ WORKING FEATURES

### 1. **User Onboarding System** ✅
- **Thread-based onboarding**: Users send any message in `INTENSIVE_JOIN_CHANNEL_ID` to start
- **SMART goals validation**: Uses GPT-5-mini to validate and provide feedback on goals
- **App username collection**: Asks if user has Refold app, collects username, verifies against activity feed
- **Role granting**: Assigns intensive role after successful onboarding
- **Coach notifications**: Sends notification to coach channel when user completes registration
- **Completion message**: Provides instructions for next steps with channel references

### 2. **ChatGPT Integration** ✅
- **GPT-5 models**: Uses `gpt-5-mini-2025-08-07` for conversations, `gpt-5-nano-2025-08-07` for summaries
- **Correct API format**: Uses `client.responses.create()` and `response.output_text`
- **Message splitting**: Handles Discord's 2000 character limit automatically
- **AI disclaimers**: Appends disclaimer to all AI-generated responses
- **Prompt system**: Dynamic prompt loading from `prompts/` directory with model specification

### 3. **Coach Commands** ✅
- **`&coach_help`**: Lists all available coach commands
- **`&user_info @username`**: Get detailed user information
- **`&all_users`**: Summary of all users in intensive
- **`&remove @username`**: Remove user from intensive program
- **`&trigger_reachout @username`**: Manually trigger reachout to user
- **`&report @username`**: Comprehensive user report with goals, attendance, activity
- **`&userlist`**: List all users with Discord and app usernames
- **Channel restrictions**: All coach commands only work in `COACH_CHANNEL_ID`

### 4. **User Commands** ✅
- **`&update_goals`**: Update intensive goals (command exists, needs verification)

### 5. **Data Management** ✅
- **JSON storage**: Users, conversations, activity feed data stored in `data/` directory
- **User profiles**: Goals, attendance, conversation summaries, reachout tracking
- **Conversation summaries**: Periodic summarization of user conversations
- **Activity tracking**: Message counts, voice channel joins, app progress

### 6. **Activity Feed Integration** ✅
- **Activity parsing**: Extracts username, activity, duration from activity feed channel
- **Username verification**: Searches last 2000 messages for username matches
- **Progress tracking**: Tracks total minutes and activities per user

---

## ❌ KNOWN BUGS & ISSUES

### 1. **Critical Bugs**

#### **Thread Attendance Not Tracked** 🚨
- **Issue**: Messages in onboarding threads are not counted for attendance
- **Impact**: Users appear inactive even if they're participating in threads
- **Fix Needed**: Add `attendance_tracker.track_message(user_id, thread_id)` to `_handle_thread_message`

#### **Typing Indicator Disappears Too Early** 🚨
- **Issue**: Typing indicator stops before full response is sent
- **Impact**: Poor user experience during AI processing
- **Fix Needed**: Wrap entire GPT call + message sending in `async with channel.typing()`

#### **Goal Updates May Not Work** 🚨
- **Issue**: `&update_goals` command sets conversation state but DM handler may not process it
- **Impact**: Users can't update their goals
- **Fix Needed**: Verify `updating_goals` state is handled in `_handle_dm_message`

### 2. **Missing Features**

#### **Conversation Summaries Not Saved** ⚠️
- **Issue**: Code exists but summaries may not be properly saved to user profiles
- **Impact**: Coaches can't see conversation history
- **Fix Needed**: Verify `add_conversation_summary` is working correctly

#### **Daily Summaries Not Running** ⚠️
- **Issue**: Scheduled task for daily coach reports may not be running
- **Impact**: Coaches don't get automated activity summaries
- **Fix Needed**: Verify scheduled tasks are properly initialized and running

#### **Automated Reachouts Not Working** ⚠️
- **Issue**: Scheduled reachout task may not be running
- **Impact**: Inactive users don't get automated check-ins
- **Fix Needed**: Verify scheduled tasks are working

### 3. **Minor Issues**

#### **Role Granting May Not Work** ⚠️
- **Issue**: Role assignment might fail due to permissions or configuration
- **Impact**: Users don't get intensive role after onboarding
- **Fix Needed**: Check `INTENSIVE_ROLE_ID` configuration and bot permissions

#### **Attendance Tracking Gaps** ⚠️
- **Issue**: Only tracks messages in `BOT_CHAT_CHANNEL_ID`, not all channels
- **Impact**: Incomplete attendance data
- **Fix Needed**: Track messages in all relevant channels

---

## 🔧 IMMEDIATE FIXES NEEDED

### Priority 1: Critical Bugs
1. **Fix thread attendance tracking**
2. **Fix typing indicator persistence**
3. **Verify goal update functionality**

### Priority 2: Missing Features
1. **Verify conversation summaries are saved**
2. **Check scheduled tasks are running**
3. **Test automated reachouts**

### Priority 3: Configuration Issues
1. **Verify role granting works**
2. **Check all environment variables are set**
3. **Test all coach commands**

---

## 📋 FEATURE STATUS BREAKDOWN

### **Joining the Intensive** - 90% Complete
- ✅ Opening conversation about goals
- ✅ SMART goals validation with GPT
- ✅ App username collection and verification
- ✅ Role granting (needs verification)
- ✅ Save info to JSON file
- ✅ Coach command to get user info
- ⚠️ Completion message needs channel ID verification

### **Attendance Tracking** - 70% Complete
- ✅ Number of messages (bot chat channel)
- ✅ Messages per day calculation
- ✅ Voice room joins tracking
- ❌ Thread message tracking (BUG)
- ❌ All channel message tracking (missing)

### **Bot Chat Channel** - 60% Complete
- ✅ Open conversation with Coach Bot
- ❌ Update/tweak goals (needs verification)
- ❌ Save conversation summaries (needs verification)
- ✅ DM chatting with coach visibility reminder
- ⚠️ Prompt quality needs improvement

### **Automated Reachouts** - 50% Complete
- ✅ Low attendance detection
- ❌ Automated DM sending (needs verification)
- ❌ Daily activity summaries to coaches (needs verification)
- ✅ Coach notifications for reachouts

### **Coach Information** - 100% Complete
- ✅ User reports with comprehensive data
- ✅ User list with Discord and app usernames
- ✅ All coach commands working
- ✅ Channel restrictions enforced

### **Activity Feed Integration** - 90% Complete
- ✅ Track user app progress from activity feed
- ✅ Include in user reports
- ✅ Username verification against activity feed
- ⚠️ Bot chat integration needs verification

---

## 🚀 NEXT DEVELOPMENT PRIORITIES

### Phase 1: Bug Fixes (Immediate)
1. Fix thread attendance tracking
2. Fix typing indicator persistence
3. Verify goal update functionality
4. Test all scheduled tasks

### Phase 2: Feature Completion (Short-term)
1. Verify conversation summaries are working
2. Test automated reachouts end-to-end
3. Improve AI prompt quality
4. Add comprehensive error handling

### Phase 3: Enhancements (Medium-term)
1. Add more detailed attendance analytics
2. Improve coach dashboard with visualizations
3. Add user progress tracking over time
4. Implement goal achievement tracking

### Phase 4: Migration Preparation (Long-term)
1. Design web app API structure
2. Create data export functionality
3. Plan user migration process
4. Document all features for web app implementation

---

## 🛠️ TECHNICAL ARCHITECTURE

### **Core Files**
- `coaching_bot.py` - Main bot with Discord events and commands
- `config.py` - Configuration and environment variable management
- `data_manager.py` - JSON data storage and retrieval
- `gpt_handler.py` - OpenAI API integration with GPT-5 models
- `attendance_tracker.py` - Activity tracking and parsing

### **Data Storage**
- `data/users.json` - User profiles, goals, attendance, conversations
- `data/conversations.json` - Chat conversation summaries
- `data/activity_feed.json` - Parsed activity from app feed

### **Prompt System**
- `prompts/` directory with model-specific prompts
- Dynamic model loading based on prompt headers
- GPT-5-mini for conversations, GPT-5-nano for summaries

### **Scheduled Tasks**
- Daily summaries for coaches (8 PM Pacific)
- Automated reachouts for inactive users
- Activity feed parsing and user progress tracking

---

## 🔍 TESTING CHECKLIST

### **Onboarding Flow**
- [ ] Message in join channel triggers thread creation
- [ ] Goals validation works with GPT feedback
- [ ] App username collection and verification
- [ ] Role is granted after completion
- [ ] Coach notification is sent
- [ ] Completion message shows correct channels

### **Coach Commands**
- [ ] All commands work in coach channel only
- [ ] User reports show comprehensive data
- [ ] Goal updates work for users
- [ ] User removal works correctly

### **Attendance Tracking**
- [ ] Messages in bot chat are tracked
- [ ] Messages in threads are tracked
- [ ] Voice channel joins are tracked
- [ ] Activity feed parsing works

### **Automated Features**
- [ ] Daily summaries are sent to coaches
- [ ] Reachouts are sent to inactive users
- [ ] Conversation summaries are saved
- [ ] Scheduled tasks are running

---

## 📝 ENVIRONMENT VARIABLES

### **Required**
- `DISCORD_BOT_TOKEN` - Discord bot token
- `OPENAI_API_KEY` - OpenAI API key

### **Optional (with defaults)**
- `INTENSIVE_ROLE_ID` - Role for intensive participants
- `COACH_ROLE_ID` - Role for coaches
- `COACH_CHANNEL_ID` - Channel for coach commands
- `BOT_CHAT_CHANNEL_ID` - Channel for bot conversations
- `INTENSIVE_JOIN_CHANNEL_ID` - Channel for onboarding
- `INTENSIVE_CHAT_ROOM_ID` - Channel for participant chat
- `DAILY_SUMMARY_HOUR` - Hour for daily summaries (default: 20)
- `TIMEZONE` - Timezone (default: America/Los_Angeles)
- `REACHOUT_THRESHOLD_DAYS` - Days before reachout (default: 3)
- `REACHOUT_THRESHOLD_MESSAGES` - Message threshold (default: 5)

---

## 🎯 SUCCESS METRICS

### **Functional Requirements**
- ✅ Users can join intensive program
- ✅ Coaches can manage users
- ✅ Attendance is tracked
- ✅ AI conversations work
- ⚠️ Automated features need verification

### **Performance Requirements**
- ✅ Bot responds quickly to commands
- ✅ AI responses are concise and helpful
- ✅ Data is persisted correctly
- ⚠️ Scheduled tasks need verification

### **User Experience**
- ✅ Clear onboarding flow
- ✅ Helpful coach commands
- ✅ Good error handling
- ❌ Typing indicators need fixing

---

## 📚 DOCUMENTATION STATUS

- ✅ README.md - Setup and usage instructions
- ✅ MASTER_PLAN.md - This comprehensive status document
- ✅ Code comments - Extensive inline documentation
- ✅ Prompt files - Well-documented AI prompts
- ⚠️ API documentation - Not needed for Discord bot

---

## 🔄 MIGRATION TO WEB APP

### **Data Export Ready**
- All user data stored in JSON format
- Conversation summaries available
- Attendance data structured
- Activity feed integration working

### **Feature Mapping**
- User onboarding → User registration flow
- Coach commands → Admin dashboard
- Attendance tracking → Analytics dashboard
- AI conversations → Chat interface
- Automated reachouts → Notification system

### **Next Steps for Web App**
1. Design REST API endpoints
2. Create user authentication system
3. Build admin dashboard
4. Implement real-time chat
5. Add advanced analytics

---

*Last Updated: January 2025*
*Status: Functional with known issues requiring immediate attention*
