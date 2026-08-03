"""
Cogs package for Refold Helper Bot.
Contains all feature-specific cogs for modular organization.
"""

# List of all cog modules - used by main bot for loading
COGS = [
    'cogs.fun',
    'cogs.resources',
    'cogs.roles',
    'cogs.moderation',
    'cogs.community',
    'cogs.admin',
    'cogs.course',
    'cogs.homework',
    'cogs.honeypot',
    'cogs.antispam',
]

# Cogs that are UNSAFE to run without a given privileged intent, and are
# skipped entirely when it is missing. This is a much shorter list than "cogs
# that use the intent" - most simply degrade, and degrading beats not running.
#
# antispam is the exception: its lone-image-dump detector fires on
# "images and no text", and without message_content every message looks like it
# has no text. Ordinary members posting captioned images would be timed out.
# A crippled anti-spam engine is worse than none, so it stays off.
COG_REQUIRED_INTENTS = {
    'cogs.antispam': ('message_content',),
}

# Features that quietly stop working when an intent is missing. Logged at
# startup so a degraded bot announces what it lost instead of appearing fine.
INTENT_DEGRADED_FEATURES = {
    'message_content': [
        'anti-spam detection engine (cog not loaded)',
        'all "!" prefix commands',
        'auto-thread naming from message text',
        'deleted-message audit log content',
        'honeypot ban log message text (bans still fire)',
        'homework CSV ingest via message attachment',
    ],
    'members': [
        'cross-server language role sync on join/leave',
        'automatic course enrollment on join',
        'member enumeration in admin/course commands',
        'account-age and join-recency anti-spam signals',
    ],
}