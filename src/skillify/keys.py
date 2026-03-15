"""API key management for skillify-generated skills.

Keys are stored in ~/.nanobot/workspace/keys.json and loaded at runtime
by generated skills via a shell helper pattern.
"""

from __future__ import annotations

import json
from pathlib import Path

KEYS_PATH = Path.home() / ".nanobot" / "workspace" / "keys.json"

# Shell snippet that skills embed to load a key at runtime.
# Usage: LOAD_KEY_CMD.format(key_name="YUTORI_API_KEY")
LOAD_KEY_CMD = (
    '{key_name}=$(python3 -c "import json, os; '
    "print(json.load(open(os.path.expanduser("
    "'~/.nanobot/workspace/keys.json'"
    "))).get('{key_name}', ''))\")"
)


def _load() -> dict[str, str]:
    if not KEYS_PATH.exists():
        return {}
    try:
        return json.loads(KEYS_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict[str, str]) -> None:
    KEYS_PATH.parent.mkdir(parents=True, exist_ok=True)
    KEYS_PATH.write_text(json.dumps(data, indent=2) + "\n")


def set_key(name: str, value: str) -> None:
    """Store an API key."""
    data = _load()
    data[name] = value
    _save(data)


def get_key(name: str) -> str | None:
    """Retrieve an API key, or None if not set."""
    return _load().get(name)


def remove_key(name: str) -> bool:
    """Remove an API key. Returns True if it existed."""
    data = _load()
    if name not in data:
        return False
    del data[name]
    _save(data)
    return True


def list_keys() -> dict[str, str]:
    """Return all stored keys (values masked)."""
    return {k: v[:8] + "..." for k, v in _load().items()}
