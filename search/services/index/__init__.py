"""
Provides integration with an ElasticSearch cluster.

The primary entrypoint to this module is :func:`.search`, which handles
:class:`search.domain.Query` instances passed by controllers, and returns a
:class:`.DocumentSet` containing search results. :func:`.get_document` is
available for future use, e.g. as part of a search API.

In addition, :func:`.add_document` and :func:`.bulk_add_documents` are provided
for indexing (e.g. by the
:mod:`search.agent.consumer.MetadataRecordProcessor`).
"""


# Start monkeypatch of elasticsearch-py's search(), use POST not GET
#   due to GCP load balancers rejecting any GET requests with a body

import elasticsearch.client
from typing import Any

def search2(self: Any, index: Any=None, doc_type: Any=None, body: Any=None, params: Any=None) -> Any:
  if params and 'from_' in params:
    params['from'] = params.pop('from_')
  if doc_type and not index:
    index = '_all'
  tmppath =  elasticsearch.client.utils._make_path(index, doc_type, '_search')
  return self.transport.perform_request('POST', tmppath, params=params, body=body)

elasticsearch.client.Elasticsearch.search = search2

#
# End monkeypatch


__all__ = ["Q", "SearchSession"]

import json
import warnings
from contextlib import contextmanager
from typing import Any, Optional, List, Generator, Dict

import urllib3
from flask import current_app
from elasticsearch import (
    Elasticsearch,
    ElasticsearchException,
    SerializationError,
    TransportError,
    helpers,
)
from elasticsearch.connection import Urllib3HttpConnection
from elasticsearch.helpers import BulkIndexError
from elasticsearch_dsl import Search, Q

from arxiv.base import logging
from arxiv.integration.meta import MetaIntegration
from search.context import get_application_config, get_application_global
from search.domain import (
    Document,
    DocumentSet,
    Query,
    AdvancedQuery,
    SimpleQuery,
    APIQuery,
    ClassicAPIQuery,
)

from search.services.index.exceptions import (
    QueryError,
    IndexConnectionError,
    DocumentNotFound,
    IndexingError,
    OutsideAllowedRange,
    MappingError,
)
from search.services.index.util import MAX_RESULTS
from search.services.index.advanced import advanced_search
from search.services.index.simple import simple_search
from search.services.index.api import api_search
from search.services.index.classic_api import classic_search
from search.services.index import highlighting
from search.services.index import results

logger = logging.getLogger(__name__)

# Disable the Elasticsearch logger. When enabled, the Elasticsearch logger
# dumps entire Tracebacks prior to propagating exceptions. Thus we end up with
# tracebacks in the logs even for handled exceptions.
logging.getLogger("elasticsearch").disabled = True


ALL_SEARCH_FIELDS = [
    "author",
    "title",
    "abstract",
    "comments",
    "journal_ref",
    "acm_class",
    "msc_class",
    "report_num",
    "paper_id",
    "doi",
    "orcid",
    "author_id",
]


@contextmanager
def handle_es_exceptions() -> Generator:
    """Handle common ElasticSearch-related exceptions."""
    try:
        yield
    except TransportError as ex:
        if ex.error == "resource_already_exists_exception":
            logger.debug("Index already exists; move along")
            return
        elif ex.error == "mapper_parsing_exception":
            logger.error("ES mapper_parsing_exception: %s", ex.info)
            logger.debug(str(ex.info))
            raise MappingError("Invalid mapping: %s" % str(ex.info)) from ex
        elif ex.error == "index_not_found_exception":
            logger.error("ES index_not_found_exception: %s", ex.info)
            SearchSession.current_session().create_index()
        elif ex.error == "parsing_exception":
            logger.error("ES parsing_exception: %s", ex.info)
            raise QueryError(ex.info) from ex
        elif ex.error == "search_phase_execution_exception":
            logger.error("ES execution_exception: %s", ex.info)
            raise QueryError(ex.info) from ex
        elif ex.status_code == 404:
            logger.error("Caught NotFoundError: %s", ex)
            raise DocumentNotFound("No such document")
        logger.error("Problem communicating with ES: %s" % ex.error)
        raise IndexConnectionError(
            "Problem communicating with ES: %s" % ex.error
        ) from ex
    except SerializationError as ex:
        logger.error("SerializationError: %s", ex)
        raise IndexingError("Problem serializing document: %s" % ex) from ex
    except BulkIndexError as ex:
        logger.error("BulkIndexError: %s", ex)
        raise IndexingError("Problem with bulk indexing: %s" % ex) from ex
    except Exception as ex:
        logger.error("Unhandled exception: %s" % ex)
        raise


