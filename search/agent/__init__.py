"""
The search agent is responsible for updating the index as papers are published.

The agent consumes notifications on the ``MetadataIsAvailable`` stream. For
each notification, the agent retrieves metadata for the most recent version of
the indicated paper from the :mod:`search.services.metadata` service. The agent
also retrieves metadata for earlier versions, if there are multiple versions
available. Each version is passed to the :mod:`search.services.index` service,
and becomes available for discovery via the :mod:`search.routes.ui` and
:mod:`search.routes.external_api`.
"""

from .consumer import MetadataRecordProcessor
