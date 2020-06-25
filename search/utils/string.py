"""String utilities."""

from typing import Union


def safe_str(s: Union[str, bytes]) -> str:
    """Return a UTF decoded string from bytes or the original string."""
    if isinstance(s, bytes):
        return s.decode("utf-8")
    return s
