"""Provides a record processor for MetadataIsAvailable notifications."""
from typing import Dict, List

import json
import os
from typing import List, Any, Optional
from arxiv.base import logging
from search.services import metadata, index
from search.process import transform
from search.domain import DocMeta, Document, asdict
from .base import BaseConsumer

logger = logging.getLogger(__name__)
logger.propagate = False


class DocumentFailed(RuntimeError):
    """Raised when an arXiv paper could not be added to the search index."""


class IndexingFailed(RuntimeError):
    """Raised when indexing failed such that future success is unlikely."""


class MetadataRecordProcessor(BaseConsumer):
    """Consumes ``MetadataIsAvailable`` notifications, updates the index."""

    MAX_ERRORS = 5
    """Max number of individual document failures before aborting entirely."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize exception counter."""
        cache_dir = kwargs.pop('cache_dir', None)
        super(MetadataRecordProcessor, self).__init__(*args, **kwargs)  # type: ignore
        self._error_count = 0
        self._cache: Optional[str] = None
        if cache_dir:
            self.init_cache(cache_dir)

    def init_cache(self, cache_dir: str) -> None:
        """Configure the processor to use a local cache for docmeta."""
        if not os.path.exists(cache_dir):
            raise ValueError(f'cache_dir does not exist: {cache_dir}')
        self._cache = cache_dir

    def _from_cache(self, arxiv_id: str) -> DocMeta:
        """
        Get the docmeta document from a local cache, if available.

        Parameters
        ----------
        arxiv_id : str

        Returns
        -------
        :class:`.DocMeta`

        Raises
        ------
        RuntimeError
            Raised when the cache is not available, or the document could not
            be found in the cache.

        """
        if not self._cache:
            raise RuntimeError('Cache not set')

        fname = '%s.json' % arxiv_id.replace('/', '_')
        cache_path = os.path.join(self._cache, fname)
        if not os.path.exists(cache_path):
            raise RuntimeError('No cached document')

        with open(cache_path) as f:
            data: dict = json.load(f)
            return DocMeta(**data)  # type: ignore
            # See https://github.com/python/mypy/issues/3937

    def _to_cache(self, arxiv_id: str, docmeta: DocMeta) -> None:
        """
        Add a document to the local cache, if available.

        Parameters
        ----------
        arxiv_id : str
        docmeta : :class:`.DocMeta`

        Raises
        ------
        RuntimeError
            Raised when the cache is not available, or the document could not
            be added to the cache.

        """
        if not self._cache:
            raise RuntimeError('Cache not set')
        fname = '%s.json' % arxiv_id.replace('/', '_')
        cache_path = os.path.join(self._cache, fname)
        try:
            with open(cache_path, 'w') as f:
                json.dump(asdict(docmeta), f)
        except Exception as e:
            raise RuntimeError(str(e)) from e

    # TODO: bring McCabe index down.
    def _get_metadata(self, arxiv_id: str) -> DocMeta:
        """
        Retrieve metadata from the :mod:`.metadata` service.

        Parameters
        ----------
        arxiv_id : str
            Am arXiv identifier, with or without a version affix.

        Returns
        -------
        :class:`.DocMeta`
            Metadata for the arXiv paper.

        Raises
        ------
        DocumentFailed
            Indexing of the document failed. This may have no bearing on the
            success of subsequent papers.
        IndexingFailed
            Indexing of the document failed in a way that indicates recovery
            is unlikely for subsequent papers.

        """
        logger.debug(f'{arxiv_id}: get metadata')
        try:
            return self._from_cache(arxiv_id)
        except Exception as e:  # Low tolerance for failure,
            rsn = str(e)
            logger.debug(f'{arxiv_id}: could not retrieve from cache: {rsn}')

        try:
            logger.debug(f'{arxiv_id}: requesting metadata')
            docmeta: DocMeta = metadata.retrieve(arxiv_id)
        except metadata.ConnectionFailed as e:
            # The metadata service will retry bad responses, but not connection
            # errors. Sometimes it just takes another try, so why not.
            logger.warning(f'{arxiv_id}: first attempt failed, retrying')
            try:
                docmeta = metadata.retrieve(arxiv_id)
            except metadata.ConnectionFailed as e:
                # Things really are looking bad. There is no need to keep
                # trying with subsequent records, so let's abort entirely.
                logger.error(f'{arxiv_id}: second attempt failed, giving up')
                raise IndexingFailed(
                    'Indexing failed; metadata endpoint could not be reached.'
                ) from e
        except metadata.RequestFailed as e:
            logger.error(f'{arxiv_id}: request failed')
            raise DocumentFailed('Request to metadata service failed') from e
        except metadata.BadResponse as e:
            logger.error(f'{arxiv_id}: bad response from metadata service')
            raise DocumentFailed('Bad response from metadata service') from e
        except Exception as e:
            logger.error(f'{arxiv_id}: unhandled error, metadata service: {e}')
            raise IndexingFailed('Unhandled exception') from e

        try:
            self._to_cache(arxiv_id, docmeta)
        except Exception as e:
            rsn = str(e)
            logger.debug(f'{arxiv_id}: could not add to cache: {rsn}')

        return docmeta

    def _get_bulk_metadata(self, arxiv_ids: List[str]) -> Dict[str,DocMeta]:
        """
        Retrieve metadata from the :mod:`.metadata` service for multiple documents.

        Parameters
        ----------
        arxiv_id : str
            Am arXiv identifier, with or without a version affix.

        Returns
        -------
        Dict[str, :class:`.DocMeta`]
            A dictionary containing arxiv_ids as keys and DocMeta objects as values.

        Raises
        ------
        DocumentFailed
            Indexing of the document failed. This may have no bearing on the
            success of subsequent papers.
        IndexingFailed
            Indexing of the document failed in a way that indicates recovery
            is unlikely for subsequent papers.

        """
        logger.debug(f'{arxiv_ids}: get bulk metadata')
        md: Dict[str,DocMeta] = {} # to store all metadata

        # First attempt to retrieve existing metadata from the cache
        for arxiv_id in arxiv_ids:
            try:
                md[arxiv_id] = self._from_cache(arxiv_id)
            except Exception as e:  # Low tolerance for failure,
                rsn = str(e)
                logger.debug(f'{arxiv_id}: could not retrieve from cache: {rsn}')
        
        # Then retrieve those not in cache
        to_retrieve = [arxiv_id for arxiv_id in arxiv_ids if arxiv_id not in md.keys()]
        if to_retrieve:
            try:
                logger.debug(f'{arxiv_ids}: requesting bulk metadata')
                md.update(metadata.bulk_retrieve(to_retrieve))
            except metadata.ConnectionFailed as e:
                # The metadata service will retry bad responses, but not connection
                # errors. Sometimes it just takes another try, so why not.
                logger.warning(f'{arxiv_ids}: first attempt failed, retrying')
                try:
                    md.update(metadata.bulk_retrieve(to_retrieve))
                except metadata.ConnectionFailed as e:
                    # Things really are looking bad. There is no need to keep
                    # trying with subsequent records, so let's abort entirely.
                    logger.error(f'{arxiv_ids}: second attempt failed, giving up')
                    raise IndexingFailed(
                        'Indexing failed; metadata endpoint could not be reached.'
                    ) from e
            except metadata.RequestFailed as e:
                logger.error(f'{arxiv_ids}: request failed')
                raise DocumentFailed('Request to metadata service failed') from e
            except metadata.BadResponse as e:
                logger.error(f'{arxiv_ids}: bad response from metadata service')
                raise DocumentFailed('Bad response from metadata service') from e
            except Exception as e:
                logger.error(f'{arxiv_ids}: unhandled error, metadata service: {e}')
                raise IndexingFailed('Unhandled exception') from e

        # cache all new entries
        to_cache = [arxiv_id for arxiv_id in md.keys()
                        if arxiv_id.split('v')[0] in to_retrieve]
        for arxiv_id in to_cache:
            try:
                self._to_cache(arxiv_id, md[arxiv_id])
            except Exception as e:
                rsn = str(e)
                logger.debug(f'{arxiv_id}: could not add to cache: {rsn}')

        return md


    @staticmethod
    def _transform_to_document(docmeta: DocMeta) -> Document:
        """
        Transform paper :class:`.DocMeta` to a search :class:`.Document`.

        Parameters
        ----------
        docmeta : :class:`DocMeta`
            Metadata for an arXiv paper.

        Returns
        -------
        :class:`.Document`
            A search document ready for indexing.

        Raises
        ------
        DocumentFailed
            Indexing of the document failed. This may have no bearing on the
            success of subsequent papers.

        """
        try:
            document = transform.to_search_document(docmeta)
        except Exception as e:
            # At the moment we don't have any special exceptions.
            logger.error('unhandled exception during transform: %s', e)
            raise DocumentFailed('Could not transform document') from e

        return document

    @staticmethod
    def _add_to_index(document: Document) -> None:
        """
        Add a :class:`.Document` to the search index.

        Parameters
        ----------
        document : :class:`.Document`

        Raises
        ------
        IndexingFailed
            Indexing of the document failed in a way that indicates recovery
            is unlikely for subsequent papers.

        """
        try:
            index.add_document(document)
        except index.IndexConnectionError as e:
            # Let's try once more before giving up entirely.
            try:
                index.add_document(document)
            except index.IndexConnectionError as e:   # Nope, not happening.
                raise IndexingFailed('Could not index document') from e
        except Exception as e:
            logger.error(f'Unhandled exception from index service: {e}')
            raise IndexingFailed('Unhandled exception') from e

    @staticmethod
    def _bulk_add_to_index(documents: List[Document]) -> None:
        """
        Add :class:`.Document` to the search index.

        Parameters
        ----------
        documents : :class:`.Document`

        Raises
        ------
        IndexingFailed
            Indexing of the document failed in a way that indicates recovery
            is unlikely for subsequent papers.

        """
        try:
            index.bulk_add_documents(documents)
        except index.IndexConnectionError as e:
            # Let's try once more before giving up entirely.
            try:
                index.bulk_add_documents(documents)
            except index.IndexConnectionError as e:   # Nope, not happening.
                logger.error(f'Could not bulk index documents: {e}')
                raise IndexingFailed('Could not bulk index documents') from e
        except Exception as e:
            logger.error(f'Unhandled exception from index service: {e}')
            raise IndexingFailed('Unhandled exception') from e

    def index_paper(self, arxiv_id: str) -> None:
        """
        Index a single paper, including its previous versions.

        Parameters
        ----------
        arxiv_id : str
            A **versionless** arXiv e-print identifier.

        """
        self.index_papers([arxiv_id])

    def index_papers(self, arxiv_ids: List[str]) -> None:
        """
        Index multiple papers, including their previous versions.

        Parameters
        ----------
        arxiv_ids : List[str]
            A list of **versionless** arXiv e-print identifiers.

        Raises
        ------
        DocumentFailed
            Indexing of the documents failed. This may have no bearing on the
            success of subsequent papers.
        IndexingFailed
            Indexing of the documents failed in a way that indicates recovery
            is unlikely for subsequent papers.

        """
        try:
            documents = []
            md = self._get_bulk_metadata(arxiv_ids)
            for arxiv_id in md:
                logger.debug(f'{arxiv_id}: get metadata')
                docmeta = md[arxiv_id]
                logger.debug(f'{arxiv_id}: transform to indexable document')
                document = MetadataRecordProcessor._transform_to_document(
                    docmeta
                )
                if 'v' in arxiv_id:
                    document.id = arxiv_id
                documents.append(document)

            logger.debug('add to index in bulk')
            MetadataRecordProcessor._bulk_add_to_index(documents)
        except (DocumentFailed, IndexingFailed) as e:
            # We just pass these along so that process_record() can keep track.
            logger.debug(f'{arxiv_ids}: Document failed: {e}')
            raise e

    def process_record(self, record: dict) -> None:
        """
        Call for each record that is passed to process_records.

        Parameters
        ----------
        data : bytes
        partition_key : bytes
        sequence_number : int
        sub_sequence_number : int

        Raises
        ------
        IndexingFailed
            Indexing of the document failed in a way that indicates recovery
            is unlikely for subsequent papers, or too many individual
            documents failed.

        """
        logger.info(f'Processing record {record["SequenceNumber"]}')
        if self._error_count > self.MAX_ERRORS:
            raise IndexingFailed('Too many errors')

        try:
            deserialized = json.loads(record['Data'].decode('utf-8'))
        except json.decoder.JSONDecodeError as e:
            logger.error("Error while deserializing data %s", e)
            logger.error("Data payload: %s", record['Data'])
            raise DocumentFailed('Could not deserialize record data')
            # return   # Don't bring down the whole batch.

        try:
            arxiv_id: str = deserialized.get('document_id')
            self.index_paper(arxiv_id)
        except DocumentFailed as e:
            logger.debug(f'{arxiv_id}: failed to index document')
            self._error_count += 1
        except IndexingFailed as e:
            logger.error(f'Indexing failed: {e}')
            raise
