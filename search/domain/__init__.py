"""
Domain classes for search service.

The domain provides a description of the main data objects used in module APIs.
Specifically, the :mod:`search.controllers`, :mod:`search.services`, and
:mod:`search.process` modules should use the domain as their primary
"language". This is intended to make static checking easier and enhance overall
intelligibility of the codebase.
"""

# pylint: disable=wildcard-import
from .base import *
from .advanced import *
from .api import *
