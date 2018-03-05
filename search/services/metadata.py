"""Provides acces to paper metadata from the core arXiv repository."""

import os
from urllib.parse import urljoin
import json
from itertools import cycle
from functools import wraps

import requests
from requests.packages.urllib3.util.retry import Retry

from arxiv import status
from search.context import get_application_config, get_application_global
from search import logging
from search.domain import DocMeta


logger = logging.getLogger(__name__)


class RequestFailed(IOError):
    """The metadata endpoint returned an unexpected status code."""


class ConnectionFailed(IOError):
    """Could not connect to the metadata service."""


class SecurityException(ConnectionFailed):
    """Raised when SSL connection fails."""


class BadResponse(IOError):
    """The response from the metadata service was malformed."""


class DocMetaSession(object):
    """An HTTP session with the docmeta endpoint."""

    def __init__(self, *endpoints: str, verify_cert: bool = True) -> None:
        """
        Initialize an HTTP session.

        """
        self._session = requests.Session()
        self._verify_cert = verify_cert
        self._retry = Retry(  # type: ignore
            total=10,
            read=10,
            connect=10,
            status=10,
            backoff_factor=0.5
        )
        self._adapter = requests.adapters.HTTPAdapter(max_retries=self._retry)
        self._session.mount('https://', self._adapter)

        for endpoint in endpoints:
            if not endpoint[-1] == '/':
                endpoint += '/'
        logger.debug(f'New DocMeta session with endpoints {endpoints}')
        self._endpoints = cycle(endpoints)

    @property
    def endpoint(self):
        """Get a metadata endpoint."""
        return self._endpoints.__next__()

    def retrieve(self, document_id: str) -> DocMeta:
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

        try:
            target = urljoin(self.endpoint, document_id)
            logger.debug(
                f'{document_id}: retrieve metadata from {target} with SSL'
                f' verify {self._verify_cert}'
            )
            response = requests.get(target, verify=self._verify_cert)
        except requests.exceptions.SSLError as e:
            logger.error('SSLError: %s', e)
            raise SecurityException('SSL failed: %s' % e) from e
        except requests.exceptions.ConnectionError as e:
            logger.error('ConnectionError: %s', e)
            raise ConnectionFailed(
                'Could not connect to metadata service: %s' % e
            ) from e

        if response.status_code not in \
                [status.HTTP_200_OK, status.HTTP_206_PARTIAL_CONTENT]:
            logger.error('Request failed: %s', response.content)
            raise RequestFailed(
                '%s: failed with %i: %s' % (
                    document_id, response.status_code, response.content
                )
            )
        logger.debug(f'{document_id}: response OK')
        try:
            data = DocMeta(response.json())
        except json.decoder.JSONDecodeError as e:
            logger.error('JSONDecodeError: %s', e)
            raise BadResponse(
                '%s: could not decode response: %s' % (document_id, e)
            ) from e
        logger.debug(f'{document_id}: response decoded; done!')
        return data

    def ok(self) -> bool:
        """Health check."""
        logger.debug('check health of metadata service at %s', self.endpoint)
        try:
            r = requests.head(self.endpoint, verify=self._verify_cert)
            logger.debug('response from metadata endpoint:  %i: %s',
                         r.status_code, r.content)
            return r.ok
        except IOError as e:
            logger.error('IOError: %s', e)
            return False


def init_app(app: object = None) -> None:
    """Set default configuration parameters for an application instance."""
    config = get_application_config(app)
    config.setdefault('METADATA_ENDPOINT', 'https://arxiv.org/docmeta/')
    config.setdefault('METADATA_VERIFY_CERT', 'True')


def get_session(app: object = None) -> DocMetaSession:
    """Get a new session with the docmeta endpoint."""
    config = get_application_config(app)
    endpoint = config.get('METADATA_ENDPOINT', 'https://arxiv.org/docmeta/')
    verify_cert = bool(eval(config.get('METADATA_VERIFY_CERT', 'True')))
    if ',' in endpoint:
        return DocMetaSession(*(endpoint.split(',')), verify_cert=verify_cert)
    return DocMetaSession(endpoint, verify_cert=verify_cert)


def current_session():
    """Get/create :class:`.DocMetaSession` for this context."""
    g = get_application_global()
    if not g:
        return get_session()
    if 'docmeta' not in g:
        g.docmeta = get_session()
    return g.docmeta


@wraps(DocMetaSession.retrieve)
def retrieve(document_id: str) -> DocMeta:
    """Retrieve an arxiv document by id."""
    return current_session().retrieve(document_id)


@wraps(DocMetaSession.ok)
def ok() -> bool:
    """Return a 200 OK."""
    return current_session().ok()
