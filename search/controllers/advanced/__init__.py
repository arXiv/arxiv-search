"""
Handle requests to support the advanced search feature.

The primary entrypoint to this module is :func:`.search`, which handles
GET requests to the author search endpoint. It uses
:class:`.AdvancedSearchForm` to generate form HTML, validate request
parameters, and produce informative error messages for the user.
"""

from typing import Tuple, Dict, Any, Optional

from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
from pytz import timezone

from werkzeug.datastructures import MultiDict
from werkzeug.exceptions import InternalServerError, BadRequest
from flask import url_for

from arxiv import status

from search.services import index, fulltext, metadata
from search.domain import AdvancedQuery, FieldedSearchTerm, DateRange, \
    Classification, FieldedSearchList, ClassificationList, Query, asdict
from arxiv.base import logging
from search.controllers.util import paginate, catch_underscore_syntax

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
        search index.
    """
    logger.debug('search request from advanced form')
    response_data: Dict[str, Any] = {}
    response_data['show_form'] = ('advanced' not in request_params)
    logger.debug('show_form: %s', str(response_data['show_form']))
    form = forms.AdvancedSearchForm(request_params)

    q: Optional[Query]
    # We want to avoid attempting to validate if no query has been entered.
    #  If a query was actually submitted via the form, 'advanced' will be
    #  present in the request parameters.
    if 'advanced' in request_params:
        if form.validate():
            logger.debug('form is valid')
            q = _query_from_form(form)

            # Pagination is handled outside of the form.
            q = paginate(q, request_params)

            # Here we intervene on the user's query to look for holdouts from
            # the
            # classic search system's author indexing syntax (surname_f). We
            # rewrite with a comma, and show a warning to the user about the
            # change.
            has_classic = False
            for term in q.terms:
                # We are only looking for this syntax in the author search, or
                # in an all-fields search.
                if term.field not in ['all', 'author']:
                    continue
                term.term, _has_classic = catch_underscore_syntax(term.term)
                has_classic = _has_classic if not has_classic else has_classic
            response_data['has_classic_format'] = has_classic

            try:
                # Execute the search. We'll use the results directly in
                #  template rendering, so they get added directly to the
                #  response content.
                response_data.update(asdict(index.search(q)))
            except index.IndexConnectionError as e:
                # There was a (hopefully transient) connection problem. Either
                #  this will clear up relatively quickly (next request), or
                #  there is a more serious outage.
                logger.error('IndexConnectionError: %s', e)
                raise InternalServerError(
                    "There was a problem connecting to the search index. This "
                    "is quite likely a transient issue, so please try your "
                    "search again. If this problem persists, please report it "
                    "to help@arxiv.org."
                ) from e
            except index.QueryError as e:
                # Base exception routers should pick this up and show bug page.
                logger.error('QueryError: %s', e)
                raise InternalServerError(
                    "There was a problem executing your query. Please try "
                    "your search again.  If this problem persists, please "
                    "report it to help@arxiv.org."
                ) from e
            response_data['query'] = q
        else:
            logger.debug('form is invalid: %s', str(form.errors))
            if 'order' in form.errors or 'size' in form.errors:
                # It's likely that the user tried to set these parameters
                # manually, or that the search originated from somewhere else
                # (and was configured incorrectly).
                advanced_url = url_for('ui.advanced_search')
                raise BadRequest(
                    f"It looks like there's something odd about your search"
                    f" request. Please try <a href='{advanced_url}'>starting"
                    f" over</a>.")

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
    q = AdvancedQuery()
    q = _update_query_with_dates(q, form.date.data)
    q = _update_query_with_terms(q, form.terms.data)
    q = _update_query_with_classification(q, form.classification.data)
    if form.include_older_versions.data:
        q.include_older_versions = True
    order = form.order.data
    if order and order != 'None':
        q.order = order
    return q


def _update_query_with_classification(q: AdvancedQuery, data: MultiDict) \
        -> AdvancedQuery:
    q.primary_classification = ClassificationList()
    groups = [
        ('computer_science', 'cs'), ('economics', 'econ'), ('eess', 'eess'),
        ('mathematics', 'math'), ('q_biology', 'q-bio'),
        ('q_finance', 'q-fin'), ('statistics', 'stat')
    ]
    for field, group in groups:
        if data.get(field):
            # Fix for these typing issues is coming soon!
            #  See: https://github.com/python/mypy/pull/4397
            q.primary_classification.append(
                Classification(group=group, archive=group)  # type: ignore
            )
    if data.get('physics') and 'physics_archives' in data:
        if 'all' in data['physics_archives']:
            q.primary_classification.append(
                Classification(group='physics')  # type: ignore
            )
        else:
            q.primary_classification.append(
                Classification(     # type: ignore
                    group='physics',
                    archive=data['physics_archives']
                )
            )
    return q


def _update_query_with_terms(q: AdvancedQuery, terms_data: list) \
        -> AdvancedQuery:
    q.terms = FieldedSearchList([
        FieldedSearchTerm(**term) for term in terms_data if term['term']
    ])
    return q


def _update_query_with_dates(q: AdvancedQuery, date_data: MultiDict) \
        -> AdvancedQuery:
    filter_by = date_data['filter_by']
    if filter_by == 'all_dates':    # Nothing to do; all dates by default.
        return q
    elif filter_by == 'past_12':
        one_year_ago = date.today() - relativedelta(months=12)
        # Fix for these typing issues is coming soon!
        #  See: https://github.com/python/mypy/pull/4397
        q.date_range = DateRange(   # type: ignore
            start_date=datetime(year=one_year_ago.year,
                                month=one_year_ago.month,
                                day=1, hour=0, minute=0, second=0,
                                tzinfo=EASTERN)
        )
    elif filter_by == 'specific_year':
        q.date_range = DateRange(   # type: ignore
            start_date=datetime(year=date_data['year'].year, month=1, day=1,
                                hour=0, minute=0, second=0, tzinfo=EASTERN),
            end_date=datetime(year=date_data['year'].year + 1, month=1, day=1,
                              hour=0, minute=0, second=0, tzinfo=EASTERN),
        )
    elif filter_by == 'date_range':
        if date_data['from_date']:
            date_data['from_date'] = datetime.combine(    # type: ignore
                date_data['from_date'],
                datetime.min.time(),
                tzinfo=EASTERN)
        if date_data['to_date']:
            date_data['to_date'] = datetime.combine(    # type: ignore
                date_data['to_date'],
                datetime.min.time(),
                tzinfo=EASTERN)

        q.date_range = DateRange(   # type: ignore
            start_date=date_data['from_date'],
            end_date=date_data['to_date'],
        )
    return q
