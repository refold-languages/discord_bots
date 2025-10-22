# Debugging Guide

## Enhanced Error Handling

The bot now has much better error handling and debugging output. Here's what to look for:

### Console Output

When the bot is running, you'll see detailed logs:

```
Generating chat response with 3 messages
Chat response generated: Great goals! Here's what you'll focus on...
Validating goals with model: gpt-5-mini-2025-08-07
GPT-5 response: {"is_valid": true, "feedback": "Great goals!", "summary": "..."}
```

### Common Issues & Solutions

#### 1. "No response" from bot
**Check console for:**
- `Error generating chat response: [error details]`
- `No response choices from chat completion`
- Full traceback with `traceback.print_exc()`

**Solutions:**
- Check OpenAI API key is valid
- Check internet connection
- Check OpenAI API status
- Verify model names are correct

#### 2. Goals validation not working
**Check console for:**
- `Validating goals with model: [model]`
- `GPT response: [response]`
- `JSON decode error for content: [content]`

**Solutions:**
- Check if prompt file exists and is readable
- Verify model name in prompt file header
- Check if GPT response is valid JSON

#### 3. Thread creation issues
**Check console for:**
- Discord permission errors
- Thread creation failures

**Solutions:**
- Ensure bot has "Create Public Threads" permission
- Check if channel allows thread creation
- Verify bot is in the correct server

### Debug Commands

Test individual components:

```bash
# Test prompt loading
python3 -c "from gpt_handler import gpt_handler; prompt, model = gpt_handler.load_prompt('smart_goals_validator.txt', user_goals='test'); print(f'Model: {model}')"

# Test bot import
python3 -c "from coaching_bot import RefoldCoachingBot; print('Bot imports successfully')"

# Test OpenAI connection (if you have a test key)
python3 -c "from gpt_handler import gpt_handler; print(gpt_handler.validate_smart_goals('Learn Japanese for 2 weeks'))"
```

### Error Messages Users See

- `❌ Sorry, I'm having trouble validating your goals right now. Please try again in a moment.`
- `❌ Sorry, I'm having trouble responding right now. Please try again in a moment.`

These are user-friendly error messages that appear when API calls fail.

### AI Disclaimer

Every AI-generated response now includes this disclaimer:
```
-# Response is AI generated. We've done our best to ensure it's output is good, but double check important information by asking a Refold coach if you're unsure
```

This appears automatically after all GPT responses to ensure users know the content is AI-generated.

**Format**: The disclaimer is now appended inline to the main message (not as a separate message) for better readability.

### Typing Indicators

The bot now shows typing indicators that persist during the entire response process:
- ✅ **During API calls** - Shows bot is "thinking" while GPT processes the request
- ✅ **During message sending** - Stays active while sending response and disclaimer
- ✅ **Proper timing** - Only disappears after all messages are sent
- ✅ **Better UX** - Users see continuous feedback during the entire process
- ✅ **Wrapped correctly** - Typing indicator wraps the entire GPT call, not just message sending

### Message Length Handling

The bot now handles Discord's 2000 character limit automatically:
- ✅ **Short messages** - Sent normally with inline disclaimer
- ✅ **Long messages** - Automatically split into multiple messages
- ✅ **Smart splitting** - Splits by sentences first, then by words if needed
- ✅ **Inline disclaimers** - AI disclaimer appended to the last message chunk
- ✅ **Smooth delivery** - Small delays between chunks for better readability

### Goal Validation

The bot now uses very lenient goal validation with full context:
- ✅ **Focus on clear goals** - Just needs to be understandable and language learning related
- ✅ **Intensive context** - Understands coaches provide structure, homework, and timeframe
- ✅ **Minimal requirements** - Only rejects if too vague or completely unrealistic
- ✅ **Quick approval** - Most clear goals are approved immediately
- ✅ **No follow-up questions** - Acknowledges goals without asking for details
- ✅ **Context-aware** - Knows the intensive program provides the framework

### Logging Levels

The bot now logs:
- ✅ Successful operations
- ❌ API errors with full tracebacks
- 🔍 Essential request details only
- 📝 Error messages when responses fail

**Clean Output**: Removed verbose API response status and debug prints to reduce terminal clutter while keeping essential error logging.
