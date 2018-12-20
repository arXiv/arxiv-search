"""Controller for search API requests."""

from typing import Tuple, Dict, Any, Optional, List
import re
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import dateutil.parser
from pytz import timezone
import pytz


from werkzeug.datastructures import MultiDict, ImmutableMultiDict
from werkzeug.exceptions import InternalServerError, BadRequest, NotFound
from flask import url_for

from arxiv import status, taxonomy
from arxiv.base import logging

from search.services import index, fulltext, metadata
from search.controllers.util import paginate
from ...domain import Query, APIQuery, FieldedSearchList, FieldedSearchTerm, \
    DateRange, ClassificationList, Classification, asdict, DocumentSet, \
    Document

logger = logging.getLogger(__name__)
EASTERN = timezone('US/Eastern')


def search(params: MultiDict) -> Tuple[Dict[str, Any], int, Dict[str, Any]]:
    """
    Handle a search request from the API.

    Parameters
    ----------
    params : :class:`MultiDict`
        GET query parameters from the request.

    Returns
    -------
    dict
        Response data (to serialize).
    int
        HTTP status code.
    dict
        Extra headers for the response.
    """
    q = APIQuery()
    terms = _get_fielded_terms(params)
    if terms is not None:
        q.terms = terms
    date_range = _get_date_params(params)
    if date_range is not None:
        q.date_range = date_range

    primary_query = params.get('primary_classification')
    if primary_query:
        primary_classification = _get_classification(primary_query)
        q.primary_classification = primary_classification

    secondary_query = params.getlist('secondary_classification')
    if secondary_query:
        q.secondary_classification = list(
            map(_get_classification, secondary_query)
        )

    include_fields = _get_include_fields(params)
    if include_fields:
        q.include_fields += include_fields

    q = paginate(q, params)     # type: ignore
    document_set = index.search(q, highlight=False)
    logger.debug('Got document set with %i results', len(document_set.results))
    return {'results': document_set, 'query': q}, status.HTTP_200_OK, {}


def paper(paper_id: str) -> Tuple[Dict[str, Any], int, Dict[str, Any]]:
    """
    Handle a request for paper metadata from the API.

    Parameters
    ----------
    paper_id : str
        arXiv paper ID for the requested paper.

    Returns
    -------
    dict
        Response data (to serialize).
    int
        HTTP status code.
    dict
        Extra headers for the response.

    Raises
    ------
    :class:`NotFound`
        Raised when there is no document with the provided paper ID.

    """
    try:
        document = index.get_document(paper_id)
    except index.DocumentNotFound as e:
        logger.error('Document not found')
        raise NotFound('No such document') from e
    return {'results': document}, status.HTTP_200_OK, {}


def _get_include_fields(params: MultiDict) -> List[str]:
    include_fields = params.getlist('include')
    allowed_fields = Document.fields()
    if include_fields:
        return [field for field in include_fields if field in allowed_fields]
    return []


def _get_fielded_terms(params: MultiDict) -> Optional[FieldedSearchList]:
    terms = FieldedSearchList()
    for field, _ in Query.SUPPORTED_FIELDS:
        values = params.getlist(field)
        for value in values:
            terms.append(FieldedSearchTerm(     # type: ignore
                operator='AND',
                field=field,
                term=value
            ))
    if len(terms) == 0:
        return None
    return terms


def _get_date_params(params: MultiDict) -> Optional[DateRange]:
    date_params = {}
    for field in ['start_date', 'end_date']:
        value = params.getlist(field)
        if not value:
            continue
        try:
            dt = dateutil.parser.parse(value[0])
            if not dt.tzinfo:
                dt = pytz.utc.localize(dt)
            dt = dt.replace(tzinfo=EASTERN)
        except ValueError:
            raise BadRequest({'field': field, 'reason': 'invalid datetime'})
        date_params[field] = dt
    if 'date_type' in params:
        date_params['date_type'] = params.get('date_type')
    if date_params:
        return DateRange(**date_params)  # type: ignore
    return None


def _to_classification(value: List[str]) -> Tuple[Classification]:
    clsns = []
    if value in taxonomy.definitions.GROUPS:
        klass = taxonomy.Group
        field = 'group'
    elif value in taxonomy.definitions.ARCHIVES:
        klass = taxonomy.Archive
        field = 'archive'
    elif value in taxonomy.definitions.CATEGORIES:
        klass = taxonomy.Category
        field = 'category'
    else:
        raise ValueError('not a valid classification')
    value = klass(value)
    clsns.append(Classification(**{field: {'id': value}}))   # type: ignore
    if value.unalias != value:
        clsns.append(Classification(**{field: {'id': value.unalias()}}))   # type: ignore
    if value.canonical != value:
        clsns.append(Classification(**{field: {'id': value.canonical}}))   # type: ignore
    return tuple(clsns)


def _get_classification(value: str) -> Tuple[Classification]:
    try:
        return _to_classification(value)
    except ValueError:
        raise BadRequest({
            'field': 'primary_classification',
            'reason': 'not a valid classification term'
        })
