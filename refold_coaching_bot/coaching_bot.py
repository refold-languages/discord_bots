"""
Refold Coaching Bot - Main entry point.
A Discord bot for managing intensive language learning programs.

ONBOARDING FLOW (FIXED 2025):
1. User sends message in INTENSIVE_JOIN_CHANNEL_ID
2. Bot creates thread and asks for goals
3. Goals validated → User profile created and saved to users.json
4. Brief encouragement → "Now let's get you set up in the app!"
5. App usage question with ✅/❌ reactions
6. Username collection and verification against activity feed
7. Role granted and registration complete

IMPORTANT: Thread messages are routed based on ongoing_conversations state, not user data.
"""

import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List

from config import config
from data_manager import data_manager
from gpt_handler import gpt_handler
from attendance_tracker import attendance_tracker


class RefoldCoachingBot(commands.Bot):
    """Main bot class for the Refold Coaching Bot."""
    
    def __init__(self):
        intents = discord.Intents.all()
        intents.members = True
        
        super().__init__(
            intents=intents,
            command_prefix=config.COMMAND_PREFIX
        )
        
        # Track ongoing conversations
        self.ongoing_conversations = {}  # user_id -> conversation_state
    
    async def setup_hook(self):
        """Setup tasks when bot starts."""
        # Start scheduled tasks
        if not self.daily_summary.is_running():
            self.daily_summary.start()
        
        if not self.reachout_check.is_running():
            self.reachout_check.start()
        
        if not self.username_verification_check.is_running():
            self.username_verification_check.start()
    
    async def on_ready(self):
        """Called when bot is ready."""
        print(f'Refold Coaching Bot logged in as {self.user}')
        print(f'Bot ID: {self.user.id}')
        print(f'Guilds: {len(self.guilds)}')
        print(f'Intensive Join Channel ID: {config.INTENSIVE_JOIN_CHANNEL_ID}')
        print(f'Bot Chat Channel ID: {config.BOT_CHAT_CHANNEL_ID}')
        print(f'Coach Channel ID: {config.COACH_CHANNEL_ID}')
        print(f'Commands loaded: {len(self.commands)}')
        for cmd in self.commands:
            print(f'  - {cmd.name}: {cmd.help}')
        print('------')
    
    async def on_message(self, message):
        """Handle all messages including DMs."""
        # Skip bot messages
        if message.author == self.user:
            return
        
        # Handle commands first
        await self.process_commands(message)
        
        # Handle intensive join channel - SIMPLE AND DIRECT
        if message.channel.id == config.INTENSIVE_JOIN_CHANNEL_ID:
            await self._handle_intensive_join_message(message)
            return
        
        # Handle DM conversations
        if isinstance(message.channel, discord.DMChannel):
            await self._handle_dm_message(message)
            return
        
        # Handle bot chat channel
        if message.channel.id == config.BOT_CHAT_CHANNEL_ID:
            attendance_tracker.track_message(message.author.id, message.channel.id)
            await self._handle_bot_chat_message(message)
            return
        
        # Handle thread messages (onboarding or bot chat)
        if isinstance(message.channel, discord.Thread):
            await self._handle_thread_message(message)
            return
        
        # Handle activity feed
        if message.channel.id == config.ACTIVITY_FEED_CHANNEL_ID:
            activity_entry = attendance_tracker.parse_activity_feed_message(message)
            if activity_entry:
                print(f"Tracked activity: {activity_entry['username']} - {activity_entry['activity']} ({activity_entry['minutes']} mins)")
    
    async def on_voice_state_update(self, member, before, after):
        """Track voice channel joins."""
        if before.channel is None and after.channel is not None:
            attendance_tracker.track_voice_join(member.id)
    
    async def _handle_bot_chat_message(self, message):
        """Handle messages in the bot chat channel."""
        user_id = message.author.id
        conversation_state = self.ongoing_conversations.get(user_id)
        
        # Check if user is in goal update conversation
        if conversation_state == 'updating_goals_conversation':
            # Handle goal update conversation in thread
            await self._handle_goal_update_conversation(message)
            return
        
        # Check for natural language goal update requests
        message_lower = message.content.lower()
        goal_update_keywords = [
            'update my goals', 'change my goals', 'new goals', 'revise my goals',
            'modify my goals', 'tweak my goals', 'adjust my goals', 'edit my goals',
            'i want to update my goals', 'i want to change my goals',
            'i need to update my goals', 'i need to change my goals'
        ]
        
        if any(keyword in message_lower for keyword in goal_update_keywords):
            # Check if user is registered
            user = data_manager.get_user(user_id)
            if not user:
                await message.channel.send("❌ You're not registered for the intensive. Please join first!")
                return
            
            # Create thread for goal update conversation
            thread_name = f"Goal Update - {message.author.display_name}"
            thread = await message.create_thread(name=thread_name, auto_archive_duration=60)
            
            # Get current goals
            current_goals = user.get('goals', 'No goals set')
            
            # Set simple conversation state
            self.ongoing_conversations[user_id] = 'updating_goals_simple'
            self.ongoing_conversations[f"{user_id}_current_goals"] = current_goals
            
            # Send simple message
            await thread.send(f"Your current goals: **{current_goals}**\n\nWhat would you like to change them to?")
            return
        
        # Create thread for conversation
        if not isinstance(message.channel, discord.Thread):
            thread_name = f"Chat with {message.author.display_name}"
            thread = await message.create_thread(name=thread_name, auto_archive_duration=60)
            
            # Get user context with rankings
            user_context = self._build_user_context(message.author.id)
            
            # Immediately process the original message with GPT
            if message.content:  # Only process if message has content
                try:
                    async with thread.typing():
                        # Create conversation array with the original message
                        messages = [{'role': 'user', 'content': message.content}]
                        response = gpt_handler.get_chat_response(messages, user_context)
                        
                        # Send response
                        await self.send_ai_response(thread, response)
                except Exception as e:
                    print(f"Error generating chat response: {e}")
                    await thread.send("❌ Sorry, I'm having trouble responding right now. Please try again in a moment.")
            else:
                # If message has no content, send a generic response
                await thread.send("Hi! I'm your Refold Coach Bot. How can I help you today?")
        
        # Handle thread messages
        elif isinstance(message.channel, discord.Thread):
            await self._handle_thread_message(message)
    
    async def _handle_thread_message(self, message):
        """Handle messages in threads (onboarding or bot chat)."""
        thread_id = message.channel.id
        user_id = message.author.id
        conversation_state = self.ongoing_conversations.get(user_id)
        
        # Check if user is in goal update conversation
        if conversation_state == 'updating_goals_simple':
            # Handle simple goal update
            user = data_manager.get_user(user_id)
            if user:
                # Update goals directly
                user['goals'] = message.content
                data_manager.save_user(user_id, user)
                await message.channel.send(f"✅ Goals updated to: **{message.content}**")
            else:
                await message.channel.send("❌ Error: Could not find your user data.")
            
            # Clean up conversation state
            del self.ongoing_conversations[user_id]
            if f"{user_id}_current_goals" in self.ongoing_conversations:
                del self.ongoing_conversations[f"{user_id}_current_goals"]
            return
        
        # Check if this is an onboarding thread
        if user_id in self.ongoing_conversations:
            await self._handle_onboarding_thread_message(message)
            return
        
        # Handle as regular bot chat thread
        await self._handle_bot_chat_thread_message(message)
    
    async def _handle_bot_chat_thread_message(self, message):
        """Handle messages in bot chat threads."""
        thread_id = message.channel.id
        user_id = message.author.id
        
        # Check for natural language goal update requests
        message_lower = message.content.lower()
        goal_update_keywords = [
            'update my goals', 'change my goals', 'new goals', 'revise my goals',
            'modify my goals', 'tweak my goals', 'adjust my goals', 'edit my goals',
            'i want to update my goals', 'i want to change my goals',
            'i need to update my goals', 'i need to change my goals'
        ]
        
        if any(keyword in message_lower for keyword in goal_update_keywords):
            # Check if user is registered
            user = data_manager.get_user(user_id)
            if not user:
                await message.channel.send("❌ You're not registered for the intensive. Please join first!")
                return
            
            # Start goal update conversation
            self.ongoing_conversations[user_id] = 'updating_goals'
            await message.channel.send("What are your new goals for the intensive?")
            return
        
        # Get user context with rankings
        user_context = self._build_user_context(message.author.id)
        
        # Fetch conversation history from Discord thread (last 10 messages)
        messages = []
        async for msg in message.channel.history(limit=10):
            # Skip empty messages or bot messages that are just disclaimers or error messages
            if not msg.content or (msg.author == self.user and (msg.content.startswith("-#") or "❌" in msg.content)):
                continue
            # Proper role attribution: user messages vs bot messages
            role = "user" if msg.author != self.user else "assistant"
            messages.insert(0, {"role": role, "content": msg.content})
        
        # Ensure we have at least the current message if history is empty
        if not messages and message.content:
            messages = [{"role": "user", "content": message.content}]
        
        # Skip processing if no valid messages
        if not messages:
            return
        
        # Generate response with typing indicator
        try:
            async with message.channel.typing():
                response = gpt_handler.get_chat_response(messages, user_context)
                
                # Send response
                await self.send_ai_response(message.channel, response)
        except Exception as e:
            print(f"Error generating chat response: {e}")
            await message.channel.send("❌ Sorry, I'm having trouble responding right now. Please try again in a moment.")
    
    async def _handle_onboarding_thread_message(self, message):
        """Handle messages in onboarding threads with SMART goals validation."""
        user_id = message.author.id
        thread = message.channel
        conversation_state = self.ongoing_conversations.get(user_id)
        
        if conversation_state == 'waiting_for_goals':
            # User provided goals - validate them
            goals_text = message.content
            data_manager.save_onboarding_conversation(user_id, thread.id, goals_text, 'initial_goals')
            
            # Validate goals with typing indicator
            try:
                async with thread.typing():
                    validation_result = gpt_handler.validate_smart_goals(goals_text)
            except Exception as e:
                print(f"Error validating goals: {e}")
                await thread.send("❌ Sorry, I'm having trouble validating your goals right now. Please try again in a moment.")
                return
            
            # Save the validation attempt
            data_manager.save_onboarding_conversation(user_id, thread.id, goals_text, 'goals_attempt', validation_result)
            
            if validation_result.get('is_valid', False):
                # Goals are good - create user profile and move to app setup
                try:
                    async with thread.typing():
                        summary = gpt_handler.summarize_approved_goals(goals_text)
                except Exception as e:
                    print(f"Error summarizing goals: {e}")
                    summary = f"Great goals! Here's what you'll focus on: {goals_text}"
                
                # Create initial user profile with goals
                user_data = {
                    'discord_username': message.author.display_name,
                    'app_username': None,  # Will be set later
                    'goals': goals_text,
                    'joined_at': datetime.now().isoformat(),
                    'role_granted': False,
                    'attendance': {
                        'total_messages': 0,
                        'messages_per_day': {},
                        'voice_joins': 0,
                        'last_active': None
                    },
                    'activity_tracking': {
                        'total_minutes': 0,
                        'activities': []
                    },
                    'reachouts': {
                        'last_reachout': None,
                        'total_reachouts': 0,
                        'conversations': []
                    },
                    'conversation_summaries': []
                }
                
                # Save user profile immediately
                data_manager.save_user(user_id, user_data)
                
                # Send brief encouragement and move to app setup
                async with thread.typing():
                    await self.send_ai_response(thread, f"✅ **Great goals!** {summary}")
                await thread.send("Now let's get you set up in the app!")
                
                # Ask about app usage with reactions
                app_question = await thread.send("Do you already use the Refold app (either on mobile or the web version)?")
                await app_question.add_reaction('✅')
                await app_question.add_reaction('❌')
                
                # Move to app usage question
                self.ongoing_conversations[user_id] = 'asking_has_app'
                self.ongoing_conversations[f"{user_id}_goals"] = goals_text
                
            else:
                # Goals need improvement - provide feedback
                feedback = validation_result.get('feedback', 'Please make your goals more specific and achievable for the 2-week intensive.')
                async with thread.typing():
                    await self.send_ai_response(thread, f"🤔 **Let's refine your goals:**\n\n{feedback}\n\nPlease revise your goals and try again!")
        
        elif conversation_state == 'asking_has_app':
            # Handle app usage question responses (text or emoji)
            response_text = message.content.lower().strip()
            
            if response_text in ['yes', 'y', '✅', 'yes i do', 'i do'] or '✅' in message.content:
                # User has app - ask for username
                await thread.send("Great! What's your Refold app display name? *It's in the top left corner of the app OR the name that appears whenever you submit an action*.")
                self.ongoing_conversations[user_id] = 'waiting_for_username'
                self.ongoing_conversations[f"{user_id}_has_app"] = True
            elif response_text in ['no', 'n', '❌', 'no i don\'t', 'i don\'t'] or '❌' in message.content:
                # User doesn't have app - send link
                await thread.send(
                    "No problem! Please go to https://refold.link/webapp to set up an account and username, then come back and give me your username."
                )
                self.ongoing_conversations[user_id] = 'waiting_for_username'
                self.ongoing_conversations[f"{user_id}_has_app"] = False
            else:
                # Unclear response - ask again with reactions
                app_question = await thread.send("Do you already use the Refold app (either on mobile or the web version)?")
                await app_question.add_reaction('✅')
                await app_question.add_reaction('❌')
        
        elif conversation_state == 'waiting_for_username':
            # User provided username - check if they have app to decide verification
            app_username = message.content.strip()
            # Store for later use
            self.ongoing_conversations[f"{user_id}_entered_username"] = app_username
            
            # Check if user has app - if not, skip verification
            has_app = self.ongoing_conversations.get(f"{user_id}_has_app", True)  # Default to True for safety
            
            if not has_app:
                # User doesn't have app - skip verification and accept username
                await self._complete_registration(user_id, thread, app_username)
                return
            
            # User has app - verify against activity feed
            try:
                matched_username = await attendance_tracker.find_matching_username(thread, app_username)
                
                if matched_username:
                    if matched_username.lower() == app_username.lower():
                        # Exact match - accept it
                        await self._complete_registration(user_id, thread, app_username)
                    else:
                        # Partial match - ask for confirmation
                        await thread.send(f"Did you mean **{matched_username}**? (Type 'yes' to confirm or 'no' to try a different username)")
                        self.ongoing_conversations[user_id] = 'waiting_for_username_confirmation'
                        self.ongoing_conversations[f"{user_id}_suggested_username"] = matched_username
                else:
                    # No match found - explain limitation and offer options
                    not_found_msg = await thread.send(
                        f"I couldn't find any recent actions by **{app_username}** in the activity feed (I can only see back about 1-2 days). "
                        "Are you sure that's your display name?\n\n"
                        "React with ✅ to use this username anyway, or ❌ to try a different username."
                    )
                    await not_found_msg.add_reaction('✅')
                    await not_found_msg.add_reaction('❌')
                    
                    self.ongoing_conversations[user_id] = 'waiting_for_username_confirmation'
                    self.ongoing_conversations[f"{user_id}_suggested_username"] = None
                    return  # Prevent fallback AI response
                    
            except Exception as e:
                print(f"Error verifying username: {e}")
                # If verification fails, just accept the username
                await self._complete_registration(user_id, thread, app_username)
        
        elif conversation_state == 'waiting_for_username_confirmation':
            # User is confirming or rejecting suggested username
            response = message.content.lower().strip()
            suggested_username = self.ongoing_conversations.get(f"{user_id}_suggested_username")
            
            if response in ['yes', 'y', 'confirm']:
                if suggested_username:
                    # Use the suggested username
                    await self._complete_registration(user_id, thread, suggested_username)
                else:
                    # Use the original username
                    original_username = self.ongoing_conversations.get(f"{user_id}_entered_username", "")
                    await self._complete_registration(user_id, thread, original_username)
            elif response in ['no', 'n', 'try again']:
                # Ask for a different username
                await thread.send("No problem! What's your Refold app display name? *It's in the top left corner of the app OR the name that appears whenever you submit an action*.")
                self.ongoing_conversations[user_id] = 'waiting_for_username'
                if f"{user_id}_suggested_username" in self.ongoing_conversations:
                    del self.ongoing_conversations[f"{user_id}_suggested_username"]
            else:
                # Unclear response - ask again
                await thread.send("Please type 'yes' to confirm or 'no' to try a different username.")
        
        elif conversation_state == 'waiting_for_app_username':
            # User provided app username - complete registration
            app_username = message.content.strip()
            goals = self.ongoing_conversations.get(f"{user_id}_goals", "No goals set")
            
            # Create user profile
            user_data = {
                'discord_username': message.author.display_name,
                'app_username': app_username,
                'goals': goals,
                'joined_at': datetime.now().isoformat(),
                'role_granted': False,
                'attendance': {
                    'total_messages': 0,
                    'messages_per_day': {},
                    'voice_joins': 0,
                    'last_active': None
                },
                'activity_tracking': {
                    'total_minutes': 0,
                    'activities': []
                },
                'reachouts': {
                    'last_reachout': None,
                    'total_reachouts': 0,
                    'conversations': []
                },
                'conversation_summaries': []
            }
            
            # Save user
            data_manager.save_user(user_id, user_data)
            
            # Grant role if configured
            if config.INTENSIVE_ROLE_ID:
                try:
                    # Check all guilds for the role
                    role = None
                    correct_guild = None
                    
                    for guild in self.guilds:
                        found_role = guild.get_role(config.INTENSIVE_ROLE_ID)
                        if found_role:
                            role = found_role
                            correct_guild = guild
                            break
                    
                    if role and correct_guild:
                        member = correct_guild.get_member(user_id)
                        if member:
                            await member.add_roles(role)
                            user_data['role_granted'] = True
                            data_manager.save_user(user_id, user_data)
                            print(f"✅ Granted role '{role.name}' to {member.display_name}")
                        else:
                            print(f"❌ Member {user_id} not found in guild '{correct_guild.name}'")
                    else:
                        print(f"❌ Role with ID {config.INTENSIVE_ROLE_ID} not found in any guild")
                except Exception as e:
                    print(f"Error granting role: {e}")
            
            # Complete registration
            await thread.send(
                "Perfect! ✅ You're now registered for the intensive.\n\n"
                "**Next steps:**\n"
                "1. Join the group channels once approved\n"
                "2. Start participating in discussions\n"
                "3. Use the bot chat channel to talk with me anytime\n\n"
                "I'll be here to help you stay motivated and on track with your goals!"
            )
            
            # Update onboarding status
            data_manager.update_user_onboarding_status(user_id, 'completed')
            
            # Clean up conversation state
            del self.ongoing_conversations[user_id]
            if f"{user_id}_goals" in self.ongoing_conversations:
                del self.ongoing_conversations[f"{user_id}_goals"]
    
    async def _handle_goal_update_conversation(self, message):
        """Handle goal update conversation in thread."""
        user_id = message.author.id
        thread_id = message.channel.id
        thread = message.channel
        
        # Get conversation data
        current_goals = self.ongoing_conversations.get(f"{user_id}_current_goals", "No goals set")
        
        # Add message to conversation history
        if thread_id not in self.thread_conversations:
            self.thread_conversations[thread_id] = []
        
        self.thread_conversations[thread_id].append({
            'role': 'user',
            'content': message.content
        })
        
        # Check if user is providing new goals (look for goal-like content)
        message_lower = message.content.lower()
        goal_indicators = ['my goals are', 'i want to', 'my new goals', 'i will', 'i plan to']
        
        if any(indicator in message_lower for indicator in goal_indicators) or len(message.content) > 50:
            # User seems to be providing new goals - validate them
            try:
                async with thread.typing():
                    validation_result = gpt_handler.validate_updated_goals(message.content)
                
                if validation_result.get('is_valid', False):
                    # Goals are valid - update user data
                    user = data_manager.get_user(user_id)
                    if user:
                        # Save previous goals for history
                        previous_goals = user.get('goals', 'No previous goals')
                        
                        # Update goals
                        user['goals'] = message.content
                        user['goals_updated_at'] = datetime.now().isoformat()
                        
                        # Add to goals history if it doesn't exist
                        if 'goals_history' not in user:
                            user['goals_history'] = []
                        user['goals_history'].append({
                            'previous_goals': previous_goals,
                            'updated_at': datetime.now().isoformat(),
                            'reason': 'User requested update'
                        })
                        
                        data_manager.save_user(user_id, user)
                        
                        # Send confirmation
                        await thread.send(
                            f"Goals updated! ✅\n\n"
                            f"Your new goals: **{message.content}**\n\n"
                            f"I'll help you stay focused on these goals!"
                        )
                        
                        # Clean up conversation state
                        del self.ongoing_conversations[user_id]
                        if f"{user_id}_thread_id" in self.ongoing_conversations:
                            del self.ongoing_conversations[f"{user_id}_thread_id"]
                        if f"{user_id}_current_goals" in self.ongoing_conversations:
                            del self.ongoing_conversations[f"{user_id}_current_goals"]
                        return
                else:
                    # Goals need improvement - provide feedback
                    feedback = validation_result.get('feedback', 'Please make your goals more specific and achievable for the 2-week intensive.')
                    async with thread.typing():
                        await self.send_ai_response(thread, f"🤔 **Let's refine your goals:**\n\n{feedback}\n\nPlease revise your goals and try again!")
                    return
                    
            except Exception as e:
                print(f"Error validating goals: {e}")
                await thread.send("❌ Sorry, I'm having trouble validating your goals right now. Please try again in a moment.")
                return
        
        # Continue the conversation
        try:
            async with thread.typing():
                response = gpt_handler.continue_goal_update_conversation(
                    self.thread_conversations[thread_id], 
                    current_goals
                )
                
                # Add bot response to history
                self.thread_conversations[thread_id].append({
                    'role': 'assistant',
                    'content': response
                })
                
                # Send response
                await self.send_ai_response(thread, response)
        except Exception as e:
            print(f"Error continuing goal update conversation: {e}")
            await thread.send("❌ Sorry, I'm having trouble responding right now. Please try again in a moment.")
    
    async def _handle_intensive_join_message(self, message):
        """Handle messages in the intensive join channel to start onboarding."""
        user_id = message.author.id
        
        # Check if user is already registered
        existing_user = data_manager.get_user(user_id)
        if existing_user:
            await message.channel.send(f"{message.author.mention} You're already registered for the intensive!")
            return
        
        # Create thread for onboarding
        thread_name = f"🎯 {message.author.display_name}'s Intensive Journey"
        thread = await message.create_thread(name=thread_name, auto_archive_duration=60)
        
        # Initialize conversation state
        self.ongoing_conversations[user_id] = 'waiting_for_goals'
        
        # Send welcome message with disclaimer
        async with thread.typing():
            welcome_message = (
                "Welcome to the Refold Intensive! 🎉\n\n"
                "I'm your Coach Bot, and I'm here to help you stay motivated and on track. We're all super glad you're part of this Refold intensive! I'm still in testing, so if anything I say sounds like nonsese, please tell one of the real coaches, Ben or Clayton.\n\n"
                "If you want more information about this intensive (or you joined by clicking into this channel in the Discord), check out our [webapp](<https://refold.link/webapp>)! There you'll see all the important information for the intensive (like what it is, what to do and what events are coming up).\n\n"
                "Now, it's important to have a plan! **What are your goals for this intensive?** Please be specific about what you want to achieve in the next 2 weeks. I'll keep track of them and help you stay accountable."
            )
            await thread.send(welcome_message)
            
            # Add disclaimer
            await thread.send("-# These messages will be processed by AI and saved for Refold coaches to review")
        
        # Save initial onboarding data
        data_manager.save_onboarding_conversation(user_id, thread.id, message.content, 'initial_message')
        data_manager.update_user_onboarding_status(user_id, 'started')
    # Scheduled tasks
    @tasks.loop(hours=24)
    async def daily_summary(self):
        """Generate daily summary for coaches at 8 PM Pacific Time."""
        if not config.COACH_CHANNEL_ID:
            return
        
        try:
            # Get data for report
            users = data_manager.get_all_users()
            stats = attendance_tracker.get_activity_stats()
            
            # Get most/least active users
            user_activities = []
            for discord_id, user in users.items():
                activity = attendance_tracker.get_user_activity_summary(int(discord_id))
                user_activities.append({
                    'name': user.get('discord_username', 'Unknown'),
                    'messages': activity.get('total_messages', 0),
                    'app_minutes': activity.get('total_app_minutes', 0)
                })
            
            # Sort by activity
            user_activities.sort(key=lambda x: x['messages'], reverse=True)
            most_active = user_activities[:5]
            least_active = user_activities[-5:]
            
            # Get recent activity feed entries
            recent_activities = data_manager.get_recent_activity_feed(days=1)
            
            # Generate report
            report_data = {
                'most_active': [f"{u['name']} ({u['messages']} msgs)" for u in most_active],
                'least_active': [f"{u['name']} ({u['messages']} msgs)" for u in least_active],
                'activity_entries': len(recent_activities),
                'reachouts': []  # TODO: Track reachouts
            }
            
            report = gpt_handler.generate_daily_report(report_data)
            
            # Send to coach channel
            channel = self.get_channel(config.COACH_CHANNEL_ID)
            if channel:
                embed = discord.Embed(
                    title="Daily Coaching Report",
                    description=report,
                    color=0x00ff00,
                    timestamp=datetime.now()
                )
                await channel.send(embed=embed)
                
        except Exception as e:
            print(f"Error generating daily summary: {e}")
    
    @tasks.loop(hours=6)
    async def reachout_check(self):
        """Check for inactive users and send reachouts."""
        try:
            inactive_users = attendance_tracker.get_inactive_users(
                config.REACHOUT_THRESHOLD_DAYS,
                config.REACHOUT_THRESHOLD_MESSAGES
            )
            
            for user in inactive_users:
                discord_id = user.get('discord_id')
                if not discord_id:
                    continue
                
                # Check if we've reached out recently
                reachouts = user.get('reachouts', {})
                last_reachout = reachouts.get('last_reachout')
                
                if last_reachout:
                    last_reachout_date = datetime.fromisoformat(last_reachout.replace('Z', '+00:00'))
                    if (datetime.now() - last_reachout_date.replace(tzinfo=None)).days < 2:
                        continue  # Don't reach out more than once every 2 days
                
                # Check if user has username and activity
                app_username = user.get('app_username')
                total_minutes = user.get('activity_tracking', {}).get('total_minutes', 0)
                
                # If no username or no activity, send username collection DM
                if not app_username or total_minutes == 0:
                    try:
                        member = self.get_user(discord_id)
                        if member:
                            await member.send(
                                "Hi! 👋 I noticed I don't have your Refold app username on file, so I can't track your progress properly.\n\n"
                                "Sorry about this - the systems aren't super connected yet! 😅\n\n"
                                "Could you tell me your Refold app display name? *It's in the top left corner of the app OR the name that appears whenever you submit an action*. You can find this in the app:\n"
                                "1. Go to your account\n"
                                "2. Look at the **Display name** field\n"
                                "3. Tell me exactly what it says\n\n"
                                "Just reply here with your username!"
                            )
                            # Set conversation state to collect username
                            self.ongoing_conversations[discord_id] = 'updating_username'
                            
                            # Notify coaches
                            if config.COACH_CHANNEL_ID:
                                channel = self.get_channel(config.COACH_CHANNEL_ID)
                                if channel:
                                    await channel.send(f"📞 Asked {member.display_name} for their Refold app username")
                    except Exception as e:
                        print(f"Error sending username collection to {discord_id}: {e}")
                    continue  # Skip regular reachout
                
                # Send regular reachout message
                try:
                    member = self.get_user(discord_id)
                    if member:
                        goals = user.get('goals', 'No specific goals set')
                        message = (
                            f"Hi {member.display_name}! 👋\n\n"
                            f"I noticed you haven't been very active recently. Remember your goals: **{goals}**\n\n"
                            f"How can I help you get back on track? Feel free to chat with me anytime!"
                        )
                        
                        await member.send(message)
                        
                        # Log reachout
                        data_manager.add_reachout_conversation(
                            discord_id,
                            'low_activity',
                            'Automated reachout sent due to low activity',
                            'No response'
                        )
                        
                        # Notify coaches
                        if config.COACH_CHANNEL_ID:
                            channel = self.get_channel(config.COACH_CHANNEL_ID)
                            if channel:
                                await channel.send(f"📞 Reached out to {member.display_name} due to low activity")
                        
                        print(f"Sent reachout to {member.display_name}")
                
                except Exception as e:
                    print(f"Error sending reachout to {discord_id}: {e}")
                    
        except Exception as e:
            print(f"Error in reachout check: {e}")
    
    @tasks.loop(seconds=86400)  # 24 hours
    async def username_verification_check(self):
        """Check for users with 0 activity and send username verification reachout."""
        try:
            users = data_manager.get_all_users()
            
            for discord_id_str, user in users.items():
                discord_id = int(discord_id_str)
                
                # Check if user has 0 minutes of activity
                activity_tracking = user.get('activity_tracking', {})
                total_minutes = activity_tracking.get('total_minutes', 0)
                
                if total_minutes == 0:
                    # Check if we've already sent verification reachout
                    if data_manager.has_username_verification_been_sent(discord_id):
                        continue
                    
                    # Check if user has an app username
                    app_username = user.get('app_username')
                    if not app_username:
                        continue
                    
                    try:
                        # Get Discord user
                        member = self.get_user(discord_id)
                        if not member:
                            continue
                        
                        # Send verification reachout
                        verification_msg = await member.send(
                            f"Hey! Your username **{app_username}** hasn't logged any actions in the last 24 hours and I'm worried I have it saved wrong. "
                            "Have you tracked any learning time in the last 24 hours?"
                        )
                        
                        # Add reactions
                        await verification_msg.add_reaction('✅')
                        await verification_msg.add_reaction('❌')
                        
                        # Set conversation state for handling response
                        self.ongoing_conversations[discord_id] = 'username_verification_response'
                        self.ongoing_conversations[f"{discord_id}_verification_msg_id"] = verification_msg.id
                        
                        # Mark as sent
                        data_manager.mark_username_verification_sent(discord_id)
                        
                        # Log reachout
                        data_manager.add_reachout_conversation(
                            discord_id,
                            'username_verification',
                            f'Sent username verification reachout for {app_username}',
                            'Awaiting response'
                        )
                        
                        print(f"Sent username verification reachout to {member.display_name} ({app_username})")
                        
                    except Exception as e:
                        print(f"Error sending username verification to {discord_id}: {e}")
                        
        except Exception as e:
            print(f"Error in username verification check: {e}")
    
    async def _handle_dm_message(self, message):
        """Handle DM messages for onboarding and conversations."""
        user_id = message.author.id
        conversation_state = self.ongoing_conversations.get(user_id)
        
        if conversation_state == 'waiting_for_goals':
            # User provided goals, ask for app username
            self.ongoing_conversations[user_id] = 'waiting_for_app_username'
            
            # Save goals temporarily
            self.ongoing_conversations[f"{user_id}_goals"] = message.content
            
            await message.channel.send(
                "Great goals! 🎯\n\n"
                "Now, what's your Refold app display name? *It's in the top left corner of the app OR the name that appears whenever you submit an action*. This helps me track your progress in the app."
            )
            return  # Prevent fallback AI response
        
        elif conversation_state == 'waiting_for_app_username':
            # User provided app username, complete registration
            goals = self.ongoing_conversations.get(f"{user_id}_goals", "No goals set")
            app_username = message.content.strip()
            
            # Create user profile
            user_data = {
                'discord_username': message.author.display_name,
                'app_username': app_username,
                'goals': goals,
                'joined_at': datetime.now().isoformat(),
                'role_granted': False,
                'attendance': {
                    'total_messages': 0,
                    'messages_per_day': {},
                    'voice_joins': 0,
                    'last_active': None
                },
                'activity_tracking': {
                    'total_minutes': 0,
                    'activities': []
                },
                'reachouts': {
                    'last_reachout': None,
                    'total_reachouts': 0,
                    'conversations': []
                },
                'conversation_summaries': []
            }
            
            # Save user
            data_manager.save_user(user_id, user_data)
            
            # Grant role if configured
            if config.INTENSIVE_ROLE_ID:
                try:
                    # Check all guilds for the role
                    role = None
                    correct_guild = None
                    
                    for guild in self.guilds:
                        found_role = guild.get_role(config.INTENSIVE_ROLE_ID)
                        if found_role:
                            role = found_role
                            correct_guild = guild
                            break
                    
                    if role and correct_guild:
                        member = correct_guild.get_member(user_id)
                        if member:
                            await member.add_roles(role)
                            user_data['role_granted'] = True
                            data_manager.save_user(user_id, user_data)
                            print(f"✅ Granted role '{role.name}' to {member.display_name}")
                        else:
                            print(f"❌ Member {user_id} not found in guild '{correct_guild.name}'")
                    else:
                        print(f"❌ Role with ID {config.INTENSIVE_ROLE_ID} not found in any guild")
                except Exception as e:
                    print(f"Error granting role: {e}")
            
            # Complete registration
            await message.channel.send(
                "Perfect! ✅ You're now registered for the intensive.\n\n"
                "**Next steps:**\n"
                "1. Join the group channels once approved\n"
                "2. Start participating in discussions\n"
                "3. Use the bot chat channel to talk with me anytime\n\n"
                "I'll be here to help you stay motivated and on track with your goals!"
            )
            
            # Clean up conversation state
            del self.ongoing_conversations[user_id]
            if f"{user_id}_goals" in self.ongoing_conversations:
                del self.ongoing_conversations[f"{user_id}_goals"]
            return  # Prevent fallback AI response
        
        elif conversation_state == 'updating_goals_conversation':
            # Handle goal update conversation in DM
            await self._handle_goal_update_conversation(message)
            return
        
        elif conversation_state == 'updating_username':
            # User provided their username
            app_username = message.content.strip()
            
            user = data_manager.get_user(user_id)
            if user:
                user['app_username'] = app_username
                data_manager.save_user(user_id, user)
                
                await message.channel.send(
                    f"Perfect! ✅ I've saved **{app_username}** as your Refold app username.\n\n"
                    "Now I can track your progress properly. Keep up the great work!"
                )
                
                # Clean up conversation state
                del self.ongoing_conversations[user_id]
                return  # Prevent fallback AI response
        
        elif conversation_state == 'waiting_for_username':
            # User provided username - check if they have app to decide verification
            app_username = message.content.strip()
            # Store for later use
            self.ongoing_conversations[f"{user_id}_entered_username"] = app_username
            
            # Check if user has app - if not, skip verification
            has_app = self.ongoing_conversations.get(f"{user_id}_has_app", True)  # Default to True for safety
            
            if not has_app:
                # User doesn't have app - skip verification and update existing user profile
                user = data_manager.get_user(user_id)
                if user:
                    user['app_username'] = app_username
                    data_manager.save_user(user_id, user)
                    await message.channel.send(
                        f"Perfect! ✅ I've saved **{app_username}** as your Refold app username.\n\n"
                        "Now I can track your progress properly. Keep up the great work!"
                    )
                # Clean up conversation state
                del self.ongoing_conversations[user_id]
                if f"{user_id}_has_app" in self.ongoing_conversations:
                    del self.ongoing_conversations[f"{user_id}_has_app"]
                return  # Prevent fallback AI response
            
            # User has app - verify against activity feed
            try:
                matched_username = await attendance_tracker.find_matching_username(message.channel, app_username)
                
                if matched_username:
                    if matched_username.lower() == app_username.lower():
                        # Exact match - update user profile
                        user = data_manager.get_user(user_id)
                        if user:
                            user['app_username'] = app_username
                            data_manager.save_user(user_id, user)
                            await message.channel.send(
                                f"Perfect! ✅ I found your username **{app_username}** in the activity feed.\n\n"
                                "Now I can track your progress properly. Keep up the great work!"
                            )
                        # Clean up conversation state
                        del self.ongoing_conversations[user_id]
                        if f"{user_id}_has_app" in self.ongoing_conversations:
                            del self.ongoing_conversations[f"{user_id}_has_app"]
                        return  # Prevent fallback AI response
                    else:
                        # Partial match - ask for confirmation
                        await message.channel.send(f"Did you mean **{matched_username}**? (Type 'yes' to confirm or 'no' to try a different username)")
                        self.ongoing_conversations[user_id] = 'waiting_for_username_confirmation'
                        self.ongoing_conversations[f"{user_id}_suggested_username"] = matched_username
                        return  # Prevent fallback AI response
                else:
                    # No match found - explain limitation and offer options
                    not_found_msg = await message.channel.send(
                        f"I couldn't find any recent actions by **{app_username}** in the activity feed (I can only see back about 1-2 days). "
                        "Are you sure that's your display name?\n\n"
                        "React with ✅ to use this username anyway, or ❌ to try a different username."
                    )
                    await not_found_msg.add_reaction('✅')
                    await not_found_msg.add_reaction('❌')
                    
                    self.ongoing_conversations[user_id] = 'waiting_for_username_confirmation'
                    self.ongoing_conversations[f"{user_id}_suggested_username"] = None
                    return  # Prevent fallback AI response
                    
            except Exception as e:
                print(f"Error verifying username: {e}")
                # If verification fails, just update the username
                user = data_manager.get_user(user_id)
                if user:
                    user['app_username'] = app_username
                    data_manager.save_user(user_id, user)
                    await message.channel.send(
                        f"Perfect! ✅ I've saved **{app_username}** as your Refold app username.\n\n"
                        "Now I can track your progress properly. Keep up the great work!"
                    )
                # Clean up conversation state
                del self.ongoing_conversations[user_id]
                if f"{user_id}_has_app" in self.ongoing_conversations:
                    del self.ongoing_conversations[f"{user_id}_has_app"]
                return  # Prevent fallback AI response
        
        elif conversation_state == 'waiting_for_username_confirmation':
            # User is confirming or rejecting suggested username
            response = message.content.lower().strip()
            suggested_username = self.ongoing_conversations.get(f"{user_id}_suggested_username")
            
            if response in ['yes', 'y', 'confirm']:
                if suggested_username:
                    # Use the suggested username
                    user = data_manager.get_user(user_id)
                    if user:
                        user['app_username'] = suggested_username
                        data_manager.save_user(user_id, user)
                        await message.channel.send(
                            f"Perfect! ✅ I've saved **{suggested_username}** as your Refold app username.\n\n"
                            "Now I can track your progress properly. Keep up the great work!"
                        )
                else:
                    # Use the original username
                    original_username = self.ongoing_conversations.get(f"{user_id}_entered_username", "")
                    if original_username:
                        user = data_manager.get_user(user_id)
                        if user:
                            user['app_username'] = original_username
                            data_manager.save_user(user_id, user)
                            await message.channel.send(
                                f"Perfect! ✅ I've saved **{original_username}** as your Refold app username.\n\n"
                                "Now I can track your progress properly. Keep up the great work!"
                            )
                # Clean up conversation state
                del self.ongoing_conversations[user_id]
                if f"{user_id}_has_app" in self.ongoing_conversations:
                    del self.ongoing_conversations[f"{user_id}_has_app"]
                if f"{user_id}_suggested_username" in self.ongoing_conversations:
                    del self.ongoing_conversations[f"{user_id}_suggested_username"]
                return  # Prevent fallback AI response
            elif response in ['no', 'n', 'try again']:
                # Ask for a different username
                await message.channel.send("No problem! What's your Refold app display name? *It's in the top left corner of the app OR the name that appears whenever you submit an action*.")
                self.ongoing_conversations[user_id] = 'waiting_for_username'
                if f"{user_id}_suggested_username" in self.ongoing_conversations:
                    del self.ongoing_conversations[f"{user_id}_suggested_username"]
                return  # Prevent fallback AI response
            else:
                # Unclear response - ask again
                await message.channel.send("Please type 'yes' to confirm or 'no' to try a different username.")
                return  # Prevent fallback AI response
        
        elif conversation_state == 'username_verification_response':
            # Handle username verification reachout response (text-based)
            response_text = message.content.lower().strip()
            
            if response_text in ['yes', 'y', 'yeah', 'yep', 'sure']:
                # User says they have tracked time - ask for username again
                await message.channel.send(
                    "Great! It sounds like I might have your username wrong. What's your Refold app display name? *It's in the top left corner of the app OR the name that appears whenever you submit an action*. "
                    "I'll search for it in the activity feed to make sure I have it right."
                )
                self.ongoing_conversations[user_id] = 'waiting_for_username'
                self.ongoing_conversations[f"{user_id}_has_app"] = True  # They have app since they tracked time
            elif response_text in ['no', 'n', 'nope', 'not yet', 'haven\'t']:
                # User says they haven't tracked time - send instructions
                await message.channel.send(
                    "No worries! Here's how to start tracking your study time:\n\n"
                    "Visit https://refold.link/tracker and start tracking your study time! "
                    "Enter a task name (include the emoji 👂 to make it part of the listening intensive), "
                    "then select what kind of language learning you're doing and hit start! "
                    "When you're done, click save and I'll see it. You got this!"
                )
                # Clean up conversation state
                del self.ongoing_conversations[user_id]
                if f"{user_id}_verification_msg_id" in self.ongoing_conversations:
                    del self.ongoing_conversations[f"{user_id}_verification_msg_id"]
            else:
                # Unclear response - ask for clarification
                await message.channel.send(
                    "I'm not sure what you mean. Did you track any learning time in the last 24 hours? "
                    "Please answer 'yes' or 'no'."
                )
            return  # Prevent fallback AI response
        
        else:
            # Regular DM conversation
            user_context = self._build_user_context(user_id)
            
            # Send reminder for first-time users
            user = data_manager.get_user(user_id)
            if not user:
                await message.channel.send("💬 **Note:** Coaches can see this conversation to help provide better support.")
            
            # Fetch conversation history from last hour (up to 10 messages)
            one_hour_ago = datetime.now() - timedelta(hours=1)
            messages = []
            async for msg in message.channel.history(after=one_hour_ago, limit=10):
                # Skip empty messages or bot messages that are just disclaimers or error messages
                if not msg.content or (msg.author == self.user and (msg.content.startswith("-#") or "❌" in msg.content)):
                    continue
                # Proper role attribution: user messages vs bot messages
                role = "user" if msg.author != self.user else "assistant"
                messages.insert(0, {"role": role, "content": msg.content})
            
            # Ensure we have at least the current message if history is empty
            if not messages and message.content:
                messages = [{"role": "user", "content": message.content}]
            
            # Skip processing if no valid messages
            if not messages:
                return
            
            # Generate response with typing indicator
            try:
                async with message.channel.typing():
                    response = gpt_handler.get_chat_response(messages, user_context)
                    
                    # Send response
                    await self.send_ai_response(message.channel, response)
            except Exception as e:
                print(f"Error generating DM response: {e}")
                await message.channel.send("❌ Sorry, I'm having trouble responding right now. Please try again in a moment.")
                
                # Save conversation summary periodically
                if user and len(user.get('conversation_summaries', [])) % 5 == 0:
                    summary_data = gpt_handler.summarize_conversation(messages)
                    data_manager.add_conversation_summary(
                        user_id,
                        'dm',
                        summary_data['summary'],
                        summary_data['key_topics'],
                        summary_data['sentiment']
                    )
    
    async def _handle_other_messages(self, message):
        """Handle other message types (bot chat, activity feed, etc.)."""
        # Track attendance for bot chat channel
        if message.channel.id == config.BOT_CHAT_CHANNEL_ID:
            attendance_tracker.track_message(message.author.id, message.channel.id)
            await self._handle_bot_chat_message(message)
        
        # Parse activity feed messages
        elif message.channel.id == config.ACTIVITY_FEED_CHANNEL_ID:
            activity_entry = attendance_tracker.parse_activity_feed_message(message)
            if activity_entry:
                print(f"Tracked activity: {activity_entry['username']} - {activity_entry['activity']} ({activity_entry['minutes']} mins)")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle emoji reactions for app username flow."""
        # Skip bot reactions
        if user == self.user:
            return
        
        # Check if this is a relevant reaction
        if str(reaction.emoji) not in ['✅', '❌']:
            return
        
        # Check if user is in onboarding state
        user_id = user.id
        conversation_state = self.ongoing_conversations.get(user_id)
        
        if conversation_state == 'asking_has_app':
            # Handle app usage confirmation
            if str(reaction.emoji) == '✅':
                # User has app - ask for username
                await reaction.message.channel.send("Great! What's your Refold app display name? *It's in the top left corner of the app OR the name that appears whenever you submit an action*.")
                self.ongoing_conversations[user_id] = 'waiting_for_username'
                self.ongoing_conversations[f"{user_id}_has_app"] = True
            elif str(reaction.emoji) == '❌':
                # User doesn't have app - send link
                await reaction.message.channel.send(
                    "No problem! Please go to https://refold.link/webapp to set up an account and username, then come back and give me your username."
                )
                self.ongoing_conversations[user_id] = 'waiting_for_username'
                self.ongoing_conversations[f"{user_id}_has_app"] = False
        
        elif conversation_state == 'waiting_for_username_confirmation':
            # Handle username confirmation
            if str(reaction.emoji) == '✅':
                # User confirms username - use it
                original_username = self.ongoing_conversations.get(f"{user_id}_entered_username", "")
                if original_username:
                    await self._complete_registration(user_id, reaction.message.channel, original_username)
            elif str(reaction.emoji) == '❌':
                # User wants to try different username
                await reaction.message.channel.send("No problem! What's your Refold app display name? *It's in the top left corner of the app OR the name that appears whenever you submit an action*.")
                self.ongoing_conversations[user_id] = 'waiting_for_username'
                if f"{user_id}_suggested_username" in self.ongoing_conversations:
                    del self.ongoing_conversations[f"{user_id}_suggested_username"]
        
        elif conversation_state == 'username_verification_response':
            # Handle username verification reachout response
            if str(reaction.emoji) == '✅':
                # User says they have tracked time - ask for username again
                await reaction.message.channel.send(
                    "Great! It sounds like I might have your username wrong. What's your Refold app display name? *It's in the top left corner of the app OR the name that appears whenever you submit an action*. "
                    "I'll search for it in the activity feed to make sure I have it right."
                )
                self.ongoing_conversations[user_id] = 'waiting_for_username'
                self.ongoing_conversations[f"{user_id}_has_app"] = True  # They have app since they tracked time
            elif str(reaction.emoji) == '❌':
                # User says they haven't tracked time - send instructions
                await reaction.message.channel.send(
                    "No worries! Here's how to start tracking your study time:\n\n"
                    "Visit https://refold.link/tracker and start tracking your study time! "
                    "Enter a task name (include the emoji 👂 to make it part of the listening intensive), "
                    "then select what kind of language learning you're doing and hit start! "
                    "When you're done, click save and I'll see it. You got this!"
                )
                # Clean up conversation state
                del self.ongoing_conversations[user_id]
                if f"{user_id}_verification_msg_id" in self.ongoing_conversations:
                    del self.ongoing_conversations[f"{user_id}_verification_msg_id"]

    async def send_ai_response(self, channel, message_content: str):
        """Sends an AI-generated response with the disclaimer, splitting long messages if needed."""
        disclaimer = "\n\n-# Response is AI generated. We've done our best to ensure it's output is good, but double check important information by asking a Refold coach if you're unsure"
        
        # Split message if it's too long for Discord (2000 char limit)
        max_length = 1900  # Leave some buffer for the disclaimer
        
        if len(message_content + disclaimer) <= max_length:
            # Message is short enough, send normally with disclaimer appended
            await channel.send(message_content + disclaimer)
        else:
            # Message is too long, split it
            # Split message into chunks
            chunks = []
            current_chunk = ""
            
            # Split by sentences first, then by words if needed
            sentences = message_content.split('. ')
            for sentence in sentences:
                if len(current_chunk + sentence + '. ') <= max_length:
                    current_chunk += sentence + '. '
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence + '. '
            
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            # Send each chunk
            for i, chunk in enumerate(chunks):
                if i == len(chunks) - 1:  # Last chunk, add disclaimer
                    await channel.send(chunk + disclaimer)
                else:
                    await channel.send(chunk)
                    await asyncio.sleep(0.5)  # Small delay between chunks

    async def _complete_registration(self, user_id: int, thread, app_username: str):
        """Complete user registration with username and grant role."""
        # Update user profile with username
        user = data_manager.get_user(user_id)
        if user:
            user['app_username'] = app_username
            data_manager.save_user(user_id, user)
        
        # Grant role if configured
        if config.INTENSIVE_ROLE_ID:
            try:
                # Check all guilds for the role
                role = None
                correct_guild = None
                
                for guild in self.guilds:
                    found_role = guild.get_role(config.INTENSIVE_ROLE_ID)
                    if found_role:
                        role = found_role
                        correct_guild = guild
                        break
                
                if role and correct_guild:
                    member = correct_guild.get_member(user_id)
                    if member:
                        await member.add_roles(role)
                        # Re-fetch user to ensure we have latest data
                        user = data_manager.get_user(user_id)
                        if user:
                            user['role_granted'] = True
                            data_manager.save_user(user_id, user)
                        print(f"✅ Granted role '{role.name}' to {member.display_name}")
                    else:
                        print(f"❌ Member {user_id} not found in guild '{correct_guild.name}'")
                else:
                    print(f"❌ Role with ID {config.INTENSIVE_ROLE_ID} not found in any guild")
            except Exception as e:
                print(f"Error granting role: {e}")
        
        # Complete registration
        chat_room_ref = f"<#{config.INTENSIVE_CHAT_ROOM_ID}>" if config.INTENSIVE_CHAT_ROOM_ID else "#intensive-chat-room"
        bot_chat_ref = f"<#{config.BOT_CHAT_CHANNEL_ID}>" if config.BOT_CHAT_CHANNEL_ID else "#bot-chat"
        
        await thread.send(
            "Perfect! ✅ You're all set up for the intensive.\n\n"
            "**Here's what to do next:**\n"
            f"• Go chat with other participants in {chat_room_ref}\n"
            f"• Come chat with me anytime in {bot_chat_ref}\n"
            f"• To update your goals, go to {bot_chat_ref} and use `&update_goals` or just say \"I want to update my goals\"\n\n"
            "I'll be here to help you stay motivated and on track with your goals!"
        )
        
        # Update onboarding status
        data_manager.update_user_onboarding_status(user_id, 'completed')
        
        # Notify coaches about new registration
        if config.COACH_CHANNEL_ID:
            try:
                coach_channel = self.get_channel(config.COACH_CHANNEL_ID)
                if coach_channel:
                    member = self.guilds[0].get_member(user_id)
                    if member:
                        user = data_manager.get_user(user_id)
                        goals = user.get('goals', 'Not set') if user else 'Not set'
                        await coach_channel.send(
                            f"🎉 **New Registration:** {member.mention} ({member.display_name}) just joined the intensive!\n"
                            f"**App Username:** {app_username}\n"
                            f"**Goals:** {goals[:200]}{'...' if len(goals) > 200 else ''}"
                        )
            except Exception as e:
                print(f"Error sending coach notification: {e}")
        
        # Clean up conversation state
        del self.ongoing_conversations[user_id]
        if f"{user_id}_goals" in self.ongoing_conversations:
            del self.ongoing_conversations[f"{user_id}_goals"]
        if f"{user_id}_entered_username" in self.ongoing_conversations:
            del self.ongoing_conversations[f"{user_id}_entered_username"]
        if f"{user_id}_suggested_username" in self.ongoing_conversations:
            del self.ongoing_conversations[f"{user_id}_suggested_username"]
    
    def _is_coach(self, user):
        """Check if user has coach role."""
        if not config.COACH_ROLE_ID:
            return user.guild_permissions.administrator
        return any(role.id == config.COACH_ROLE_ID for role in user.roles)
    
    def _build_user_context(self, user_id: int) -> Dict[str, Any]:
        """Build comprehensive user context with rankings."""
        user = data_manager.get_user(user_id)
        if not user:
            return {
                'goals': 'No goals set',
                'app_username': 'Not provided',
                'total_minutes': 0,
                'minutes_rank': 'N/A',
                'conversation_count': 0,
                'conversation_rank': 'N/A',
                'reachout_count': 0,
                'reachout_rank': 'N/A',
                'total_users': 0
            }
        
        rankings = data_manager.get_user_rankings(user_id)
        activity_tracking = user.get('activity_tracking', {})
        reachouts = user.get('reachouts', {})
        conversation_summaries = user.get('conversation_summaries', [])
        
        return {
            'goals': user.get('goals', 'No goals set'),
            'app_username': user.get('app_username', 'Not provided'),
            'total_minutes': activity_tracking.get('total_minutes', 0),
            'minutes_rank': rankings.get('total_minutes_rank', 'N/A'),
            'conversation_count': len(conversation_summaries),
            'conversation_rank': rankings.get('conversations_rank', 'N/A'),
            'reachout_count': reachouts.get('total_reachouts', 0),
            'reachout_rank': rankings.get('reachouts_rank', 'N/A'),
            'total_users': rankings.get('total_users', 0)
        }
    
    
    async def _send_reachout(self, user_id: int, user: discord.Member):
        """Send a reachout message to a user."""
        try:
            # Get user data
            user_data = data_manager.get_user(user_id)
            if not user_data:
                return
            
            # Get user's goals
            goals = user_data.get('goals', 'No goals set')
            
            # Generate personalized reachout message
            try:
                async with user.typing():
                    reachout_message = gpt_handler.generate_reachout_message(goals)
            except Exception as e:
                print(f"Error generating reachout message: {e}")
                reachout_message = (
                    f"Hi {user.display_name}! 👋\n\n"
                    f"I noticed you haven't been very active lately. Your goals are: {goals}\n\n"
                    f"How are you doing with your intensive? Is there anything I can help you with?"
                )
            
            # Send DM
            await user.send(reachout_message)
            
            # Update reachout tracking
            reachouts = user_data.get('reachouts', {})
            reachouts['last_reachout'] = datetime.now().isoformat()
            reachouts['total_reachouts'] = reachouts.get('total_reachouts', 0) + 1
            
            # Save updated user data
            data_manager.save_user(user_id, user_data)
            
            print(f"Sent reachout to {user.display_name} (ID: {user_id})")
            
        except Exception as e:
            print(f"Error sending reachout to {user.display_name}: {e}")


# Commands
@commands.command(name='update_goals', help='Update your intensive goals')
async def update_goals(ctx):
    """Update user goals."""
    user_id = ctx.author.id
    
    # Check if user is registered
    user = data_manager.get_user(user_id)
    if not user:
        await ctx.send("❌ You're not registered for the intensive. Please join first!")
        return
    
    # Create thread for goal update conversation
    thread_name = f"Goal Update - {ctx.author.display_name}"
    thread = await ctx.message.create_thread(name=thread_name, auto_archive_duration=60)
    
    # Get current goals
    current_goals = user.get('goals', 'No goals set')
    
    # Start simple goal update conversation
    bot = ctx.bot
    bot.ongoing_conversations[user_id] = 'updating_goals_simple'
    bot.ongoing_conversations[f"{user_id}_current_goals"] = current_goals
    
    # Send simple message
    await thread.send(f"Your current goals: **{current_goals}**\n\nWhat would you like to change them to?")

@commands.command(name='user_info', help='Get user information (coaches only)')
async def user_info(ctx, member: discord.Member = None):
    """Get detailed information about a user."""
    bot = ctx.bot
    if not bot._is_coach(ctx.author):
        await ctx.send("❌ Only coaches can use this command.")
        return
    
    # Check if command is used in coach channel
    if ctx.channel.id != config.COACH_CHANNEL_ID:
        await ctx.send(f"❌ This command can only be used in the coach channel.")
        return
    
    if not member:
        await ctx.send("❌ Please mention a user. Usage: `&user_info @username`")
        return
    
    user_id = member.id
    user = data_manager.get_user(user_id)
    
    if not user:
        await ctx.send(f"❌ {member.mention} is not registered for the intensive.")
        return
    
    # Create embed with user information
    embed = discord.Embed(
        title=f"User Information: {member.display_name}",
        color=0x00ff00
    )
    
    embed.add_field(name="Discord Username", value=user.get('discord_username', 'Unknown'), inline=True)
    embed.add_field(name="App Username", value=user.get('app_username', 'Not provided'), inline=True)
    embed.add_field(name="Goals", value=user.get('goals', 'No goals set'), inline=False)
    embed.add_field(name="Joined At", value=user.get('joined_at', 'Unknown'), inline=True)
    embed.add_field(name="Role Granted", value="✅" if user.get('role_granted', False) else "❌", inline=True)
    
    # Attendance info
    attendance = user.get('attendance', {})
    embed.add_field(name="Total Messages", value=attendance.get('total_messages', 0), inline=True)
    embed.add_field(name="Voice Joins", value=attendance.get('voice_joins', 0), inline=True)
    embed.add_field(name="Last Active", value=attendance.get('last_active', 'Never'), inline=True)
    
    # Activity tracking
    activity = user.get('activity_tracking', {})
    embed.add_field(name="Total App Minutes", value=activity.get('total_minutes', 0), inline=True)
    embed.add_field(name="Activities Count", value=len(activity.get('activities', [])), inline=True)
    
    # Reachouts
    reachouts = user.get('reachouts', {})
    embed.add_field(name="Total Reachouts", value=reachouts.get('total_reachouts', 0), inline=True)
    embed.add_field(name="Last Reachout", value=reachouts.get('last_reachout', 'Never'), inline=True)
    
    await ctx.send(embed=embed)

@commands.command(name='all_users', help='Get summary of all users (coaches only)')
async def all_users(ctx):
    """Get summary of all users in the intensive."""
    bot = ctx.bot
    if not bot._is_coach(ctx.author):
        await ctx.send("❌ Only coaches can use this command.")
        return
    
    # Check if command is used in coach channel
    if ctx.channel.id != config.COACH_CHANNEL_ID:
        await ctx.send(f"❌ This command can only be used in the coach channel.")
        return
    
    users = data_manager.get_all_users()
    
    if not users:
        await ctx.send("❌ No users registered for the intensive.")
        return
    
    # Create embed with user summary
    embed = discord.Embed(
        title="Intensive Users Summary",
        color=0x0099ff
    )
    
    # Get user stats
    total_users = len(users)
    users_with_roles = sum(1 for user in users.values() if user.get('role_granted', False))
    users_with_goals = sum(1 for user in users.values() if user.get('goals'))
    users_with_app = sum(1 for user in users.values() if user.get('app_username'))
    
    embed.add_field(name="Total Users", value=total_users, inline=True)
    embed.add_field(name="Users with Roles", value=users_with_roles, inline=True)
    embed.add_field(name="Users with Goals", value=users_with_goals, inline=True)
    embed.add_field(name="Users with App Username", value=users_with_app, inline=True)
    
    # Get most/least active users
    user_activities = []
    for discord_id, user in users.items():
        activity = attendance_tracker.get_user_activity_summary(int(discord_id))
        user_activities.append({
            'name': user.get('discord_username', 'Unknown'),
            'messages': activity.get('total_messages', 0),
            'app_minutes': activity.get('total_app_minutes', 0)
        })
    
    # Sort by activity
    user_activities.sort(key=lambda x: x['messages'], reverse=True)
    most_active = user_activities[:5]
    least_active = user_activities[-5:]
    
    # Format names
    most_active_names = [f"{user['name']} ({user['messages']} msgs)" for user in most_active]
    inactive_names = [f"{user['name']} ({user['messages']} msgs)" for user in least_active]
    
    embed.add_field(
        name="Most Active Users (Top 5)",
        value=", ".join(most_active_names),
        inline=False
    )
    embed.add_field(
        name="Inactive Users (Last 5)",
        value=", ".join(inactive_names),
        inline=False
    )
    
    await ctx.send(embed=embed)

@commands.command(name='remove', help='Remove a user from the intensive (coaches only)')
async def remove_user(ctx, user: discord.Member = None):
    """Remove a user from the intensive program."""
    bot = ctx.bot
    if not bot._is_coach(ctx.author):
        await ctx.send("❌ Only coaches can use this command.")
        return
    
    # Check if command is used in coach channel
    if ctx.channel.id != config.COACH_CHANNEL_ID:
        await ctx.send(f"❌ This command can only be used in the coach channel.")
        return
    
    if not user:
        await ctx.send("❌ Please mention a user to remove. Usage: `&remove @username`")
        return
    
    user_id = user.id
    
    # Check if user exists in the system
    existing_user = data_manager.get_user(user_id)
    if not existing_user:
        await ctx.send(f"❌ {user.mention} is not registered for the intensive.")
        return
    
    # Remove user from users.json
    try:
        data_manager.remove_user(user_id)
        
        # Remove role if they have it
        if config.INTENSIVE_ROLE_ID:
            role = ctx.guild.get_role(config.INTENSIVE_ROLE_ID)
            if role and role in user.roles:
                await user.remove_roles(role)
        
        await ctx.send(f"✅ Successfully removed {user.mention} from the intensive program.")
        
    except Exception as e:
        print(f"Error removing user: {e}")
        await ctx.send(f"❌ Error removing {user.mention}. Please try again.")

@commands.command(name='trigger_reachout', help='Trigger a reachout to a user (coaches only)')
async def trigger_reachout(ctx, user: discord.Member = None):
    """Manually trigger a reachout to a user for testing."""
    bot = ctx.bot
    if not bot._is_coach(ctx.author):
        await ctx.send("❌ Only coaches can use this command.")
        return
    
    # Check if command is used in coach channel
    if ctx.channel.id != config.COACH_CHANNEL_ID:
        await ctx.send(f"❌ This command can only be used in the coach channel.")
        return
    
    if not user:
        await ctx.send("❌ Please mention a user. Usage: `&trigger_reachout @username`")
        return
    
    user_id = user.id
    
    # Check if user exists in the system
    existing_user = data_manager.get_user(user_id)
    if not existing_user:
        await ctx.send(f"❌ {user.mention} is not registered for the intensive.")
        return
    
    try:
        # Trigger reachout
        await bot._send_reachout(user_id, user)
        await ctx.send(f"✅ Triggered reachout to {user.mention}")
        
    except Exception as e:
        print(f"Error triggering reachout: {e}")
        await ctx.send(f"❌ Error triggering reachout to {user.mention}. Please try again.")

@commands.command(name='report', help='Get detailed user report (coaches only)')
async def user_report(ctx, user: discord.Member = None):
    """Get a comprehensive report about a user."""
    bot = ctx.bot
    if not bot._is_coach(ctx.author):
        await ctx.send("❌ Only coaches can use this command.")
        return
    
    # Check if command is used in coach channel
    if ctx.channel.id != config.COACH_CHANNEL_ID:
        await ctx.send(f"❌ This command can only be used in the coach channel.")
        return
    
    if not user:
        await ctx.send("❌ Please mention a user. Usage: `&report @username`")
        return
    
    user_id = user.id
    user_data = data_manager.get_user(user_id)
    
    if not user_data:
        await ctx.send(f"❌ {user.mention} is not registered for the intensive.")
        return
    
    try:
        # Get activity summary
        activity = attendance_tracker.get_user_activity_summary(user_id)
        
        # Create comprehensive embed
        embed = discord.Embed(
            title=f"📊 User Report: {user.display_name}",
            color=0x0099ff
        )
        
        # Basic Info
        embed.add_field(
            name="👤 Basic Information",
            value=f"**Discord:** {user_data.get('discord_username', 'Unknown')}\n"
                  f"**App Username:** {user_data.get('app_username', 'Not provided')}\n"
                  f"**Joined:** {user_data.get('joined_at', 'Unknown')}\n"
                  f"**Role Granted:** {'✅' if user_data.get('role_granted', False) else '❌'}",
            inline=False
        )
        
        # Goals
        goals = user_data.get('goals', 'No goals set')
        embed.add_field(
            name="🎯 Goals",
            value=goals[:1000] + "..." if len(goals) > 1000 else goals,
            inline=False
        )
        
        # Attendance Stats
        attendance = user_data.get('attendance', {})
        embed.add_field(
            name="📈 Attendance",
            value=f"**Total Messages:** {attendance.get('total_messages', 0)}\n"
                  f"**Voice Joins:** {attendance.get('voice_joins', 0)}\n"
                  f"**Last Active:** {attendance.get('last_active', 'Never')}",
            inline=True
        )
        
        # Activity Stats
        embed.add_field(
            name="📱 App Activity",
            value=f"**Total Minutes:** {activity.get('total_app_minutes', 0)}\n"
                  f"**Avg/Day:** {activity.get('avg_messages_per_day', 0)} msgs\n"
                  f"**Days Active:** {activity.get('days_active', 0)}",
            inline=True
        )
        
        # Reachout Info
        reachouts = user_data.get('reachouts', {})
        embed.add_field(
            name="📞 Reachouts",
            value=f"**Total:** {reachouts.get('total_reachouts', 0)}\n"
                  f"**Last:** {reachouts.get('last_reachout', 'Never')}\n"
                  f"**Conversations:** {len(reachouts.get('conversations', []))}",
            inline=True
        )
        
        # Recent Activities
        activities = user_data.get('activity_tracking', {}).get('activities', [])
        if activities:
            recent_activities = activities[-5:]  # Last 5 activities
            activity_text = "\n".join([
                f"• {act.get('activity', 'Unknown')} ({act.get('minutes', 0)} mins) - {act.get('timestamp', 'Unknown')}"
                for act in recent_activities
            ])
            embed.add_field(
                name="🔄 Recent Activities",
                value=activity_text[:1000] + "..." if len(activity_text) > 1000 else activity_text,
                inline=False
            )
        
        # Conversation Summaries
        summaries = user_data.get('conversation_summaries', [])
        if summaries:
            recent_summary = summaries[-1]
            embed.add_field(
                name="💬 Recent Conversation",
                value=f"**Sentiment:** {recent_summary.get('sentiment', 'neutral').title()}\n"
                      f"**Summary:** {recent_summary.get('summary', 'No summary')[:500]}",
                inline=False
            )
        
        # Onboarding Info
        onboarding = user_data.get('onboarding', {})
        if onboarding:
            embed.add_field(
                name="🚀 Onboarding",
                value=f"**Status:** {onboarding.get('status', 'Unknown')}\n"
                      f"**Thread ID:** {onboarding.get('thread_id', 'N/A')}\n"
                      f"**Iterations:** {len(onboarding.get('goals_iterations', []))}",
                inline=True
            )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"Error generating user report: {e}")
        await ctx.send(f"❌ Error generating report for {user.mention}. Please try again.")

@commands.command(name='userlist', help='List all users in the intensive (coaches only)')
async def userlist(ctx):
    """List all users registered for the intensive."""
    bot = ctx.bot
    if not bot._is_coach(ctx.author):
        await ctx.send("❌ Only coaches can use this command.")
        return
    
    # Check if command is used in coach channel
    if ctx.channel.id != config.COACH_CHANNEL_ID:
        await ctx.send(f"❌ This command can only be used in the coach channel.")
        return
    
    try:
        users = data_manager.get_all_users()
        
        if not users:
            await ctx.send("❌ No users registered for the intensive.")
            return
        
        # Create embed with user list
        embed = discord.Embed(
            title="👥 Intensive Users List",
            color=0x00ff00
        )
        
        # Sort users by Discord username
        user_list = []
        for discord_id, user_data in users.items():
            try:
                member = ctx.guild.get_member(int(discord_id))
                discord_name = member.display_name if member else user_data.get('discord_username', 'Unknown')
                app_username = user_data.get('app_username', 'Not provided')
                role_granted = '✅' if user_data.get('role_granted', False) else '❌'
                
                user_list.append({
                    'discord_name': discord_name,
                    'app_username': app_username,
                    'role_granted': role_granted,
                    'messages': user_data.get('attendance', {}).get('total_messages', 0)
                })
            except (ValueError, TypeError):
                continue
        
        # Sort by Discord name
        user_list.sort(key=lambda x: x['discord_name'].lower())
        
        # Format user list
        user_text = ""
        for user in user_list:
            user_text += f"**{user['discord_name']}** ({user['app_username']}) {user['role_granted']} - {user['messages']} msgs\n"
        
        # Split into chunks if too long
        if len(user_text) > 2000:
            # Split into multiple embeds
            chunks = []
            current_chunk = ""
            for line in user_text.split('\n'):
                if len(current_chunk + line + '\n') > 2000:
                    chunks.append(current_chunk.strip())
                    current_chunk = line + '\n'
                else:
                    current_chunk += line + '\n'
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            
            # Send first chunk
            embed.add_field(
                name=f"Users ({len(user_list)} total)",
                value=chunks[0],
                inline=False
            )
            await ctx.send(embed=embed)
            
            # Send remaining chunks
            for i, chunk in enumerate(chunks[1:], 1):
                embed = discord.Embed(
                    title=f"👥 Intensive Users List (Part {i+1})",
                    color=0x00ff00
                )
                embed.add_field(
                    name="Users (continued)",
                    value=chunk,
                    inline=False
                )
                await ctx.send(embed=embed)
        else:
            embed.add_field(
                name=f"Users ({len(user_list)} total)",
                value=user_text,
                inline=False
            )
            await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"Error generating user list: {e}")
        await ctx.send("❌ Error generating user list. Please try again.")

@commands.command(name='coach_help', help='List all available coach commands')
async def coach_help(ctx):
    """List all available coach commands."""
    bot = ctx.bot
    if not bot._is_coach(ctx.author):
        await ctx.send("❌ Only coaches can use this command.")
        return
    
    # Check if command is used in coach channel
    if ctx.channel.id != config.COACH_CHANNEL_ID:
        await ctx.send(f"❌ This command can only be used in the coach channel.")
        return
    
    # Create help embed
    embed = discord.Embed(
        title="🤖 Refold Coaching Bot - Coach Commands",
        description="All coach commands must be used in the coach channel.",
        color=0x0099ff
    )
    
    # User Management Commands
    embed.add_field(
        name="👥 User Management",
        value=(
            "`&userlist` - List all users in the intensive\n"
            "`&user_info @username` - Get basic user information\n"
            "`&report @username` - Get comprehensive user report\n"
            "`&remove @username` - Remove user from intensive"
        ),
        inline=False
    )
    
    # Testing Commands
    embed.add_field(
        name="🧪 Testing & Tools",
        value=(
            "`&trigger_reachout @username` - Manually trigger reachout\n"
            "`&all_users` - Get summary of all users\n"
            "`&coach_help` - Show this help message"
        ),
        inline=False
    )
    
    # User Commands (for reference)
    embed.add_field(
        name="👤 User Commands",
        value=(
            "`&update_goals` - Update your intensive goals\n"
            "*Available in any channel*"
        ),
        inline=False
    )
    
    # Usage Notes
    embed.add_field(
        name="📝 Usage Notes",
        value=(
            "• All coach commands require the Coach role\n"
            "• Commands must be used in the coach channel\n"
            "• Use `@username` to mention users in commands\n"
            "• Commands are case-sensitive"
        ),
        inline=False
    )
    
    embed.set_footer(text="Refold Coaching Bot - Coach Dashboard")
    
    await ctx.send(embed=embed)

async def main():
    """Main function to start the bot."""
    bot = RefoldCoachingBot()
    
    # Add commands to bot
    bot.add_command(update_goals)
    bot.add_command(user_info)
    bot.add_command(all_users)
    bot.add_command(remove_user)
    bot.add_command(trigger_reachout)
    bot.add_command(user_report)
    bot.add_command(userlist)
    bot.add_command(coach_help)
    
    try:
        await bot.start(config.BOT_TOKEN)
    except KeyboardInterrupt:
        print("Bot shutdown requested...")
    except Exception as e:
        print(f"Bot crashed: {e}")
    finally:
        if not bot.is_closed():
            await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
