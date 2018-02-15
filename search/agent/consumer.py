"""Provides a record processor for MetadataIsAvailable notifications."""

import json
import time
import os
from search import logging
from search.services import metadata, index
from search.process import transform
from search.domain import DocMeta, Document
from .base import BaseRecordProcessor, ProcessRecordsInput

logger = logging.getLogger(__name__)


class DocumentFailed(RuntimeError):
    """Raised when an arXiv paper could not be added to the search index."""


class IndexingFailed(RuntimeError):
    """Raised when indexing failed such that future success is unlikely."""


class MetadataRecordProcessor(BaseRecordProcessor):
    """Consumes ``MetadataIsAvailable`` notifications, updates the index."""

    MAX_ERRORS = 5
    """Max number of individual document failures before aborting entirely."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize exception counter."""
        super(MetadataRecordProcessor, self).__init__(*args, **kwargs) # type: ignore
        self._error_count = 0
        self._cache: str

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
            return DocMeta(json.load(f).items())

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
                json.dump(dict(docmeta.items()), f)
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
            docmeta = metadata.retrieve(arxiv_id)

        # TODO: use a context manager for retry?
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
            logger.error(f'{arxiv_id}: unhandled error from metadata service')
            raise IndexingFailed('Unhandled exception') from e

        try:
            self._to_cache(arxiv_id, docmeta)
        except Exception as e:
            rsn = str(e)
            logger.debug(f'{arxiv_id}: could not add to cache: {rsn}')

        return docmeta

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
        DocumentFailed
            Indexing of the document failed. This may have no bearing on the
            success of subsequent papers.
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
            logger.error('unhandled exception from index service')
            raise IndexingFailed('Unhandled exception') from e

    # TODO: update this based on the final verdict on submission/announcement
    #  dates.
    def index_paper(self, arxiv_id: str) -> Document:
        """
        Index a paper, including its previous versions.

        Parameters
        ----------
        arxiv_id : str
            A **versionless** arXiv e-print identifier.

        Raises
        ------
        DocumentFailed
            Indexing of the document failed. This may have no bearing on the
            success of subsequent papers.
        IndexingFailed
            Indexing of the document failed in a way that indicates recovery
            is unlikely for subsequent papers.
        """
        try:
            docmeta = self._get_metadata(arxiv_id)
            document = MetadataRecordProcessor._transform_to_document(docmeta)

            current_version = docmeta.version
            logger.debug(f'current version is {current_version}')
            if current_version is not None and current_version > 1:
                for version in range(1, current_version):
                    ver_docmeta = self._get_metadata(f'{arxiv_id}v{version}')
                    ver_document =\
                        MetadataRecordProcessor._transform_to_document(
                            ver_docmeta)

                    # The earlier versions are here primarily to respond to
                    # queries that explicitly specify the version number.
                    ver_document.is_current = False

                    # Add a reference to the most recent version.
                    ver_document.latest = f'{arxiv_id}v{current_version}'
                    # Set the primary document ID to the version-specied
                    # arXiv identifier, to avoid clobbering the latest version.
                    ver_document.id = f'{arxiv_id}v{version}'
                    MetadataRecordProcessor._add_to_index(ver_document)

            # Finally, index the most recent version.
            document.is_current = True
            MetadataRecordProcessor._add_to_index(document)
        except (DocumentFailed, IndexingFailed) as e:
            # We just pass these along so that process_record() can keep track.
            # TODO: Ensure this is the correct behavior.
            raise e

        return document

    # TODO: verify notification payload on MetadataIsAvailable stream.
    def process_record(self, data: bytes, partition_key: bytes,
                       sequence_number: int, sub_sequence_number: int) -> None:
        """
        Called for each record that is passed to process_records.

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
        if self._error_count > self.MAX_ERRORS:
            raise IndexingFailed('Too many errors')

        try:
            deserialized = json.loads(data.decode('utf-8'))
        except Exception as e:
            logger.error("Error while deserializing data: %s", e)
            logger.error("Data payload: %s", data)
            return   # Don't bring down the whole batch.

        try:
            arxiv_id: str = deserialized.get('document_id')
            self.index_paper(arxiv_id)
        except DocumentFailed as e:
            logger.debug(f'{arxiv_id}: failed to index document')
            self._error_count += 1
        except IndexingFailed as e:
            raise
