"""Unit tests for :mod:`search.agent`."""

from unittest import TestCase, mock

from search.domain import DocMeta, Document
from search.services import metadata, index
from search.agent import consumer


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
        """The metadata service returns valid metadata."""
        mock_metadata.ConnectionFailed = metadata.ConnectionFailed
        mock_metadata.retrieve.side_effect = metadata.ConnectionFailed
        with self.assertRaises(consumer.IndexingFailed):
            self.processor._get_metadata('1234.5678')
