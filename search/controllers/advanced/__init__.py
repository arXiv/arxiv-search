"""Controller for advanced search."""

from typing import Tuple, Dict, Any

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from arxiv import status

from search.services import index, fulltext, metadata
from search.process import query
from search.domain import AdvancedQuery, FieldedSearchTerm, DateRange, \
    Classification, FieldedSearchList, ClassificationList
from search import logging
from . import forms

logger = logging.getLogger(__name__)

Response = Tuple[Dict[str, Any], int, Dict[str, Any]]


def search(request_params: dict) -> Response:
    """
    Perform a search from the advanced search interface.
    """
    logger.debug('search request from advanced form')
    response_data = {}
    response_data['show_form'] = ('advanced' not in request_params)
    logger.debug('show_form: %s', str(response_data['show_form']))
    form = forms.AdvancedSearchForm(request_params)
    if form.validate():
        logger.debug('form is valid')
        q = _query_from_form(form)
        q = query.paginate(q, request_params)
        response_data.update(index.search(q))
        response_data['query'] = q
    else:
        logger.debug('form is invalid: %s' % str(form.errors))
        q = None
        response_data['query'] = q
    response_data['form'] = form
    return response_data, status.HTTP_200_OK, {}


def _query_from_form(form: forms.AdvancedSearchForm) -> AdvancedQuery:
    """
    Generate a :class:`.AdvancedQuery` from valid :class:`.AdvancedSearchForm`.

    Parameters
    ----------
    form : :class:`.AdvancedSearchForm`
        Presumed to be filled and valid.

    Returns
    -------
    :class:`.AdvancedQuery`
    """
    query = AdvancedQuery()
    query = _update_query_with_dates(query, form.date.data)
    query = _update_query_with_terms(query, form.terms.data)
    query = _update_query_with_classification(query, form.classification.data)
    return query


def _update_query_with_classification(query: AdvancedQuery, data: dict) \
        -> AdvancedQuery:
    query.primary_classification = ClassificationList()
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


def _update_query_with_terms(query: AdvancedQuery, terms_data: list) \
        -> AdvancedQuery:
    query.terms = FieldedSearchList([
        FieldedSearchTerm(**term) for term in terms_data if term['term']
    ])
    return query


def _update_query_with_dates(query: AdvancedQuery, date_data: dict) \
        -> AdvancedQuery:
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
