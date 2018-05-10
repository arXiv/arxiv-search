"""
Provides integration with an ElasticSearch cluster.

The primary entrypoint to this module is :func:`.search`, which handles
:class:`search.domain.Query` instances passed by controllers, and returns a
:class:`.DocumentSet` containing search results. :func:`.get_document` is
available for future use, e.g. as part of a search API.

In addition, :func:`.add_document` and :func:`.bulk_add_documents` are provided
for indexing (e.g. by the
:mod:`search.agent.consumer.MetadataRecordProcessor`).

:class:`.SearchSession` encapsulates configuration parameters and a connection
to the Elasticsearch cluster for thread-safety. The functions mentioned above
load the appropriate instance of :class:`.SearchSession` depending on the
context of the request.
"""

import json
import urllib3
from contextlib import contextmanager
from typing import Any, Optional, Tuple, Union, List, Generator
from functools import reduce, wraps
from operator import ior
from elasticsearch import Elasticsearch, ElasticsearchException, \
                          SerializationError, TransportError, NotFoundError, \
                          helpers
from elasticsearch.connection import Urllib3HttpConnection
from elasticsearch.helpers import BulkIndexError

from elasticsearch_dsl import Search, Q

from search.context import get_application_config, get_application_global
from arxiv.base import logging
from search.domain import Document, DocumentSet, Query, AdvancedQuery, \
    SimpleQuery, asdict

from .exceptions import QueryError, IndexConnectionError, DocumentNotFound, \
    IndexingError, OutsideAllowedRange, MappingError
from .util import MAX_RESULTS
from .advanced import advanced_search
from .simple import simple_search
from .highlighting import highlight
from . import results

logger = logging.getLogger(__name__)

# Disable the Elasticsearch logger. When enabled, the Elasticsearch logger
# dumps entire Tracebacks prior to propagating exceptions. Thus we end up with
# tracebacks in the logs even for handled exceptions.
logging.getLogger('elasticsearch').disabled = True


ALL_SEARCH_FIELDS = ['author', 'title', 'abstract', 'comments', 'journal_ref',
                     'acm_class', 'msc_class', 'report_num', 'paper_id', 'doi',
                     'orcid', 'author_id']


@contextmanager
def handle_es_exceptions() -> Generator:
    """Handle common ElasticSearch-related exceptions."""
    try:
        yield
    except TransportError as e:
        if e.error == 'resource_already_exists_exception':
            logger.debug('Index already exists; move along')
            return
        elif e.error == 'mapper_parsing_exception':
            logger.error('ES mapper_parsing_exception: %s', e.info)
            logger.debug(str(e.info))
            raise MappingError('Invalid mapping: %s' % str(e.info)) from e
        elif e.error == 'index_not_found_exception':
            logger.error('ES index_not_found_exception: %s', e.info)
            create_index()
        elif e.error == 'parsing_exception':
            logger.error('ES parsing_exception: %s', e.info)
            raise QueryError(e.info) from e
        logger.error('Problem communicating with ES: %s' % e.error)
        raise IndexConnectionError(
            'Problem communicating with ES: %s' % e.error
        ) from e
    except SerializationError as e:
        logger.error("SerializationError: %s", e)
        raise IndexingError('Problem serializing document: %s' % e) from e
    except BulkIndexError as e:
        logger.error("BulkIndexError: %s", e)
        raise IndexingError('Problem with bulk indexing: %s' % e) from e
    except Exception as e:
        logger.error('Unhandled exception: %s')
        raise


