"""
Provides acces to paper metadata from the core arXiv repository.

The primary entrypoint to this module is :func:`.retrieve`, which retrieves
:class:`.DocMeta` for a published arXiv paper.

:class:`.DocMetaSession` encapsulates configuration parameters and a connection
to the docmeta endpoint(s) for thread-safety and efficiency. The functions
mentioned above load the appropriate instance of :class:`.DocMetaSession`
depending on the context of the request.
"""

import ast
import json
from typing import List
from http import HTTPStatus
from itertools import cycle
from functools import wraps
from urllib.parse import urljoin

import requests
from requests.packages.urllib3.util.retry import Retry

import logging

from search.domain import DocMeta
from search.context import get_application_config, get_application_global


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

        Parameters
        ----------
        endpoints : str
            One or more endpoints for metadata retrieval. If more than one
            are provided, calls to :meth:`.retrieve` will cycle through those
            endpoints for each call.
        verify_cert : bool
            Whether or not SSL certificate verification should enforced.

        """
        self._session = requests.Session()
        self._verify_cert = verify_cert
        self._retry = Retry(  # type: ignore
            total=10, read=10, connect=10, status=10, backoff_factor=0.5
        )
        self._adapter = requests.adapters.HTTPAdapter(max_retries=self._retry)
        self._session.mount("https://", self._adapter)

        for endpoint in endpoints:
            if not endpoint[-1] == "/":
                endpoint += "/"
        logger.debug(f"New DocMeta session with endpoints {endpoints}")
        self._endpoints = cycle(endpoints)

    @property
    def endpoint(self) -> str:
        """Get a metadata endpoint."""
        logger.debug("get next endpoint")
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
        if not document_id:  # This could use further elaboration.
            raise ValueError("Invalid value for document_id")

        try:
            target = urljoin(self.endpoint, "/docmeta/")
            target = urljoin(target, document_id)
            logger.debug(
                f"{document_id}: retrieve metadata from {target} with SSL"
                f" verify {self._verify_cert}"
            )
            response = requests.get(
                target,
                verify=self._verify_cert,
                headers={"User-Agent": "arXiv/system"},
            )
        except requests.exceptions.SSLError as ex:
            logger.error("SSLError: %s", ex)
            raise SecurityException("SSL failed: %s" % ex) from ex
        except requests.exceptions.ConnectionError as ex:
            logger.error("ConnectionError: %s", ex)
            raise ConnectionFailed(
                "Could not connect to metadata service: %s" % ex
            ) from ex

        if response.status_code not in [
            HTTPStatus.OK,
            HTTPStatus.PARTIAL_CONTENT,
        ]:
            logger.error("Request failed: %s", response.content)
            raise RequestFailed(
                "%s: failed with %i: %s"
                % (document_id, response.status_code, response.content)
            )
        logger.debug(f"{document_id}: response OK")
        try:
            data = DocMeta(**response.json())  # type: ignore
            # See https://github.com/python/mypy/issues/3937
        except json.decoder.JSONDecodeError as ex:
            logger.error("JSONDecodeError: %s", ex)
            raise BadResponse(
                "%s: could not decode response: %s" % (document_id, ex)
            ) from ex
        logger.debug(f"{document_id}: response decoded; done!")
        return data

    def bulk_retrieve(self, document_ids: List[str]) -> List[DocMeta]:
        """
        Retrieve metadata for an arXiv paper.

        Parameters
        ----------
        document_ids : List[str]

        Returns
        -------
        dict

        Raises
        ------
        IOError
        ValueError
        """
        if not document_ids:  # This could use further elaboration.
            raise ValueError("Invalid value for document_ids")

        query_string = "/docmeta_bulk?" + "&".join(
            f"id={document_id}" for document_id in document_ids
        )

        try:
            target = urljoin(self.endpoint, query_string)
            logger.debug(
                f"{document_ids}: retrieve metadata from {target} with SSL"
                f" verify {self._verify_cert}"
            )
            response = self._session.get(target, verify=self._verify_cert)
        except requests.exceptions.SSLError as ex:
            logger.error("SSLError: %s", ex)
            raise SecurityException("SSL failed: %s" % ex) from ex
        except requests.exceptions.ConnectionError as ex:
            logger.error("ConnectionError: %s", ex)
            raise ConnectionFailed(
                "Could not connect to metadata service: %s" % ex
            ) from ex

        if response.status_code not in [
            HTTPStatus.OK,
            HTTPStatus.PARTIAL_CONTENT,
        ]:
            logger.error("Request failed: %s", response.content)
            raise RequestFailed(
                "%s: failed with %i: %s"
                % (document_ids, response.status_code, response.content)
            )
        logger.debug(f"{document_ids}: response OK")
        try:
            resp = response.json()  # A list with metadata for each paper.
            data: List[DocMeta]
            data = [DocMeta(**value) for value in resp]  # type: ignore
        except json.decoder.JSONDecodeError as ex:
            logger.error("JSONDecodeError: %s", ex)
            raise BadResponse(
                "%s: could not decode response: %s" % (document_ids, ex)
            ) from ex
        logger.debug(f"{document_ids}: response decoded; done!")
        return data


def init_app(app: object = None) -> None:
    """Set default configuration parameters for an application instance."""
    config = get_application_config(app)
    config.setdefault("METADATA_ENDPOINT", "https://arxiv.org/")
    config.setdefault("METADATA_VERIFY_CERT", "True")


def get_session(app: object = None) -> DocMetaSession:
    """Get a new session with the docmeta endpoint."""
    config = get_application_config(app)
    endpoint = config.get("METADATA_ENDPOINT", "https://arxiv.org/")
    verify_cert = bool(
        ast.literal_eval(config.get("METADATA_VERIFY_CERT", "True"))
    )
    if "," in endpoint:
        return DocMetaSession(*(endpoint.split(",")), verify_cert=verify_cert)
    return DocMetaSession(endpoint, verify_cert=verify_cert)


def current_session() -> DocMetaSession:
    """Get/create :class:`.DocMetaSession` for this context."""
    g = get_application_global()
    if not g:
        return get_session()
    elif "docmeta" not in g:
        g.docmeta = get_session()  # type: ignore
    return g.docmeta  # type: ignore


@wraps(DocMetaSession.retrieve)
def retrieve(document_id: str) -> DocMeta:
    """Retrieve an arxiv document by id."""
    return current_session().retrieve(document_id)


@wraps(DocMetaSession.bulk_retrieve)
def bulk_retrieve(document_ids: List[str]) -> List[DocMeta]:
    """Retrieve an arxiv document by id."""
    return current_session().bulk_retrieve(document_ids)
