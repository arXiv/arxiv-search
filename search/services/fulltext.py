"""Retrieve fulltext content for arXiv papers."""

from search import status
import requests
import os
from urllib.parse import urljoin
import json

FULLTEXT_ENDPOINT = os.environ.get('FULLTEXT_ENDPOINT',
                                   'https://fulltext.arxiv.org/fulltext/')


def retrieve(document_id: str, endpoint: str=FULLTEXT_ENDPOINT) -> dict:
    """
    Retrieve fulltext content for an arXiv paper.

    Parameters
    ----------
    document_id : str
        arXiv identifier, including version tag. E.g. ``"1234.56787v3"``.
    endpoint : str
        Base URL for fulltext endpoint.

    Returns
    -------
    dict
        Includes the content itself, creation (extraction) date, and extractor
        version.

    Raises
    ------
    ValueError
        Raised when ``document_id`` is not a valid arXiv paper identifier.
    IOError
        Raised when unable to retrieve fulltext content.
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

    if response.status_code != status.HTTP_200_OK:
        raise IOError('%s: could not retrieve fulltext: %i' %
                      (document_id, response.status_code))
    try:
        data = response.json()
    except json.decoder.JSONDecodeError as e:
        raise IOError('%s: could not decode response: %s' %
                      (document_id, e)) from e
    return data


def ok() -> bool:
    """Health check."""
    try:
        return requests.head(FULLTEXT_ENDPOINT).ok
    except IOError:
        pass
    return False
