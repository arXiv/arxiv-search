"""Controller for search API requests."""

from typing import Tuple, Dict, Any, Optional
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


def search(params: MultiDict) -> Tuple[DocumentSet, int, Dict[str, Any]]:
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

    classifications = _get_classifications(params)
    if classifications is not None:
        q.primary_classification = classifications

    q = paginate(q, params)     # type: ignore
    return index.search(q, highlight=False), status.HTTP_200_OK, {}


def paper(paper_id: str) -> Tuple[Document, int, Dict[str, Any]]:
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
    return document, status.HTTP_200_OK, {}


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
    for field in ['start_date', 'end_date', 'date_type']:
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
    if date_params:
        return DateRange(**date_params)  # type: ignore
    return None


def _get_classifications(params: MultiDict) -> Optional[ClassificationList]:
    classifications = ClassificationList()
    for value in params.getlist('primary_classification'):
        if value not in taxonomy.ARCHIVES:
            raise BadRequest({
                'field': 'primary_classification',
                'reason': 'not a valid archive'
            })
        classifications.append(
            Classification(archive=value)   # type: ignore
        )
    if len(classifications) == 0:
        return None
    return classifications
