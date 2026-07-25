"""All regular expressions live here — no inline regex anywhere else (NASA-web rule)."""
import re

# Control characters except \n and \t — stripped from every prompt.
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")

# Known prompt-injection signatures (case-insensitive). Version-controlled blocklist.
INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?prior\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+", re.IGNORECASE),
    re.compile(r"^\s*system\s*:", re.IGNORECASE | re.MULTILINE),
    re.compile(r"<\|im_start\|>", re.IGNORECASE),
)

# HH:MM 24h time strings on chore preference windows.
TIME_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

# First JSON object embedded in an LLM completion.
JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)

# YYYY-MM-DD occurrence dates on recurring-event delete/exception operations.
DATE_YMD = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Runs of non-alphanumeric characters, collapsed to one hyphen when deriving
# an event-type `key` slug from a user-supplied label.
SLUG_NON_ALNUM = re.compile(r"[^a-z0-9]+")
