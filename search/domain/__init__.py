"""
Domain classes for search service.

The domain provides a description of the main data objects used in module APIs.
Specifically, the :mod:`search.controllers`, :mod:`search.services`, and
:mod:`search.process` modules should use the domain as their primary
"language". This is intended to make static checking easier and enhance overall
intelligibility of the codebase.
"""

# pylint: disable=wildcard-import
from search.domain.base import *
from search.domain.advanced import *
from search.domain.api import APIQuery
from search.domain.classic_api import ClassicAPIQuery
from search.domain.documents import *  # type: ignore
