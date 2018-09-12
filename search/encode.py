"""Utilities for response encoding/serialization."""

from datetime import date, datetime

from flask.json import JSONEncoder

from typing import Any, List, Union


class ISO8601JSONEncoder(JSONEncoder):
    """Renders date and datetime objects as ISO8601 datetime strings."""

    def default(self, obj: Any) -> Union[str, List[Any]]:
        """Overriden to render date(time)s in isoformat."""
        try:
            if isinstance(obj, (date, datetime)):
                return obj.isoformat()
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return JSONEncoder.default(self, obj) #type: ignore
