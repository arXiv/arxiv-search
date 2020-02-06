"""URL conversion for paths containing arXiv groups or archives."""

from typing import List, Optional
from arxiv import taxonomy
from werkzeug.routing import BaseConverter, ValidationError


class ArchiveConverter(BaseConverter):
    """Route converter for arXiv IDs."""

    def to_python(self, value: str) -> Optional[List[str]]:
        """Parse URL path part to Python rep (str)."""
        valid_archives = []
        for archive in value.split(","):
            if archive not in taxonomy.ARCHIVES:
                continue
            # Support old archives.
            if archive in taxonomy.ARCHIVES_SUBSUMED:
                cat = taxonomy.CATEGORIES[taxonomy.ARCHIVES_SUBSUMED[archive]]
                archive = cat["in_archive"]
            valid_archives.append(archive)
        if not valid_archives:
            raise ValidationError()
        return valid_archives

    def to_url(self, value: List[str]) -> str:
        """Cast Python rep (list) to URL path part."""
        return ",".join(value)
