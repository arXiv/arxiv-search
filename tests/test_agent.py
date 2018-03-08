"""Unit tests for :mod:`search.agent`."""

from unittest import TestCase, mock
# from datetime import datetime
# from pytz import timezone
from search.domain import DocMeta, Document
from search.services import metadata, index
from search.agent import consumer

# EASTERN = timezone('US/Eastern')


class TestIndexPaper(TestCase):
    """Re-index all versions of an arXiv paper."""

    def setUp(self):
        """Initialize a :class:`.MetadataRecordProcessor`."""
        self.processor = consumer.MetadataRecordProcessor()

    @mock.patch('search.agent.consumer.index')
    @mock.patch('search.agent.consumer.transform')
    @mock.patch('search.agent.consumer.metadata')
    def test_paper_has_one_version(self, mock_meta, mock_tx, mock_idx):
        """The arXiv paper has only one version."""
        mock_docmeta = DocMeta(version=1, paper_id='1234.56789', title='foo',
                               submitted_date='2001-03-02T03:04:05-400')
        mock_meta.retrieve.return_value = mock_docmeta
        mock_doc = Document(version=1, paper_id='1234.56789', title='foo',
                            submitted_date=['2001-03-02T03:04:05-400'])
        mock_tx.to_search_document.return_value = mock_doc

        self.processor.index_paper('1234.56789')

        mock_idx.bulk_add_documents.assert_called_once_with([mock_doc])

    @mock.patch('search.agent.consumer.index')
    @mock.patch('search.agent.consumer.transform')
    @mock.patch('search.agent.consumer.metadata')
    def test_paper_has_three_versions(self, mock_meta, mock_tx, mock_idx):
        """The arXiv paper has three versions."""
        mock_dm_1 = DocMeta(version=1, paper_id='1234.56789', title='foo',
                            submitted_date='2001-03-02T03:04:05-400')
        mock_dm_2 = DocMeta(version=2, paper_id='1234.56789', title='foo',
                            submitted_date='2001-03-03T03:04:05-400')
        mock_dm_3 = DocMeta(version=3, paper_id='1234.56789', title='foo',
                            submitted_date='2001-03-04T03:04:05-400')
        mock_meta.retrieve.side_effect = [mock_dm_3, mock_dm_1, mock_dm_2]
        mock_doc_1 = Document(version=1, paper_id='1234.56789', title='foo',
                              submitted_date=['2001-03-02T03:04:05-400'],
                              submitted_date_all=[
                                '2001-03-02T03:04:05-400',
                              ])
        mock_doc_2 = Document(version=2, paper_id='1234.56789', title='foo',
                              submitted_date=['2001-03-03T03:04:05-400'],
                              submitted_date_all=[
                                '2001-03-02T03:04:05-400',
                                '2001-03-03T03:04:05-400',
                              ])
        mock_doc_3 = Document(version=3, paper_id='1234.56789', title='foo',
                              submitted_date=['2001-03-04T03:04:05-400'],
                              submitted_date_all=[
                                '2001-03-02T03:04:05-400',
                                '2001-03-03T03:04:05-400',
                                '2001-03-04T03:04:05-400'
                              ])
        mock_tx.to_search_document.side_effect = [
            mock_doc_3, mock_doc_1, mock_doc_2
        ]
        self.processor.index_paper('1234.56789')
        self.assertEqual(mock_meta.retrieve.call_count, 3,
                         "Metadata should be retrieved for each version.")
        mock_idx.bulk_add_documents.assert_called_once_with(
            [mock_doc_1, mock_doc_2, mock_doc_3])


class TestAddToIndex(TestCase):
    """Add a search document to the index."""

    def setUp(self):
        """Initialize a :class:`.MetadataRecordProcessor`."""
        self.processor = consumer.MetadataRecordProcessor()

    @mock.patch('search.agent.consumer.index')
    def test_add_document_succeeds(self, mock_index):
        """The search document is added successfully."""
        try:
            self.processor._add_to_index(Document())
        except Exception as e:
            self.fail(e)
        mock_index.add_document.assert_called_once()

    @mock.patch('search.agent.consumer.index')
    def test_index_raises_index_connection_error(self, mock_index):
        """The index raises :class:`.index.IndexConnectionError`."""
        mock_index.IndexConnectionError = index.IndexConnectionError

        mock_index.add_document.side_effect = index.IndexConnectionError
        with self.assertRaises(consumer.IndexingFailed):
            self.processor._add_to_index(Document())

    @mock.patch('search.agent.consumer.index')
    def test_index_raises_unhandled_error(self, mock_index):
        """The index raises an unhandled exception."""
        mock_index.IndexConnectionError = index.IndexConnectionError

        mock_index.add_document.side_effect = RuntimeError
        with self.assertRaises(consumer.IndexingFailed):
            self.processor._add_to_index(Document())

