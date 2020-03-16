from typing import Optional, Union
from datetime import datetime, timezone

from dateutil import parser

# Timestamps


class DateTime(datetime):
    """DateTime is a hack wrapper around datetime.

    Feedgen doesn't have custom timestamp formatting. It uses isoformat, so
    we use a custom class that overrides the isoformat class.
    """

    def isoformat(self, sep: str = "T", timespec: str = "auto") -> str:
        """Return formatted datetime."""
        return self.strftime("%Y-%m-%dT%H:%M:%SZ")

    @property
    def tzinfo(self) -> timezone:
        """Return the objects timezone."""
        return timezone.utc


def utc_now() -> DateTime:
    """Return timezone aware current timestamp."""
    return DateTime.fromtimestamp(
        datetime.utcnow().astimezone(timezone.utc).timestamp()
    )


def to_utc(dt: Optional[Union[DateTime, datetime, str]]) -> DateTime:
    """Localize datetime objects to UTC timezone.

    If the datetime object is None return current timestamp.
    """
    if dt is None:
        return utc_now()
    if isinstance(dt, str):
        try:
            parsed_dt = parser.parse(dt)
            return DateTime.fromtimestamp(parsed_dt.timestamp())
        except Exception:
            return utc_now()
    return DateTime.fromtimestamp(dt.astimezone(timezone.utc).timestamp())
