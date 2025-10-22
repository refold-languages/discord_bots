# Prompt Management System

This directory contains all AI prompts used by the Refold Coaching Bot. Each prompt file includes model specifications and can be easily modified.

## File Format

Each prompt file follows this format:

```
# MODEL: gpt-5-mini-2025-08-07
# PURPOSE: Brief description of what this prompt does

[Actual prompt content with {{variables}}]
```

## Model Specification

You can change which GPT model is used for each prompt by modifying the `# MODEL:` line:

- `gpt-5-mini-2025-08-07` - Good balance of speed and quality (recommended for most tasks)
- `gpt-5-nano-2025-08-07` - Fastest and cheapest (good for simple classification/summarization)
- `gpt-5-2025-08-07` - Most capable but slower and more expensive (for complex reasoning)

## Available Prompts

### Goals Validation
- `smart_goals_validator.txt` - Validates if goals meet SMART criteria
- `smart_goals_feedback.txt` - Provides improvement suggestions for goals
- `smart_goals_summarizer.txt` - Creates summary of approved goals

### Coaching
- `coach_bot_system.txt` - Main system prompt for bot conversations

### Analytics
- `conversation_summarizer.txt` - Summarizes user conversations
- `daily_report_generator.txt` - Generates daily coach reports
- `reachout_classifier.txt` - Classifies reachout outcomes

## Variables

Prompts use `{{variable_name}}` syntax for dynamic content. Common variables:

- `{{user_goals}}` - User's stated goals
- `{{app_username}}` - User's Refold app username
- `{{conversation_text}}` - Full conversation text
- `{{user_goals}}` - User's goals for context

## Modifying Prompts

1. Edit the prompt file directly
2. Change the model if needed by updating the `# MODEL:` line
3. Test by restarting the bot
4. No code changes required!

## Best Practices

- Use `gpt-5-nano` for simple classification tasks
- Use `gpt-5-mini` for most conversational and reasoning tasks
- Use `gpt-5` only for complex analysis that requires deep reasoning
- Keep prompts focused and specific
- Test changes with real user scenarios
