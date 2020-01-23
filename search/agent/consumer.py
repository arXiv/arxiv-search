"""Provides a record processor for MetadataIsAvailable notifications."""

import json
import os
import time
from typing import List, Any, Optional, Dict
from arxiv.base import logging
from search.services import metadata, index
from search.process import transform
from search.domain import DocMeta, Document, asdict
from arxiv.base.agent import BaseConsumer

from retry.api import retry_call

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
        self.sleep: float = kwargs.pop('sleep', 0.1)
        super(MetadataRecordProcessor, self).__init__(*args, **kwargs)  # type: ignore
        self._error_count = 0

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
        logger.debug('%s: get metadata', arxiv_id)

        try:
            docmeta: DocMeta = retry_call(metadata.retrieve, (arxiv_id,),
                                          exceptions=metadata.ConnectionFailed,
                                          tries=2)
        except metadata.ConnectionFailed as ex:
            # Things really are looking bad. There is no need to keep
            # trying with subsequent records, so let's abort entirely.
            logger.error('%s: second attempt failed, giving up', arxiv_id)
            raise IndexingFailed(
                'Indexing failed; metadata endpoint could not be reached.'
            ) from ex
        except metadata.RequestFailed as ex:
            logger.error(f'{arxiv_id}: request failed')
            raise DocumentFailed('Request to metadata service failed') from ex
        except metadata.BadResponse as ex:
            logger.error(f'{arxiv_id}: bad response from metadata service')
            raise DocumentFailed('Bad response from metadata service') from ex
        except Exception as ex:
            logger.error(f'{arxiv_id}: unhandled error, metadata service: {ex}')
            raise IndexingFailed('Unhandled exception') from ex
        return docmeta

    def _get_bulk_metadata(self, arxiv_ids: List[str]) -> List[DocMeta]:
        """
        Retrieve metadata from :mod:`.metadata` service for multiple documents.

        Parameters
        ----------
        arxiv_id : str
            Am arXiv identifier, with or without a version affix.

        Returns
        -------
        Dict[str, :class:`.DocMeta`]
            A dictionary containing arxiv_ids as keys and DocMeta objects as
            values.

        Raises
        ------
        DocumentFailed
            Indexing of the document failed. This may have no bearing on the
            success of subsequent papers.
        IndexingFailed
            Indexing of the document failed in a way that indicates recovery
            is unlikely for subsequent papers.

        """
        logger.debug('%s: get bulk metadata', arxiv_ids)
        meta: List[DocMeta]
        try:
            meta = retry_call(metadata.bulk_retrieve, (arxiv_ids,),
                              exceptions=metadata.ConnectionFailed,
                              tries=2)
        except metadata.ConnectionFailed as ex:
            # Things really are looking bad. There is no need to keep
            # trying with subsequent records, so let's abort entirely.
            logger.error('%s: second attempt failed, giving up', arxiv_ids)
            raise IndexingFailed('Metadata endpoint not available') from ex
        except metadata.RequestFailed as ex:
            logger.error('%s: request failed', arxiv_ids)
            raise DocumentFailed('Request to metadata service failed') from ex
        except metadata.BadResponse as ex:
            logger.error('%s: bad response from metadata service', arxiv_ids)
            raise DocumentFailed('Bad response from metadata service') from ex
        except Exception as ex:
            logger.error('%s: unhandled error, metadata svc: %s', arxiv_ids, ex)
            raise IndexingFailed('Unhandled exception') from ex
        return meta

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
        except Exception as ex:
            # At the moment we don't have any special exceptions.
            logger.error('unhandled exception during transform: %s', ex)
            raise DocumentFailed('Could not transform document') from ex

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
            retry_call(index.SearchSession.add_document, (document,),
                       exceptions=index.IndexConnectionError, tries=2)
        except index.IndexConnectionError as ex:
            raise IndexingFailed('Could not index document') from ex
        except Exception as ex:
            logger.error(f'Unhandled exception from index service: {ex}')
            raise IndexingFailed('Unhandled exception') from ex

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
            retry_call(index.SearchSession.bulk_add_documents, (documents,),
                       exceptions=index.IndexConnectionError, tries=2)
        except index.IndexConnectionError as ex:
            raise IndexingFailed('Could not bulk index documents') from ex
        except Exception as ex:
            logger.error(f'Unhandled exception from index service: {ex}')
            raise IndexingFailed('Unhandled exception') from ex

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
            for docmeta in self._get_bulk_metadata(arxiv_ids):
                logger.debug('%s: transform to Document', docmeta.paper_id)
                document = MetadataRecordProcessor._transform_to_document(
                    docmeta
                )
                documents.append(document)
            logger.debug('add to index in bulk')
            MetadataRecordProcessor._bulk_add_to_index(documents)
        except (DocumentFailed, IndexingFailed) as ex:
            # We just pass these along so that process_record() can keep track.
            logger.debug(f'{arxiv_ids}: Document failed: {ex}')
            raise ex

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
        time.sleep(self.sleep)
        logger.info(f'Processing record {record["SequenceNumber"]}')
        if self._error_count > self.MAX_ERRORS:
            raise IndexingFailed('Too many errors')

        try:
            deserialized = json.loads(record['Data'].decode('utf-8'))
        except json.decoder.JSONDecodeError as ex:
            logger.error("Error while deserializing data %s", ex)
            logger.error("Data payload: %s", record['Data'])
            raise DocumentFailed('Could not deserialize record data')
            # return   # Don't bring down the whole batch.

        try:
            arxiv_id: str = deserialized.get('document_id')
            self.index_paper(arxiv_id)
        except DocumentFailed as ex:
            logger.debug('%s: failed to index document: %s', arxiv_id, ex)
            self._error_count += 1
        except IndexingFailed as ex:
            logger.error('Indexing failed: %s', ex)
            raise
