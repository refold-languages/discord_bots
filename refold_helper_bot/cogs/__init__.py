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
# skipped entirely when it is missing. Most features simply degrade, and
# degrading beats not running. (antispam used to be listed here; it now runs a
# content-free mode, with the content filter delegated to Discord AutoMod.)
COG_REQUIRED_INTENTS = {}

# Features that quietly stop working when an intent is missing. Logged at
# startup so a degraded bot announces what it lost instead of appearing fine.
INTENT_DEGRADED_FEATURES = {
    'members': [
        'cross-server language role sync on join/leave',
        'automatic course enrollment on join',
        'role assignment for existing members on /roster load',
    ],
}
