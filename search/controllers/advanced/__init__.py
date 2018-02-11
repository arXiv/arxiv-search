"""Controller for advanced search."""

from typing import Tuple, Dict, Any

from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
from pytz import timezone

from werkzeug import MultiDict
from werkzeug.exceptions import InternalServerError
from arxiv import status

from search.services import index, fulltext, metadata
from search.process import query
from search.domain import AdvancedQuery, FieldedSearchTerm, DateRange, \
    Classification, FieldedSearchList, ClassificationList
from search import logging
from . import forms

logger = logging.getLogger(__name__)

Response = Tuple[Dict[str, Any], int, Dict[str, Any]]

EASTERN = timezone('US/Eastern')


def search(request_params: MultiDict) -> Response:
    """
    Perform a search from the advanced search interface.

    This is intended to support ONLY form-based search, to replace the classic
    advanced search view.

    Parameters
    ----------
    request_params : dict

    Returns
    -------
    dict
        Response content.
    int
        HTTP status code.
    dict
        Extra headers to add to the response.

    Raises
    ------
    InternalServerError
        Raised when there is an unrecoverable error while interacting with the
        search index. This should be handled in the base routes, to display a
        "bug" error page to the user.
    """
    logger.debug('search request from advanced form')
    response_data = {}
    response_data['show_form'] = ('advanced' not in request_params)
    logger.debug('show_form: %s', str(response_data['show_form']))
    form = forms.AdvancedSearchForm(request_params)

    # We want to avoid attempting to validate if no query has been entered.
    #  If a query was actually submitted via the form, 'advanced' will be
    #  present in the request parameters.
    if 'advanced' in request_params:
        if form.validate():
            logger.debug('form is valid')
            q = _query_from_form(form)

            # Pagination is handled outside of the form.
            q = query.paginate(q, request_params)
            try:
                # Execute the search. We'll use the results directly in
                #  template rendering, so they get added directly to the
                #  response content.
                response_data.update(index.search(q))
            except index.IndexConnectionError as e:
                # There was a (hopefully transient) connection problem. Either
                #  this will clear up relatively quickly (next request), or
                #  there is a more serious outage.
                response_data['index_error'] = True
            except index.QueryError as e:
                # Base exception routers should pick this up and show bug page.
                raise InternalServerError(
                    'Encountered an error in search query'
                ) from e

            response_data['query'] = q
        else:
            logger.debug('form is invalid: %s' % str(form.errors))
            # Force the form to be displayed, so that we can render errors.
            #  This has most likely occurred due to someone manually crafting
            #  a GET response, but it could be something else.
            response_data['show_form'] = True

    # We want the form handy even when it is not shown to the user. For
    #  example, we can generate new form-friendly requests to update sort
    #  order and page size by embedding the form (hidden).
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
    order = form.order.data
    if order and order != 'None':
        query.order = order
    return query


def _update_query_with_classification(query: AdvancedQuery, data: MultiDict) \
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


def _update_query_with_dates(query: AdvancedQuery, date_data: MultiDict) \
        -> AdvancedQuery:
    if date_data.get('all_dates'):    # Nothing to do; all dates by default.
        return query
    elif date_data.get('past_12'):
        one_year_ago = date.today() - relativedelta(months=12)
        query.date_range = DateRange(
            start_date=datetime(year=one_year_ago.year,
                                month=one_year_ago.month,
                                day=1, hour=0, minute=0, second=0,
                                tzinfo=EASTERN)
        )
    elif date_data.get('specific_year'):
        query.date_range = DateRange(
            start_date=datetime(year=date_data['year'].year, month=1, day=1,
                                hour=0, minute=0, second=0, tzinfo=EASTERN),
            end_date=datetime(year=date_data['year'].year + 1, month=1, day=1,
                              hour=0, minute=0, second=0, tzinfo=EASTERN),
        )
    elif date_data.get('date_range'):
        if date_data['from_date']:
            date_data['from_date'] = datetime.combine(date_data['from_date'],
                                                      datetime.min.time(),
                                                      tzinfo=EASTERN)
        if date_data['to_date']:
            date_data['to_date'] = datetime.combine(date_data['to_date'],
                                                    datetime.min.time(),
                                                    tzinfo=EASTERN)

        query.date_range = DateRange(
            start_date=date_data['from_date'],
            end_date=date_data['to_date'],
        )
    return query
