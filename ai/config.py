"""
ai/config.py — loads GROQ_API_KEY from a .env file or the real
environment. The key is never hardcoded and never written back to disk.
"""

import os
from pathlib import Path

ENV_VAR_NAME = "GROQ_API_KEY"


def _load_dotenv(env_path: Path):
    """Minimal .env parser — avoids adding a python-dotenv dependency.
    Only sets variables that are not already present in os.environ, so a
    real environment variable always takes precedence over the .env file.
    """
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def get_api_key() -> str | None:
    """Returns the Groq API key, or None if it isn't configured anywhere."""
    project_root = Path(__file__).resolve().parent.parent
    _load_dotenv(project_root / ".env")
    return os.environ.get(ENV_VAR_NAME)
