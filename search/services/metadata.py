"""Retrieval of metadata from the core arXiv repository."""


from search import status
import requests
import os
from urllib.parse import urljoin
import json

METADATA_ENDPOINT = os.environ.get('METADATA_ENDPOINT',
                                   'https://arxiv.org/docmeta/')


# TODO: this doesn't implement the usual Flask service pattern, but it seems
#  like overkill in this case. Depending on how this is used, we can revisit
#  whether it should be Flask-ified.
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
