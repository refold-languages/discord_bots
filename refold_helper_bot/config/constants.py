"""
Constants and hardcoded values for Refold Helper Bot.
All server IDs, channel IDs, and role mappings are defined here.
"""

# =============================================================================
# CROSS-SERVER ROLE MAPPING
# =============================================================================

# Maps language sub-server IDs to their corresponding role IDs in the main server
ROLE_MAPPING = {
    778787713012727809: '775883964266840066',  # Japanese
    667734565309382657: '780905794001698836',  # Spanish
    778788342929031188: '780905858715615262',  # Korean
    785938955823480842: '780978573514637332',  # German
    784482683282915389: '780906072457347083',  # Mandarin
    784471610270810166: '780978638421098508',  # French
    784470147930783835: '780978715920171031',  # English
    785922884446191649: '780978614409101362',  # Russian
    833885350584778804: '784613059100278834',  # Portuguese
    833879263823396864: '780979018957848596',  # Italian
    856910581088780309: '780978677495627786',  # Arabic
    789554739553632287: '784529021420568597',  # Cantonese
    1030979301362900992: '804928731025899541', # Tagalog
}

# =============================================================================
# COMMUNITY SERVERS
# =============================================================================

# All servers that are part of the Refold community network
COMMUNITY_SERVERS = {
    775877387426332682,   # Main server
    1093991079197560912,  # Additional community server
    778787713012727809,   # Japanese
    667734565309382657,   # Spanish
    778788342929031188,   # Korean
    785938955823480842,   # German
    784482683282915389,   # Mandarin
    784471610270810166,   # French
    784470147930783835,   # English
    785922884446191649,   # Russian
    833885350584778804,   # Portuguese
    833879263823396864,   # Italian
    856910581088780309,   # Arabic
    789554739553632287,   # Cantonese
    1030979301362900992,  # Tagalog
}

# =============================================================================
# AUTOMATED THREADS AND ACCOUNTABILITY
# =============================================================================

# Channels where daily accountability threads are created
ACCOUNTABILITY_CHANNEL_IDS = [829501009717755955]

# Channels where weekly graduate check-in threads are created
GRADS_ACCOUNTABILITY_CHANNEL_IDS = [1314250635188764742]

# Role pinged for daily accountability threads
DAILY_ACCOUNTABILITY_ROLE_ID = 1209597318043533404

# =============================================================================
# REACTION ROLES
# =============================================================================

# Channels where reaction role system is active
REACTION_ROLE_CHANNEL_IDS = [
    1202719368237293648,
    934209764819361902,
    1300934590004985969,
    819431673954959400,
]

# =============================================================================
# GRADUATE ROLE SYSTEM
# =============================================================================

# Maps thread IDs to role IDs for automatic graduate role assignment
THREAD_ROLES = {
    1124391562265239595: 1127996842475536557,
    1138512836277043210: 1138216925026078821,
}

# Roles that disqualify users from getting graduate roles
DISQUALIFIED_ROLES = [1093991198328365098, 1093997383995641986]

# =============================================================================
# SPANISH BOOK CLUB
# =============================================================================

# Configuration for Spanish book club role toggle
SPANISH_BOOK_CLUB = {
    'guild_id': 667734565309382657,
    'role_id': 1346227790017593376,
}

# =============================================================================
# MODERATION
# =============================================================================

# Servers to ignore when logging deleted messages
IGNORED_SERVER_IDS = [757802790532677683, 778787713012727809, 778331995297808438]

# Channel where deleted messages are logged
DELETED_MESSAGE_LOG_CHANNEL_ID = 966080907477909514

# =============================================================================
# ADMINISTRATION
# =============================================================================

# User IDs allowed to run admin commands like user count
ALLOWED_ADMIN_USER_IDS = {288075451463761920, 754169419881775285}

# =============================================================================
# UPVOTE/DOWNVOTE REACTIONS
# =============================================================================

# Custom emoji IDs for poll reactions
UPVOTE_EMOJI = '<:ReUpvote:993947837836558417>'
DOWNVOTE_EMOJI = '<:ReDownvote:993947836796383333>'

# =============================================================================
# FILE PATHS
# =============================================================================

# Data file names (will be prefixed with DATA_DIR from settings)
THREAD_CHANNELS_FILE = 'thread_channels.dat'
POLL_CHANNELS_FILE = 'poll_channels.dat'
PROJECTS_FILE = 'projects.json'
LANGUAGE_ROLES_FILE = 'language_roles.tsv'
VIDEO_LINKS_FILE = 'video_links.tsv'
CROWDSOURCE_DOCS_FILE = 'crowdsource_docs.tsv'
UNIQUE_USERS_FILE = 'unique_users.tsv'
REACTION_ROLES_FILE = 'reaction_roles.tsv'