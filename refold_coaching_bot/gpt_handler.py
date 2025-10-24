"""
OpenAI GPT integration for Refold Coaching Bot.
Handles chat responses, conversation summaries, and coach reports.

IMPORTANT: This file uses client.responses.create() for GPT-5 models, NOT client.chat.completions.create()
The training data may be outdated - this is the CORRECT format as of 2025.
"""

import os
import json
from openai import OpenAI
from typing import List, Dict, Any
from config import config


class GPTHandler:
    """Handles all OpenAI API interactions."""
    
    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.prompts_dir = config.PROMPTS_DIR
    
    def get_chat_response(self, messages: List[Dict[str, str]], user_context: Dict[str, Any] = None) -> str:
        """Generate chat response using GPT-5-mini."""
        try:
            # Build system prompt with user context
            system_prompt = self._build_system_prompt(user_context)
            
            # Prepare messages with system prompt
            chat_messages = [{"role": "system", "content": system_prompt}]
            chat_messages.extend(messages)
            
            
            # Convert messages to single input string for GPT-5
            input_text = ""
            for msg in chat_messages:
                if msg["role"] == "system":
                    input_text += f"System: {msg['content']}\n\n"
                elif msg["role"] == "user":
                    input_text += f"User: {msg['content']}\n\n"
                elif msg["role"] == "assistant":
                    input_text += f"Assistant: {msg['content']}\n\n"
            
            # IMPORTANT: Use client.responses.create() for GPT-5 models (NOT client.chat.completions.create)
            # This is the CORRECT format as of 2025 - training data may be outdated
            response = self.client.responses.create(
                model="gpt-5-mini-2025-08-07",
                input=input_text
            )
            
            # Use the correct API format
            if hasattr(response, 'output_text') and response.output_text:
                content = response.output_text
                
                # Validate content
                if not content or content.strip() == "" or content.strip() == "...":
                    print("Empty or invalid response from GPT")
                    return "I'm having trouble generating a proper response right now. Please try again in a moment."
                
                return content
            else:
                print("No output_text from GPT-5 response")
                return "I'm sorry, I couldn't generate a response. Please try again."
                
        except Exception as e:
            print(f"Error generating chat response: {e}")
            import traceback
            traceback.print_exc()
            return "I'm having trouble connecting right now. Please try again later."
    
    def summarize_conversation(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Generate conversation summary using GPT-5-nano."""
        try:
            # Prepare conversation text
            conversation_text = "\n".join([
                f"{msg['role']}: {msg['content']}" for msg in messages
            ])
            
            prompt, model = self.load_prompt('conversation_summarizer.txt', 
                                    conversation_text=conversation_text)
            
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=300
            )
            
            if response.choices and response.choices[0].message:
                # Try to parse JSON response
                import json
                try:
                    return json.loads(response.choices[0].message.content)
                except json.JSONDecodeError:
                    # Fallback if JSON parsing fails
                    content = response.choices[0].message.content
                    return {
                        "summary": content,
                        "key_topics": ["general"],
                        "sentiment": "neutral"
                    }
            else:
                return {
                    "summary": "Conversation summary unavailable",
                    "key_topics": ["general"],
                    "sentiment": "neutral"
                }
                
        except Exception as e:
            print(f"Error summarizing conversation: {e}")
            return {
                "summary": "Error generating summary",
                "key_topics": ["general"],
                "sentiment": "neutral"
            }
    
    def generate_daily_report(self, data: Dict[str, Any]) -> str:
        """Generate daily coach report using GPT-5-nano."""
        try:
            prompt, model = self.load_prompt('daily_report_generator.txt',
                                    most_active=data.get('most_active', []),
                                    least_active=data.get('least_active', []),
                                    activity_entries=data.get('activity_entries', 0),
                                    reachouts=data.get('reachouts', []))
            
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=500
            )
            
            if response.choices and response.choices[0].message:
                return response.choices[0].message.content
            else:
                return "Daily report generation failed."
                
        except Exception as e:
            print(f"Error generating daily report: {e}")
            return "Error generating daily report."
    
    def classify_reachout_outcome(self, conversation: str) -> str:
        """Classify the outcome of a reachout conversation using GPT-5-nano."""
        try:
            prompt, model = self.load_prompt('reachout_classifier.txt', conversation=conversation)
            
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=50
            )
            
            if response.choices and response.choices[0].message:
                return response.choices[0].message.content.strip()
            else:
                return "No response"
                
        except Exception as e:
            print(f"Error classifying reachout outcome: {e}")
            return "No response"
    
    def _build_system_prompt(self, user_context: Dict[str, Any] = None) -> str:
        """Build system prompt for chat responses."""
        if user_context:
            goals = user_context.get('goals', 'No specific goals set')
            app_username = user_context.get('app_username', 'Not provided')
            total_minutes = user_context.get('total_minutes', 0)
            minutes_rank = user_context.get('minutes_rank', 'N/A')
            conversation_count = user_context.get('conversation_count', 0)
            conversation_rank = user_context.get('conversation_rank', 'N/A')
            reachout_count = user_context.get('reachout_count', 0)
            reachout_rank = user_context.get('reachout_rank', 'N/A')
            total_users = user_context.get('total_users', 0)
            
            prompt, _ = self.load_prompt('coach_bot_system.txt', 
                                  user_goals=goals, 
                                  app_username=app_username,
                                  total_minutes=total_minutes,
                                  minutes_rank=minutes_rank,
                                  conversation_count=conversation_count,
                                  conversation_rank=conversation_rank,
                                  reachout_count=reachout_count,
                                  reachout_rank=reachout_rank,
                                  total_users=total_users)
            return prompt
        else:
            prompt, _ = self.load_prompt('coach_bot_system.txt', 
                                  user_goals='No goals set', 
                                  app_username='Not provided',
                                  total_minutes=0,
                                  minutes_rank='N/A',
                                  conversation_count=0,
                                  conversation_rank='N/A',
                                  reachout_count=0,
                                  reachout_rank='N/A',
                                  total_users=0)
            return prompt
    
    def load_prompt(self, filename: str, **variables) -> tuple[str, str]:
        """Load a prompt from file and replace variables. Returns (prompt, model)."""
        try:
            filepath = os.path.join(self.prompts_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract model from header
            model = "gpt-5-mini-2025-08-07"  # default
            lines = content.split('\n')
            for line in lines:
                if line.startswith('# MODEL:'):
                    model = line.replace('# MODEL:', '').strip()
                    break
            
            # Remove header lines (lines starting with #)
            prompt_lines = []
            for line in lines:
                if not line.startswith('#'):
                    prompt_lines.append(line)
            
            prompt = '\n'.join(prompt_lines).strip()
            
            # Replace variables in the format {{variable_name}}
            for key, value in variables.items():
                prompt = prompt.replace(f'{{{{{key}}}}}', str(value))
            
            return prompt, model
        except FileNotFoundError:
            print(f"Warning: Prompt file {filename} not found")
            return "", "gpt-5-mini-2025-08-07"
        except Exception as e:
            print(f"Error loading prompt {filename}: {e}")
            return "", "gpt-5-mini-2025-08-07"
    
    def validate_smart_goals(self, goals_text: str) -> Dict[str, Any]:
        """Validate if goals meet SMART criteria using the model specified in the prompt file."""
        try:
            prompt, model = self.load_prompt('smart_goals_validator.txt', user_goals=goals_text)
            print(f"Validating goals with model: {model}")
            
            # IMPORTANT: Use client.responses.create() for GPT-5 models (NOT client.chat.completions.create)
            # This is the CORRECT format as of 2025 - training data may be outdated
            response = self.client.responses.create(
                model=model,
                input=prompt
            )
            
            # Use the correct response format
            if hasattr(response, 'output_text') and response.output_text:
                content = response.output_text
            else:
                print("No output_text from GPT-5 response")
                return {
                    "is_valid": False,
                    "feedback": "I'm having trouble validating your goals right now. Please try again in a moment.",
                    "summary": ""
                }
            
            # Validate content
            if not content or content.strip() == "" or content.strip() == "...":
                print("Empty or invalid response from GPT")
                return {
                    "is_valid": False,
                    "feedback": "I'm having trouble validating your goals right now. Please try again in a moment.",
                    "summary": ""
                }
            
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                print(f"JSON decode error for content: {content}")
                # Fallback if JSON parsing fails
                return {
                    "is_valid": False,
                    "feedback": "Unable to validate goals. Please try again.",
                    "summary": ""
                }
                
        except Exception as e:
            print(f"Error validating goals: {e}")
            import traceback
            traceback.print_exc()
            return {
                "is_valid": False,
                "feedback": "Error validating goals. Please try again.",
                "summary": ""
            }
    
    def generate_goals_feedback(self, goals_text: str, issues: str) -> str:
        """Generate feedback for goals that need improvement."""
        try:
            prompt, model = self.load_prompt('smart_goals_feedback.txt', 
                                    user_goals=goals_text, 
                                    issues=issues)
            
            # GPT-5 models don't support temperature parameter
            if model.startswith('gpt-5'):
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_completion_tokens=400
                )
            else:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_completion_tokens=400,
                    temperature=1
                )
            
            if response.choices and response.choices[0].message:
                content = response.choices[0].message.content
                if not content or content.strip() == "" or content.strip() == "...":
                    return "Please revise your goals to make them more specific and achievable for the 2-week intensive."
                return content
            else:
                return "Please revise your goals to make them more specific and achievable for the 2-week intensive."
                
        except Exception as e:
            print(f"Error generating feedback: {e}")
            return "Please revise your goals to make them more specific and achievable for the 2-week intensive."
    
    def summarize_approved_goals(self, goals_text: str) -> str:
        """Create a summary of approved goals."""
        try:
            prompt, model = self.load_prompt('smart_goals_summarizer.txt', user_goals=goals_text)
            
            # IMPORTANT: Use client.responses.create() for GPT-5 models (NOT client.chat.completions.create)
            # This is the CORRECT format as of 2025 - training data may be outdated
            response = self.client.responses.create(
                model=model,
                input=prompt
            )
            
            if hasattr(response, 'output_text') and response.output_text:
                return response.output_text
            else:
                return f"Great goals! Here's what you'll focus on: {goals_text}"
                
        except Exception as e:
            print(f"Error summarizing goals: {e}")
            return f"Great goals! Here's what you'll focus on: {goals_text}"
    
    def generate_reachout_message(self, goals: str) -> str:
        """Generate a personalized reachout message for inactive users."""
        try:
            prompt, model = self.load_prompt('reachout_message.txt', user_goals=goals)
            print(f"Generating reachout message with model: {model}")
            
            # IMPORTANT: Use client.responses.create() for GPT-5 models (NOT client.chat.completions.create)
            # This is the CORRECT format as of 2025 - training data may be outdated
            response = self.client.responses.create(
                model=model,
                input=prompt
            )
            
            # Use the correct response format
            if hasattr(response, 'output_text') and response.output_text:
                content = response.output_text
            else:
                print("No output_text from GPT-5 response")
                return (
                    f"Hi! 👋\n\n"
                    f"I noticed you haven't been very active lately. Your goals are: {goals}\n\n"
                    f"How are you doing with your intensive? Is there anything I can help you with?"
                )
            
            # Validate content
            if not content or content.strip() == "" or content.strip() == "...":
                print("Empty or invalid response from GPT")
                return (
                    f"Hi! 👋\n\n"
                    f"I noticed you haven't been very active lately. Your goals are: {goals}\n\n"
                    f"How are you doing with your intensive? Is there anything I can help you with?"
                )
            
            return content
            
        except Exception as e:
            print(f"Error generating reachout message: {e}")
            return (
                f"Hi! 👋\n\n"
                f"I noticed you haven't been very active lately. Your goals are: {goals}\n\n"
                f"How are you doing with your intensive? Is there anything I can help you with?"
            )
    
    def start_goal_update_conversation(self, current_goals: str) -> str:
        """Start a conversational goal update process."""
        try:
            prompt, model = self.load_prompt('goal_update_conversation.txt', 
                                    current_goals=current_goals,
                                    conversation_context="initial")
            
            # Use the same format as other working methods
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=400
            )
            
            if response.choices and response.choices[0].message:
                content = response.choices[0].message.content
                if not content or content.strip() == "" or content.strip() == "...":
                    return f"Your current goals: **{current_goals}**\n\nWhat's prompting you to update them?"
                return content
            else:
                return f"Your current goals: **{current_goals}**\n\nWhat's prompting you to update them?"
                
        except Exception as e:
            print(f"Error starting goal update conversation: {e}")
            return f"Your current goals: **{current_goals}**\n\nWhat's prompting you to update them?"
    
    def continue_goal_update_conversation(self, messages: List[Dict[str, str]], current_goals: str) -> str:
        """Continue the goal update conversation."""
        try:
            # Build conversation context
            conversation_context = "\n".join([
                f"{msg['role']}: {msg['content']}" for msg in messages[-5:]  # Last 5 messages for context
            ])
            
            prompt, model = self.load_prompt('goal_update_conversation.txt', 
                                    current_goals=current_goals,
                                    conversation_context=conversation_context)
            
            # Use the same format as other working methods
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=400
            )
            
            if response.choices and response.choices[0].message:
                content = response.choices[0].message.content
                if not content or content.strip() == "" or content.strip() == "...":
                    return "I'm here to help you refine your goals. What would you like to focus on?"
                return content
            else:
                return "I'm here to help you refine your goals. What would you like to focus on?"
                
        except Exception as e:
            print(f"Error continuing goal update conversation: {e}")
            return "I'm here to help you refine your goals. What would you like to focus on?"
    
    def validate_updated_goals(self, new_goals: str) -> Dict[str, Any]:
        """Validate updated goals using existing SMART goals validation."""
        return self.validate_smart_goals(new_goals)


# Global GPT handler instance
gpt_handler = GPTHandler()
