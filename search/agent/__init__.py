"""
The search agent is responsible for updating the index as papers are published.

The agent consumes notifications on the ``MetadataIsAvailable`` stream. For
each notification, the agent retrieves metadata for the most recent version of
the indicated paper from the :mod:`search.services.metadata` service. The agent
also retrieves metadata for earlier versions, if there are multiple versions
available. Each version is passed to the :mod:`search.services.index` service,
and becomes available for discovery via :mod:`search.routes.ui`.
"""
from typing import Optional

from flask import current_app as app

from arxiv.base import agent
from .consumer import MetadataRecordProcessor, DocumentFailed, IndexingFailed


def process_stream(duration: Optional[int] = None) -> None:
    """
    Configure and run the record processor.

    Parameters
    ----------
    duration : int
        Time (in seconds) to run record processing. If None (default), will
        run "forever".

    """
    # We use the Flask application instance for configuration, and to manage
    # integrations with metadata service, search index.
    agent.process_stream(
        MetadataRecordProcessor, app.config, duration=duration
    )