class SearchSession(object):
    """Encapsulates session with Elasticsearch host."""

    def __init__(self, host: str, index: str, port: int=9200,
                 scheme: str='http', user: Optional[str]=None,
                 password: Optional[str]=None, mapping: Optional[str]=None,
                 verify: bool=True, **extra: Any) -> None:
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
        self.doc_type = 'document'
        use_ssl = True if scheme == 'https' else False
        http_auth = '%s:%s' % (user, password) if user else None

        logger.debug(
            f'init ES session for index {index} at {scheme}://{host}:{port}'
            f' with verify={verify}, ssl={use_ssl}, and user={user}'
        )

        try:
            self.es = Elasticsearch([{'host': host, 'port': port,
                                      'use_ssl': use_ssl,
                                      'http_auth': http_auth,
                                      'verify_certs': verify}],
                                    connection_class=Urllib3HttpConnection,
                                    **extra)
        except ElasticsearchException as e:
            logger.error('ElasticsearchException: %s', e)
            raise IndexConnectionError(
                'Could not initialize ES session: %s' % e
            ) from e

    def _base_search(self) -> Search:
        return Search(using=self.es, index=self.index)

    def _load_mapping(self) -> dict:
        if not self.mapping or type(self.mapping) is not str:
            raise IndexingError('Mapping not set')
        with open(self.mapping) as f:
            mappings: dict = json.load(f)
        return mappings

    def cluster_available(self) -> bool:
        """
        Determine whether or not the ES cluster is available.

        Returns
        -------
        bool
        """
        try:
            self.es.cluster.health(wait_for_status='yellow', request_timeout=1)
            return True
        except urllib3.exceptions.HTTPError as e:
            logger.debug('Health check failed: %s', str(e))
            return False
        except Exception as e:
            logger.debug('Health check failed: %s', str(e))
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

    def reindex(self, old_index: str, new_index: str,
                wait_for_completion: bool = False) -> dict:
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

        response: dict = self.es.reindex({
            "source": {"index": old_index},
            "dest": {"index": new_index}
        }, wait_for_completion=wait_for_completion)
        return response

    def get_task_status(self, task: str) -> dict:
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
            Must be a valid search document, per ``schema/Document.json``.

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
            ident = document.id if document.id else document.paper_id
            logger.debug(f'{ident}: index document')
            self.es.index(index=self.index, doc_type=self.doc_type,
                          id=ident, body=document)

    def bulk_add_documents(self, documents: List[Document],
                           docs_per_chunk: int = 500) -> None:
        """
        Add documents to the search index using the bulk API.

        Parameters
        ----------
        document : :class:`.Document`
            Must be a valid search document, per ``schema/Document.json``.
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
            logger.debug('index does not exist')
            self.create_index()
            logger.debug('created index')

        with handle_es_exceptions():
            actions = ({
                '_index': self.index,
                '_type': self.doc_type,
                '_id': document.id,
                '_source': asdict(document)
            } for document in documents)

            helpers.bulk(client=self.es, actions=actions,
                         chunk_size=docs_per_chunk)
            logger.debug('added %i documents to index', len(documents))

    def get_document(self, document_id: int) -> Document:
        """
        Retrieve a document from the index by ID.

        Uses ``metadata_id`` as the primary identifier for the document.

        Parameters
        ----------
        doument_id : int
            Value of ``metadata_id`` in the original document.

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
            record = self.es.get(index=self.index, doc_type=self.doc_type,
                                 id=document_id)

        if not record:
            logger.error("No such document: %s", document_id)
            raise DocumentNotFound('No such document')
        return Document(**record['_source'])    # type: ignore
        # See https://github.com/python/mypy/issues/3937

    def search(self, query: Query) -> DocumentSet:
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
        max_pages = int(MAX_RESULTS/query.page_size)
        if query.page > max_pages:
            _message = f'Requested page {query.page}, but max is {max_pages}'
            logger.error(_message)
            raise OutsideAllowedRange(_message)

        # Perform the search.
        logger.debug('got current search request %s', str(query))
        current_search = self._base_search()
        try:
            if isinstance(query, AdvancedQuery):
                current_search = advanced_search(current_search, query)
            elif isinstance(query, SimpleQuery):
                current_search = simple_search(current_search, query)
        except TypeError as e:
            logger.error('Malformed query: %s', str(e))
            raise QueryError('Malformed query') from e

        # Highlighting is performed by Elasticsearch; here we include the
        # fields and configuration for highlighting.
        current_search = highlight(current_search)

        with handle_es_exceptions():
            # Slicing the search adds pagination parameters to the request.
            resp = current_search[query.page_start:query.page_end].execute()

        # Perform post-processing on the search results.
        return results.to_documentset(query, resp)

    def exists(self, paper_id_v: str) -> bool:
        """Determine whether a paper exists in the index."""
        with handle_es_exceptions():
            ex: bool = self.es.exists(self.index, self.doc_type, paper_id_v)
            return ex


