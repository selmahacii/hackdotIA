from datetime import UTC, datetime


def ensure_utc_datetime(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware and normalize to UTC.

    Rejects naive datetimes to avoid timezone ambiguity.
    """
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError(
            "Timestamp must be timezone-aware (e.g. UTC ISO 8601). Naive datetimes are not allowed."
        )
    return dt.astimezone(UTC)


def strip_non_empty_str(v: str) -> str:
    """Strip whitespace and ensure string is not empty."""
    stripped = v.strip()
    if not stripped:
        raise ValueError("Field cannot be empty or contain only whitespace.")
    return stripped
