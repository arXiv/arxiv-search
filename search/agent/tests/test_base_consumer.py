"""Tests for :class:`.BaseConsumer`."""

from unittest import TestCase, mock
from botocore.exceptions import BotoCoreError, WaiterError, ClientError

from search.agent.base import BaseConsumer, StreamNotAvailable, StopProcessing


class TestBaseConsumer(TestCase):
    """Test :class:`.BaseConsumer` behavior and public methods."""

    def setUp(self):
        self.checkpointer = mock.MagicMock()
        self.checkpointer.position = None

    @mock.patch('boto3.client')
    def test_init(self, mock_client_factory):
        """On init, consumer should wait for stream to be available."""
        mock_client = mock.MagicMock()
        mock_waiter = mock.MagicMock()
        mock_client.get_waiter.return_value = mock_waiter
        mock_client_factory.return_value = mock_client

        try:
            BaseConsumer('foo', '1', 'a1b2c3d4', 'qwertyuiop', 'us-east-1',
                         self.checkpointer)
        except Exception as e:
            self.fail('If the waiter returns without an exception, no'
                      ' exception should be raised.')
        self.assertEqual(mock_waiter.wait.call_count, 1,
                         "A boto3 waiter should be used")

    @mock.patch('boto3.client')
    def test_init_stream_not_available(self, mock_client_factory):
        """If the stream is not available, should raise an exception."""
        mock_client = mock.MagicMock()
        mock_waiter = mock.MagicMock()

        def raise_waiter_error(*a, **k):
            raise WaiterError('', {}, {})

        mock_waiter.wait.side_effect = raise_waiter_error
        mock_client.get_waiter.return_value = mock_waiter
        mock_client_factory.return_value = mock_client
        with self.assertRaises(StreamNotAvailable):
            BaseConsumer('foo', '1', 'a1b2c3d4', 'qwertyuiop', 'us-east-1',
                         self.checkpointer)

    @mock.patch('boto3.client')
    def test_iteration(self, mock_client_factory):
        """Test iteration behavior."""
        mock_client = mock.MagicMock()
        mock_client_factory.return_value = mock_client
        mock_client.get_records.return_value = {
            'Records': [
                {'SequenceNumber': str(i)} for i in range(10)
            ],
            'NextShardIterator': '10'
        }
        consumer = BaseConsumer('foo', '1', 'a1b2c3d4', 'qwertyuiop',
                                'us-east-1', self.checkpointer)
        next_start, processed = consumer.process_records('0')
        self.assertGreater(mock_client.get_records.call_count, 0)
        self.assertEqual(processed, 10)
        self.assertEqual(next_start, '10', "Should return NextShardIterator")

    @mock.patch('boto3.client')
    def test_process_records_until_shard_closes(self, mock_client_factory):
        """Should call GetRecords until no next iterator is available."""
        mock_client = mock.MagicMock()
        mock_client_factory.return_value = mock_client
        mock_client.get_shard_iterator.return_value = {'ShardIterator': '1'}

        def get_records(**kwargs):
            start = int(kwargs['ShardIterator'])
            end = start + int(kwargs['Limit'])
            if start > 500:
                return {'Records': [], 'NextShardIterator': None}
            return {
                'Records': [
                    {'SequenceNumber': str(i)} for i in range(start, end)
                ],
                'NextShardIterator': str(end + 1)
            }

        mock_client.get_records.side_effect = get_records

        batch_size = 50
        consumer = BaseConsumer('foo', '1', 'a1b2c3d4', 'qwertyuiop',
                                'us-east-1', self.checkpointer,
                                batch_size=batch_size)
        with self.assertRaises(StopProcessing):
            consumer.go()
        self.assertEqual(mock_client.get_records.call_count,
                         (500/batch_size) + 1,
                         "Should call Kinesis GetRecords until no iterator"
                         " is returned.")

    @mock.patch('boto3.client')
    def test_process_records_with_clienterror(self, mock_client_factory):
        """Should try to checkpoint before exiting."""
        mock_client = mock.MagicMock()
        mock_client_factory.return_value = mock_client
        mock_client.get_shard_iterator.return_value = {'ShardIterator': '1'}

        def raise_client_error(*args, **kwargs):
            raise ClientError({'Error': {'Code': 'foo'}}, {})

        mock_client.get_records.side_effect = raise_client_error

        batch_size = 50
        consumer = BaseConsumer('foo', '1', 'a1b2c3d4', 'qwertyuiop',
                                'us-east-1', self.checkpointer,
                                batch_size=batch_size)
        consumer.position = 'fooposition'
        try:
            consumer.go()
        except Exception:
            pass
        self.assertEqual(self.checkpointer.checkpoint.call_count, 1)

    @mock.patch('boto3.client')
    def test_start_from_timestamp(self, mock_client_factory):
        """Consumer is initialized with start_type 'AT_TIMESTAMP'."""
        mock_client = mock.MagicMock()
        mock_client_factory.return_value = mock_client
        mock_client.get_shard_iterator.return_value = {'ShardIterator': '1'}

        consumer = BaseConsumer('foo', '1', 'a1b2c3d4', 'qwertyuiop',
                                'us-east-1', self.checkpointer,
                                start_type='AT_TIMESTAMP')
        consumer._get_iterator()
        args, kwargs = mock_client.get_shard_iterator.call_args
        self.assertEqual(kwargs['ShardIteratorType'], 'AT_TIMESTAMP')
        self.assertIn('Timestamp', kwargs)

    @mock.patch('boto3.client')
    def test_start_from_position(self, mock_client_factory):
        """Consumer is initialized with start_type 'AT_TIMESTAMP'."""
        mock_client = mock.MagicMock()
        mock_client_factory.return_value = mock_client
        mock_client.get_shard_iterator.return_value = {'ShardIterator': '1'}

        consumer = BaseConsumer('foo', '1', 'a1b2c3d4', 'qwertyuiop',
                                'us-east-1', self.checkpointer,
                                start_type='AT_TIMESTAMP')
        consumer.position = 'fooposition'
        consumer._get_iterator()
        args, kwargs = mock_client.get_shard_iterator.call_args
        self.assertEqual(kwargs['ShardIteratorType'], 'AFTER_SEQUENCE_NUMBER')
        self.assertEqual(kwargs['StartingSequenceNumber'], 'fooposition')

    @mock.patch('boto3.client')
    def test_start_from_trim_horizon(self, mock_client_factory):
        """Consumer is initialized with start_type 'AT_TIMESTAMP'."""
        mock_client = mock.MagicMock()
        mock_client_factory.return_value = mock_client
        mock_client.get_shard_iterator.return_value = {'ShardIterator': '1'}

        consumer = BaseConsumer('foo', '1', 'a1b2c3d4', 'qwertyuiop',
                                'us-east-1', self.checkpointer,
                                start_type='TRIM_HORIZON')
        consumer._get_iterator()
        args, kwargs = mock_client.get_shard_iterator.call_args
        self.assertEqual(kwargs['ShardIteratorType'], 'TRIM_HORIZON')
        self.assertNotIn('StartingSequenceNumber', kwargs)
