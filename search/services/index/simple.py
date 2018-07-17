"""Support for the simple search feature."""

from elasticsearch_dsl import Search

from search.domain import SimpleQuery

from .prepare import SEARCH_FIELDS, limit_by_classification
from .util import sort


def simple_search(search: Search, query: SimpleQuery) -> Search:
    """
    Prepare a :class:`.Search` from a :class:`.SimpleQuery`.

    Parameters
    ----------
    search : :class:`.Search`
        An Elasticsearch DSL search object, in preparation for execution.
    query : :class:`.SimpleQuery`
        A query originating from the simple search controller.

    Returns
    -------
    :class:`.Search`
        The passed search object, updated with query parameters that implement
        the passed :class:`.SimpleQuery`.

    """
    search = search.filter("term", is_current=True)
    q = SEARCH_FIELDS[query.search_field](query.value)
    if query.primary_classification:
        q &= limit_by_classification(query.primary_classification)
    search = search.query(q)
    search = sort(query, search)
    return search
