# globals.py

# afk_users and user_levels are no longer needed here as they will be
# managed within the bot object itself, and eventually in a database.
# For now, we keep them for backward compatibility with the current cogs.
afk_users = {}
user_xp = {}
user_levels = {}

# This file is no longer used for saving data.
# The LEVELS_FILE path is still useful for loading existing data once.
LEVELS_FILE = "levels.json"

# The PROFANITY_WORDS list is no longer used since the
# moderation cog now uses a machine learning model.
# We keep it as a placeholder to avoid import errors for now.
PROFANITY_WORDS = []