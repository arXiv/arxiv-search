"""Search query parsing and sanitization."""

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from search.domain import Query, FieldedSearchTerm, DateRange, Classification
from search.forms import AdvancedSearchForm


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


def _update_query_with_classification(query: Query, data: dict) -> Query:
    query.primary_classification = []
    groups = [
        ('computer_science', 'cs'), ('economics', 'econ'), ('eess', 'eess'),
        ('mathematics', 'math'), ('q_biology', 'q-bio'),
        ('q_finance', 'q-fin'), ('statistics', 'stat')
    ]
    for field, group in groups:
        if data.get(field):
            query.primary_classification.append(
                Classification(group=group, archive=group)
            )
    if data.get('physics') and 'physics_archives' in data:
        if 'all' in data['physics_archives']:
            query.primary_classification.append(
                Classification(group='physics')
            )
        else:
            query.primary_classification.append(
                Classification(group='physics',
                               archive=data['physics_archives'])
            )
    return query


def _update_query_with_terms(query: Query, terms_data: list) -> Query:
    query.terms = [
        FieldedSearchTerm(**term) for term in terms_data if term['term']
    ]
    return query


def _update_query_with_dates(query: Query, date_data: dict) -> Query:
    if date_data.get('all_dates'):    # Nothing to do; all dates by default.
        return query
    elif date_data.get('past_12'):
        one_year_ago = date.today() - relativedelta(months=12)
        query.date_range = DateRange(
            start_date=date(year=one_year_ago.year,
                            month=one_year_ago.month,
                            day=1)
        )
    elif date_data.get('specific_year'):
        query.date_range = DateRange(
            start_date=date(year=date_data['year'], month=1, day=1),
            end_date=date(year=date_data['year'] + 1, month=1, day=1),
        )
    elif date_data.get('date_range'):
        query.date_range = DateRange(
            start_date=date_data['from_date'],
            end_date=date_data['to_date'],
        )
    return query


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


def from_form(form: AdvancedSearchForm) -> Query:
    """
    Generate a :class:`.Query` from a valid :class:`.AdvancedSearchForm`.

    Parameters
    ----------
    form : :class:`.AdvancedSearchForm`
        Presumed to be filled and valid.

    Returns
    -------
    :class:`.Query`
    """
    query = Query()
    query = _update_query_with_dates(query, form.date.data)
    query = _update_query_with_terms(query, form.terms.data)
    query = _update_query_with_classification(query, form.classification.data)
    return query
