"""
Helpers for persisting alert state to avoid duplicate notifications.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict


def load_state(file: str) -> Dict[str, Any]:
    """
    Load previously triggered alert state from disk.
    """
    if os.path.exists(file):
        try:
            with open(file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            # Corrupt or unreadable state – start fresh
            return {}
    return {}


def save_state(state: Dict[str, Any], file: str) -> None:
    """
    Persist alert state to disk.
    """
    with open(file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)

