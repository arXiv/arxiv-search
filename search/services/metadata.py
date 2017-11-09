"""Retrieval of metadata from the core arXiv repository."""

import os
from urllib.parse import urljoin
import json

import requests

from search import status
from search import logging

logger = logging.getLogger(__name__)

METADATA_ENDPOINT = os.environ.get('METADATA_ENDPOINT',
                                   'https://arxiv.org/docmeta/')


def retrieve(document_id: str, endpoint: str=METADATA_ENDPOINT) -> dict:
    """
    Retrieve metadata for an arXiv paper.

    Parameters
    ----------
    document_id : str

    Returns
    -------
    dict

    Raises
    ------
    IOError
    ValueError
    """
    if not document_id:    # This could use further elaboration.
        raise ValueError('Invalid value for document_id')

    if not endpoint[-1] == '/':
        endpoint += '/'
    target_url = urljoin(endpoint, document_id)
    try:
        response = requests.get(target_url)
    except requests.exceptions.SSLError as e:
        raise IOError('SSL failed: %s' % e)

    if response.status_code not in \
            [status.HTTP_200_OK, status.HTTP_206_PARTIAL_CONTENT]:
        raise IOError('%s: could not retrieve metadata: %i' %
                      (document_id, response.status_code))
    try:
        data = response.json()
    except json.decoder.JSONDecodeError as e:
        raise IOError('%s: could not decode response: %s' %
                      (document_id, e)) from e
    return data


def ok() -> bool:
    """Health check."""
    logger.debug('check health of metadata service at %s', METADATA_ENDPOINT)
    try:
        r = requests.head(METADATA_ENDPOINT)
        logger.debug('response from metadata endpoint:  %i: %s',
                     r.status_code, r.content)
        return r.ok
    except IOError as e:
        logger.debug('connection to metadata endpoint failed with %s', e)
    return False
