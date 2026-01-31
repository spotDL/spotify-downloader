"""Constants for the matching engine."""

# Words that indicate a different version of a song (remix, live, etc.)
# These will penalize the match score if found in the result but not in the song
FORBIDDEN_WORDS: list[str] = [
    "bassboosted",
    "remix",
    "remastered",
    "remaster",
    "reverb",
    "bassboost",
    "live",
    "acoustic",
    "8daudio",
    "concert",
    "acapella",
    "slowed",
    "instrumental",
    "cover",
]

# Minimum thresholds for matching
MIN_NAME_MATCH: float = 60.0  # Minimum name match percentage
MIN_ARTIST_MATCH: float = 70.0  # Minimum artist match percentage
MIN_TIME_MATCH: float = 25.0  # Minimum time match percentage

# Score adjustments
FORBIDDEN_WORD_PENALTY: float = 15.0  # Points deducted per forbidden word
EXPLICIT_MISMATCH_PENALTY: float = 5.0  # Points deducted for explicit mismatch

# Match thresholds
HIGH_MATCH_THRESHOLD: float = 85.0  # Threshold for high-quality matches
ISRC_MATCH_THRESHOLD: float = 80.0  # ISRC match considered reliable above this