def init_app(app: object = None) -> None:
    """Set default configuration parameters for an application instance."""
    config = get_application_config(app)
    config.setdefault('ELASTICSEARCH_HOST', 'localhost')
    config.setdefault('ELASTICSEARCH_PORT', '9200')
    config.setdefault('ELASTICSEARCH_INDEX', 'arxiv')
    config.setdefault('ELASTICSEARCH_USER', None)
    config.setdefault('ELASTICSEARCH_PASSWORD', None)
    config.setdefault('ELASTICSEARCH_MAPPING', 'mappings/DocumentMapping.json')
    config.setdefault('ELASTICSEARCH_VERIFY', 'true')


# TODO: consider making this private.
def get_session(app: object = None) -> SearchSession:
    """Get a new session with the search index."""
    config = get_application_config(app)
    host = config.get('ELASTICSEARCH_HOST', 'localhost')
    port = config.get('ELASTICSEARCH_PORT', '9200')
    scheme = config.get('ELASTICSEARCH_SCHEME', 'http')
    index = config.get('ELASTICSEARCH_INDEX', 'arxiv')
    verify = config.get('ELASTICSEARCH_VERIFY', 'true') == 'true'
    user = config.get('ELASTICSEARCH_USER', None)
    password = config.get('ELASTICSEARCH_PASSWORD', None)
    mapping = config.get('ELASTICSEARCH_MAPPING',
                         'mappings/DocumentMapping.json')
    return SearchSession(host, index, port, scheme, user, password, mapping,
                         verify=verify)


# TODO: consider making this private.
def current_session() -> SearchSession:
    """Get/create :class:`.SearchSession` for this context."""
    g = get_application_global()
    if not g:
        return get_session()
    if 'search' not in g:
        g.search = get_session()    # type: ignore
    return g.search     # type: ignore


@wraps(SearchSession.search)
def search(query: Query) -> DocumentSet:
    """Retrieve search results."""
    return current_session().search(query)


@wraps(SearchSession.add_document)
def add_document(document: Document) -> None:
    """Add Document."""
    return current_session().add_document(document)


@wraps(SearchSession.bulk_add_documents)
def bulk_add_documents(documents: List[Document]) -> None:
    """Add Documents."""
    return current_session().bulk_add_documents(documents)


@wraps(SearchSession.get_document)
def get_document(document_id: int) -> Document:
    """Retrieve arxiv document by id."""
    return current_session().get_document(document_id)


@wraps(SearchSession.cluster_available)
def cluster_available() -> bool:
    """Check whether the cluster is available."""
    return current_session().cluster_available()


@wraps(SearchSession.create_index)
def create_index() -> None:
    """Create the search index."""
    current_session().create_index()


@wraps(SearchSession.exists)
def exists(paper_id_v: str) -> bool:
    """Check whether a paper is present in the index."""
    return current_session().exists(paper_id_v)


@wraps(SearchSession.index_exists)
def index_exists(index_name: str) -> bool:
    """Check whether an index exists."""
    return current_session().index_exists(index_name)


@wraps(SearchSession.reindex)
def reindex(old_index: str, new_index: str,
            wait_for_completion: bool = False) -> dict:
    """Create a new index and reindex with the current mappings."""
    return current_session().reindex(old_index, new_index, wait_for_completion)


@wraps(SearchSession.get_task_status)
def get_task_status(task: str) -> dict:
    """Get the status of a running task in ES (e.g. reindex)."""
    return current_session().get_task_status(task)


def ok() -> bool:
    """Health check."""
    try:
        current_session()
    except Exception:    # TODO: be more specific.
        return False
    return True
