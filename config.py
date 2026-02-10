"""
User configuration for the market opportunity alert system.

Telegram credentials are loaded from environment variables:
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID

You can set these via:
1. Environment variables (export TELEGRAM_BOT_TOKEN=...)
2. .env file (recommended for local development)
"""

import os
import re
from pathlib import Path

def _load_env_fallback(env_path: Path, *, override: bool) -> None:
    """
    Minimal .env loader used when python-dotenv is unavailable.
    Supports KEY=VALUE lines and ignores blanks/comments.
    """
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if not key:
            continue

        if override or key not in os.environ:
            os.environ[key] = value

# Try to load from .env file if python-dotenv is available
env_path = Path(__file__).parent / ".env"
try:
    from dotenv import load_dotenv

    if env_path.exists():
        # Make .env the source of truth for local runs.
        load_dotenv(env_path, override=True)
except ImportError:
    # Fallback so .env still works without python-dotenv installed.
    _load_env_fallback(env_path, override=True)

# =====================
# USER CONFIGURATION
# =====================

# Index symbols
INDEX_SYMBOL = "^NSEI"       # Nifty 50
VIX_SYMBOL = "^INDIAVIX"     # India VIX

# Crash levels (in %) and their lookback periods for rolling highs
# Keys are drawdown percentages, values are yfinance-compatible periods.
LEVELS = {
    5: "3mo",
    10: "6mo",
    15: "1y",
    20: "2y",
}

# Telegram bot configuration
# Load from environment variables (required)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError(
        "TELEGRAM_BOT_TOKEN environment variable is required. "
        "Set it via: export TELEGRAM_BOT_TOKEN=your_token "
        "or create a .env file with TELEGRAM_BOT_TOKEN=your_token"
    )

if not TELEGRAM_CHAT_ID:
    raise ValueError(
        "TELEGRAM_CHAT_ID environment variable is required. "
        "Set it via: export TELEGRAM_CHAT_ID=your_chat_id "
        "or create a .env file with TELEGRAM_CHAT_ID=your_chat_id"
    )

TOKEN_PATTERN = re.compile(r"^\d+:[A-Za-z0-9_-]{20,}$")
CHAT_ID_PATTERN = re.compile(r"^(-?\d+|@[A-Za-z0-9_]{5,})$")

if not TOKEN_PATTERN.match(TELEGRAM_BOT_TOKEN):
    raise ValueError(
        "TELEGRAM_BOT_TOKEN looks invalid. Expected format like '123456:ABC...'. "
        "Do not use placeholders like '...'."
    )

if not CHAT_ID_PATTERN.match(TELEGRAM_CHAT_ID):
    raise ValueError(
        "TELEGRAM_CHAT_ID looks invalid. Use a numeric chat id (e.g. 1610205172, -100...) "
        "or a channel username like @my_channel."
    )

# Local state file to remember which alerts have already fired
STATE_FILE = "state.json"

# Deployment guidance per drawdown level
DEPLOYMENT_PLAN = {
    5: {
        "title": "Observe only",
        "action": "Continue SIPs. No lump-sum deployment.",
        "allocation": None,
    },
    10: {
        "title": "Small deployment",
        "action": "Deploy small cash into Large Cap funds.",
        "allocation": "Large Cap focused",
    },
    15: {
        "title": "Meaningful deployment",
        "action": "Deploy meaningful cash. Add Midcap exposure gradually.",
        "allocation": "70% Large Cap / 30% Midcap",
    },
    20: {
        "title": "Aggressive deployment",
        "action": "Deploy aggressively following allocation plan.",
        "allocation": "50% Large / 35% Mid / 15% Small (optional)",
    },
}

