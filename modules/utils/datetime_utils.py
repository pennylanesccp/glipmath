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


def parse_timestamp(value: object) -> datetime | None:
    """Parse a BigQuery TIMESTAMP-like value into an aware datetime."""

    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    text = str(value).strip()
    if not text:
        return None

    normalized = text.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_local_datetime(value: object) -> datetime | None:
    """Parse a BigQuery DATETIME-like value into a naive datetime."""

    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)

    text = str(value).strip()
    if not text:
        return None

    normalized = text.replace("T", " ")
    if normalized.endswith("Z"):
        normalized = normalized[:-1]
    parsed = datetime.fromisoformat(normalized)
    return parsed.replace(tzinfo=None)


def to_iso_timestamp(value: datetime) -> str:
    """Serialize a timezone-aware datetime as ISO 8601."""

    normalized = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return normalized.astimezone(timezone.utc).isoformat()


def to_bigquery_datetime_string(value: datetime | None) -> str | None:
    """Serialize a local wall-clock datetime for BigQuery DATETIME columns."""

    if value is None:
        return None
    return value.replace(tzinfo=None).isoformat(sep=" ")