class SearchSession(metaclass=MetaIntegration):
    """Encapsulates session with Elasticsearch host."""

    def __init__(
        self,
        host: str,
        index: str,
        port: int = 9200,
        scheme: str = "http",
        user: Optional[str] = None,
        password: Optional[str] = None,
        mapping: Optional[str] = None,
        verify: bool = True,
        **extra: Any,
    ) -> None:
        """
        Initialize the connection to Elasticsearch.

        Parameters
        ----------
        host : str
        index : str
        port : int
            Default: 9200
        scheme: str
            Default: 'http'
        user: str
            Default: None
        password: str
            Default: None

        Raises
        ------
        IndexConnectionError
            Problem communicating with Elasticsearch host.


        """
        self.index = index
        self.mapping = mapping
        self.doc_type = "document"
        use_ssl = True if scheme == "https" else False
        http_auth = "%s:%s" % (user, password) if user else None

        self.conn_params = {
            "host": host,
            "port": port,
            "use_ssl": use_ssl,
            "http_auth": http_auth,
            "verify_certs": verify,
        }
        self.conn_extra = extra
        if not use_ssl:
            warnings.warn(f"TLS is disabled, using port {port}")
        if host == "localhost":
            warnings.warn(f"Using ES at {host}:{port}; not OK for production")

    def new_connection(self) -> Elasticsearch:
        """Create a new :class:`.Elasticsearch` connection."""
        logger.debug("init ES session with %s", self.conn_params)
        try:
            es = Elasticsearch(
                [self.conn_params],
                connection_class=Urllib3HttpConnection,
                **self.conn_extra,
            )
        except ElasticsearchException as ex:
            logger.error("ElasticsearchException: %s", ex)
            raise IndexConnectionError(
                "Could not initialize ES session: %s" % ex
            ) from ex
        return es

    def _base_search(self) -> Search:
        return Search(using=self.es, index=self.index)

    # FIXME: Return type.
    def _load_mapping(self) -> Dict[Any, Any]:
        if not self.mapping or not isinstance(self.mapping, str):
            raise IndexingError("Mapping not set")
        with open(self.mapping) as f:
            mappings: dict = json.load(f)
        return mappings

    @property
    def es(self) -> Elasticsearch:
        """
        Get or create the current :class:`.Elasticsearch` connection.

        The :class:`.Elasticsearch` connection is threadsafe, so we can reuse
        the same connection across the whole app. See
        `https://elasticsearch-py.readthedocs.io/en/master/#thread-safety`_.

        We use the `extensions` lookup on the Flask app to store the
        connection.
        """
        if current_app:
            if "elasticsearch" not in current_app.extensions:
                current_app.extensions["elasticsearch"] = self.new_connection()
            return current_app.extensions["elasticsearch"]
        return self.new_connection()

    def cluster_available(self) -> bool:
        """
        Determine whether or not the ES cluster is available.

        Returns
        -------
        bool

        """
        try:
            self.es.cluster.health(wait_for_status="yellow", request_timeout=1)
            return True
        except urllib3.exceptions.HTTPError as ex:
            logger.debug("Health check failed: %s", str(ex))
            return False
        except Exception as ex:
            logger.debug("Health check failed: %s", str(ex))
            return False

    def create_index(self) -> None:
        """
        Create the search index.

        Parameters
        ----------
        mappings : dict
            See
            elastic.co/guide/en/elasticsearch/reference/current/mapping.html

        """
        logger.debug('create ES index "%s"', self.index)
        with handle_es_exceptions():
            self.es.indices.create(self.index, self._load_mapping())

    def index_exists(self, index_name: str) -> bool:
        """
        Determine whether or not an index exists.

        Parameters
        ----------
        index_name : str

        Returns
        -------
        bool

        """
        with handle_es_exceptions():
            _exists: bool = self.es.indices.exists(index_name)
            return _exists

    # FIXME: Return type.
    def reindex(
        self, old_index: str, new_index: str, wait_for_completion: bool = False
    ) -> Dict[Any, Any]:
        """
        Create a new index and reindex with the current mappings.

        Creating the new index and performing the reindexing operation are two
        separate actions via the ES API. If creation of the next index
        succeeds but the request to reindex fails, no attempt is made to clean
        up. If the new index already exists, will still attempt to perform
        the reindex operation.

        Parameters
        ----------
        old_index: str
            Name of the index to copy from.
        new_index: str
            Name of the index to create and copy to.

        Returns
        -------
        dict
            Response from ElasticSearch reindex API. If `wait_for_completion`
            is False (default), should include a `task` key with a task ID
            that can be used to check the status of the reindexing operation.

        """
        logger.debug('reindex "%s" as "%s"', old_index, new_index)
        with handle_es_exceptions():
            self.es.indices.create(new_index, self._load_mapping())

        response: dict = self.es.reindex(
            {"source": {"index": old_index}, "dest": {"index": new_index}},
            wait_for_completion=wait_for_completion,
        )
        return response

    # FIXME: Return type.
    def get_task_status(self, task: str) -> Dict[Any, Any]:
        """
        Get the status of a running task in ES (e.g. reindex).

        Parameters
        ----------
        task : str
            A task ID, e.g. returned in response to an asynchronous reindexing
            request.

        Returns
        -------
        dict
            Response from ElasticSearch task API.

        """
        with handle_es_exceptions():
            response: dict = self.es.tasks.get(task)
        return response

    def add_document(self, document: Document) -> None:
        """
        Add a document to the search index.

        Uses ``paper_id_v`` as the primary identifier for the document. If the
        document is already indexed, will quietly overwrite.

        Parameters
        ----------
        document : :class:`.Document`
            Must be a valid search document, per
            ``schema/DocumentMetadata.json``.

        Raises
        ------
        :class:`.IndexConnectionError`
            Problem communicating with Elasticsearch host.
        :class:`.QueryError`
            Problem serializing ``document`` for indexing.

        """
        if not self.es.indices.exists(index=self.index):
            self.create_index()

        with handle_es_exceptions():
            ident = document["id"] if document["id"] else document["paper_id"]
            logger.debug(f"{ident}: index document")
            self.es.index(
                index=self.index,
                doc_type=self.doc_type,
                id=ident,
                body=document,
            )

    def bulk_add_documents(
        self, documents: List[Document], docs_per_chunk: int = 500
    ) -> None:
        """
        Add documents to the search index using the bulk API.

        Parameters
        ----------
        document : :class:`.Document`
            Must be a valid search document, per
            ``schema/DocumentMetadata.json``.
        docs_per_chunk: int
            Number of documents to send to ES in a single chunk
        Raises
        ------
        IndexConnectionError
            Problem communicating with Elasticsearch host.
        BulkIndexingError
            Problem serializing ``document`` for indexing.

        """
        if not self.es.indices.exists(index=self.index):
            logger.debug("index does not exist")
            self.create_index()
            logger.debug("created index")

        with handle_es_exceptions():
            actions = (
                {
                    "_index": self.index,
                    "_type": self.doc_type,
                    "_id": document["id"],
                    "_source": document,
                }
                for document in documents
            )

            helpers.bulk(
                client=self.es, actions=actions, chunk_size=docs_per_chunk
            )
            logger.debug("added %i documents to index", len(documents))

    def get_document(self, document_id: str) -> Document:
        """
        Retrieve a document from the index by ID.

        Parameters
        ----------
        doument_id : int

        Returns
        -------
        :class:`.Document`

        Raises
        ------
        IndexConnectionError
            Problem communicating with the search index.
        QueryError
            Invalid query parameters.

        """
        with handle_es_exceptions():
            record = self.es.get(
                index=self.index, doc_type=self.doc_type, id=document_id
            )

        if not record:
            logger.error("No such document: %s", document_id)
            raise DocumentNotFound("No such document")
        return results.to_document(record["_source"], highlight=False)
        # See https://github.com/python/mypy/issues/3937

    def search(self, query: Query, highlight: bool = True) -> DocumentSet:
        """
        Perform a search.

        Parameters
        ----------
        query : :class:`.Query`

        Returns
        -------
        :class:`.DocumentSet`

        Raises
        ------
        IndexConnectionError
            Problem communicating with the search index.
        QueryError
            Invalid query parameters.

        """
        # Make sure that the user is not requesting a nonexistant page.
        max_pages = int(MAX_RESULTS / query.size)
        if query.page > max_pages:
            _message = f"Requested page {query.page}, but max is {max_pages}"
            logger.error(_message)
            raise OutsideAllowedRange(_message)

        # Perform the search.
        logger.debug("got current search request %s", str(query))
        current_search = self._base_search()
        try:
            if isinstance(query, AdvancedQuery):
                current_search = advanced_search(current_search, query)
            elif isinstance(query, SimpleQuery):
                current_search = simple_search(current_search, query)
            elif isinstance(query, APIQuery):
                current_search = api_search(current_search, query)
            elif isinstance(query, ClassicAPIQuery):
                current_search = classic_search(current_search, query)
        except TypeError as ex:
            raise ex

        if highlight:
            # Highlighting is performed by Elasticsearch; here we include the
            # fields and configuration for highlighting.
            current_search = highlighting.highlight(current_search)

        if isinstance(query, APIQuery):
            current_search = current_search.extra(
                _source={"include": query.include_fields}
            )

        with handle_es_exceptions():
            # Slicing the search adds pagination parameters to the request.
            resp = current_search[query.page_start : query.page_end].execute()

        # Perform post-processing on the search results.
        return results.to_documentset(query, resp, highlight=highlight)

    def exists(self, paper_id_v: str) -> bool:
        """Determine whether a paper exists in the index."""
        with handle_es_exceptions():
            ex: bool = self.es.exists(self.index, self.doc_type, paper_id_v)
        return ex

    @classmethod
    def init_app(cls, app: object = None) -> None:
        """Set default configuration parameters for an application instance."""
        config = get_application_config(app)
        config.setdefault("ELASTICSEARCH_SERVICE_HOST", "localhost")
        config.setdefault("ELASTICSEARCH_SERVICE_PORT", "9200")
        config.setdefault("ELASTICSEARCH_INDEX", "arxiv")
        config.setdefault("ELASTICSEARCH_USER", None)
        config.setdefault("ELASTICSEARCH_PASSWORD", None)
        config.setdefault(
            "ELASTICSEARCH_MAPPING", "mappings/DocumentMapping.json"
        )
        config.setdefault("ELASTICSEARCH_VERIFY", "true")

    @classmethod
    def get_session(cls, app: object = None) -> "SearchSession":
        """Get a new session with the search index."""
        config = get_application_config(app)
        host = config.get("ELASTICSEARCH_SERVICE_HOST", "localhost")
        port = config.get("ELASTICSEARCH_SERVICE_PORT", "9200")
        scheme = config.get(
            "ELASTICSEARCH_SERVICE_PORT_%s_PROTO" % port, "http"
        )
        index = config.get("ELASTICSEARCH_INDEX", "arxiv")
        verify = config.get("ELASTICSEARCH_VERIFY", "true") == "true"
        user = config.get("ELASTICSEARCH_USER", None)
        password = config.get("ELASTICSEARCH_PASSWORD", None)
        mapping = config.get(
            "ELASTICSEARCH_MAPPING", "mappings/DocumentMapping.json"
        )
        return cls(
            host, index, port, scheme, user, password, mapping, verify=verify
        )

    @classmethod
    def current_session(cls) -> "SearchSession":
        """Get/create :class:`.SearchSession` for this context."""
        g = get_application_global()
        if not g:
            return cls.get_session()
        if "search" not in g:
            g.search = cls.get_session()  # type: ignore
        return g.search  # type: ignore


def ok() -> bool:
    """Health check."""
    try:
        SearchSession.current_session().cluster_available()
    except Exception:  # TODO: be more specific.
        return False
    return True
