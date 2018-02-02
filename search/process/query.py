"""Search query parsing and sanitization."""

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from search.domain import Query, FieldedSearchTerm, DateRange, Classification


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


def paginate(query: Query, data: dict) -> Query:
    """
    Update pagination parameters on a :class:`.Query` from request parameters.

    Parameters
    ----------
    query : :class:`.Query`
    data : dict

    Returns
    -------
    :class:`.Query`
    """
    query.page_start = int(data.get('start', 0))
    query.page_size = int(data.get('size', 25))
    return query
