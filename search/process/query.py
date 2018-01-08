"""Search query parsing and sanitization."""

from search.domain import Query


def _parse(query_params: dict) -> Query:
    return Query(**query_params)


# TODO: write me.
def _sanitize(query: Query) -> Query:
    return query


# TODO: write me.
def _validate(query: Query) -> Query:
    return query


def prepare(query_params: dict) -> Query:
    """
    Sanitize raw query parameters, and generate a :class:`.Query`.

    Parameters
    ----------
    query_params : dict

    Returns
    -------
    :class:`.Query`
    """
    return _sanitize(_parse(query_params))