class TestBulkAddToIndex(TestCase):
    """Add multiple search documents to the index in bulk."""

    def setUp(self):
        """Initialize a :class:`.MetadataRecordProcessor`."""
        self.processor = consumer.MetadataRecordProcessor()

    @mock.patch('search.agent.consumer.index')
    def test_bulk_add_documents_succeeds(self, mock_index):
        """The search document is added successfully."""
        try:
            self.processor._bulk_add_to_index([Document()])
        except Exception as e:
            self.fail(e)
        mock_index.bulk_add_documents.assert_called_once()

    @mock.patch('search.agent.consumer.index')
    def test_index_raises_index_connection_error(self, mock_index):
        """The index raises :class:`.index.IndexConnectionError`."""
        mock_index.IndexConnectionError = index.IndexConnectionError

        mock_index.bulk_add_documents.side_effect = index.IndexConnectionError
        with self.assertRaises(consumer.IndexingFailed):
            self.processor._bulk_add_to_index([Document()])

    @mock.patch('search.agent.consumer.index')
    def test_index_raises_unhandled_error(self, mock_index):
        """The index raises an unhandled exception."""
        mock_index.IndexConnectionError = index.IndexConnectionError

        mock_index.bulk_add_documents.side_effect = RuntimeError
        with self.assertRaises(consumer.IndexingFailed):
            self.processor._bulk_add_to_index([Document()])

class TestTransformToDocument(TestCase):
    """Transform metadata into a search document."""

    def setUp(self):
        """Initialize a :class:`.MetadataRecordProcessor`."""
        self.processor = consumer.MetadataRecordProcessor()

    @mock.patch('search.agent.consumer.transform')
    def test_transform_raises_exception(self, mock_transform):
        """The transform module raises an exception."""
        mock_transform.to_search_document.side_effect = RuntimeError
        with self.assertRaises(consumer.DocumentFailed):
            self.processor._transform_to_document(DocMeta())


class TestGetMetadata(TestCase):
    """Retrieve metadata for an arXiv e-print."""

    def setUp(self):
        """Initialize a :class:`.MetadataRecordProcessor`."""
        self.processor = consumer.MetadataRecordProcessor()

    @mock.patch('search.agent.consumer.metadata')
    def test_metadata_service_returns_metadata(self, mock_metadata):
        """The metadata service returns valid metadata."""
        docmeta = DocMeta()
        mock_metadata.retrieve.return_value = docmeta
        self.assertEqual(docmeta, self.processor._get_metadata('1234.5678'),
                         "The metadata is returned.")

    @mock.patch('search.agent.consumer.metadata')
    def test_metadata_service_raises_connection_error(self, mock_metadata):
        """The metadata service raises :class:`.metadata.ConnectionFailed`."""
        mock_metadata.ConnectionFailed = metadata.ConnectionFailed
        mock_metadata.RequestFailed = metadata.RequestFailed
        mock_metadata.BadResponse = metadata.BadResponse

        mock_metadata.retrieve.side_effect = metadata.ConnectionFailed
        with self.assertRaises(consumer.IndexingFailed):
            self.processor._get_metadata('1234.5678')

    @mock.patch('search.agent.consumer.metadata')
    def test_metadata_service_raises_request_error(self, mock_metadata):
        """The metadata service raises :class:`.metadata.RequestFailed`."""
        mock_metadata.ConnectionFailed = metadata.ConnectionFailed
        mock_metadata.RequestFailed = metadata.RequestFailed
        mock_metadata.BadResponse = metadata.BadResponse

        mock_metadata.retrieve.side_effect = metadata.RequestFailed
        with self.assertRaises(consumer.DocumentFailed):
            self.processor._get_metadata('1234.5678')

    @mock.patch('search.agent.consumer.metadata')
    def test_metadata_service_raises_bad_response(self, mock_metadata):
        """The metadata service raises :class:`.metadata.BadResponse`."""
        mock_metadata.ConnectionFailed = metadata.ConnectionFailed
        mock_metadata.RequestFailed = metadata.RequestFailed
        mock_metadata.BadResponse = metadata.BadResponse

        mock_metadata.retrieve.side_effect = metadata.BadResponse
        with self.assertRaises(consumer.DocumentFailed):
            self.processor._get_metadata('1234.5678')
