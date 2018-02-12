"""URL conversion for paths containing arXiv IDs."""
# TODO: move this to arxiv-base.

import re

from werkzeug.routing import BaseConverter, ValidationError

import search.util as util


class ArXivConverter(BaseConverter):
    """Route converter for arXiv IDs."""

    def to_python(self, value: str) -> str:
        """Parse URL path part to Python rep (str)."""
        return util.parse_arxiv_id(value)

    def to_url(self, value: str) -> str:
        """Cast Python rep (str) to URL path part."""
        return value
