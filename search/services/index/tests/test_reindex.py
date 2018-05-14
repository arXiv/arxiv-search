"""Tests for reindexing."""

from unittest import TestCase, mock

from search.services import index


def raise_index_exists(*args, **kwargs):
    """Raise a resource_already_exists_exception TransportError."""
    raise index.TransportError(400, 'resource_already_exists_exception', {})


class TestReindexing(TestCase):
    """Tests for :func:`.index.reindex`."""

    @mock.patch('search.services.index.Elasticsearch')
    def test_reindex_from_scratch(self, mock_Elasticsearch):
        """Reindex to an index that does not exist."""
        mock_es = mock.MagicMock()
        mock_Elasticsearch.return_value = mock_es
        index.reindex('barindex', 'bazindex')
        self.assertEqual(mock_es.indices.create.call_count, 1,
                         "Should attempt to create the new index")
        self.assertEqual(mock_es.indices.create.call_args[0][0], "bazindex",
                         "Should attempt to create the new index")

        self.assertEqual(mock_es.reindex.call_count, 1,
                         "Should proceed to request reindexing")
        self.assertEqual(mock_es.reindex.call_args[0][0]['source']['index'],
                         'barindex')
        self.assertEqual(mock_es.reindex.call_args[0][0]['dest']['index'],
                         'bazindex')

    @mock.patch('search.services.index.Elasticsearch')
    def test_reindex_already_exists(self, mock_Elasticsearch):
        """Reindex to an index that already exists."""
        mock_es = mock.MagicMock()
        mock_Elasticsearch.return_value = mock_es
        mock_es.indices.create.side_effect = raise_index_exists
        index.reindex('barindex', 'bazindex')
        self.assertEqual(mock_es.indices.create.call_count, 1,
                         "Should attempt to create the new index")
        self.assertEqual(mock_es.indices.create.call_args[0][0], "bazindex",
                         "Should attempt to create the new index")

        self.assertEqual(mock_es.reindex.call_count, 1,
                         "Should proceed to request reindexing")
        self.assertEqual(mock_es.reindex.call_args[0][0]['source']['index'],
                         'barindex')
        self.assertEqual(mock_es.reindex.call_args[0][0]['dest']['index'],
                         'bazindex')


class TestTaskStatus(TestCase):
    """Tests for :func:`.index.get_task_status`."""

    @mock.patch('search.services.index.Elasticsearch')
    def test_get_task_status(self, mock_Elasticsearch):
        """Get task status via the ES API."""
        mock_es = mock.MagicMock()
        mock_Elasticsearch.return_value = mock_es
        
        task_id = 'foonode:bartask'
        index.get_task_status(task_id)
        self.assertEqual(mock_es.tasks.get.call_count, 1,
                         "Should call the task status endpoint")
        self.assertEqual(mock_es.tasks.get.call_args[0][0], task_id,
                         "Should call the task status endpoint with task ID")
