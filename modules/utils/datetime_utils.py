from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo


def utc_now() -> datetime:
    """Return the current UTC datetime."""

    return datetime.now(timezone.utc)


def local_now(timezone_name: str) -> datetime:
    """Return the current datetime in the configured local timezone."""

    return utc_now().astimezone(ZoneInfo(timezone_name))


def today_in_timezone(timezone_name: str) -> date:
    """Return the current local date for a timezone."""

    return local_now(timezone_name).date()


def parse_iso_datetime(value: str | None) -> datetime | None:
    """Parse an ISO-like datetime string when present."""

    if not value:
        return None
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def to_iso_timestamp(value: datetime) -> str:
    """Serialize a timezone-aware datetime as ISO 8601."""

    return value.isoformat()
