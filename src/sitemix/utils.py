from __future__ import annotations

import re
from datetime import datetime, timezone


def utc_now_iso() -> str:
    """Return current UTC timestamp as ISO 8601 string with Z suffix."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(value: str, max_len: int = 80) -> str:
    """Convert arbitrary text to a stable file-safe slug."""
    value = value.strip().lower()
    value = re.sub(r"https?://", "", value)
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    if not value:
        value = "sitemix"
    return value[:max_len].rstrip("-")
