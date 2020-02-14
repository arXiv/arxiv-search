"""Translate classic API `Phrase` objects to Elasticsearch DSL."""

from elasticsearch_dsl import Q, Search

from search.domain import ClassicAPIQuery
from search.services.index.api_classic.query_builder import query_builder


def classic_search(search: Search, query: ClassicAPIQuery) -> Search:
    """
    Prepare a :class:`.Search` from a :class:`.ClassicAPIQuery`.

    Parameters
    ----------
    search : :class:`.Search`
        An Elasticsearch search in preparation.
    query : :class:`.ClassicAPIQuery`
        An query originating from the Classic API.

    Returns
    -------
    :class:`.Search`
        The passed ES search object, updated with specific query parameters
        that implement the advanced query.

    """
    # Initialize query.
    if query.phrase:
        dsl_query = query_builder(query.phrase)
    else:
        dsl_query = Q()

    # Filter id_list if necessary.
    if query.id_list:
        # Separate versioned and unversioned papers.
        paper_ids = [id for id in query.id_list if "v" not in id]
        paper_ids_vs = [id for id in query.id_list if "v" in id]

        # Filter by most recent unversioned paper or any versioned paper.
        id_query = (
            Q("terms", paper_id=paper_ids) & Q("term", is_current=True)
        ) | Q("terms", paper_id_v=paper_ids_vs)

        search = search.filter(id_query)
    else:
        # If no id_list, only display current results.
        search = search.filter("term", is_current=True)

    return search.query(dsl_query).sort(*query.order.to_es())
