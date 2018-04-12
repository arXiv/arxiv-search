"""
Provides a base class for Kinesis record handling.

.. _todo: This should move to arXiv-base, per ARXIVNG-281.
"""

import time
import json
import os
from typing import Any, Optional, Tuple, Generator, Callable
from contextlib import contextmanager
import signal

import boto3
from botocore.exceptions import WaiterError, NoCredentialsError, \
    PartialCredentialsError, BotoCoreError, ClientError

from arxiv.base import logging
logger = logging.getLogger(__name__)
logger.propagate = False

class CheckpointError(RuntimeError):
    """Checkpointing failed."""


class StreamNotAvailable(RuntimeError):
    """Could not find or connect to the stream."""


class KinesisRequestFailed(RuntimeError):
    """Raised when a Kinesis request failed permanently."""


class StopProcessing(RuntimeError):
    """Gracefully stopped processing upon unrecoverable error."""


class ConfigurationError(RuntimeError):
    """There was a problem with the configuration."""


def retry(retries: int = 5, wait: int = 5) -> Callable:
    """
    Decorator factory for retrying Kinesis calls.

    Parameters
    ----------
    retries : int
        Number of times to retry before failing.
    wait : int
        Number of seconds to wait between retries.

    Returns
    -------
    function
        A decorator that retries the decorated func ``retries`` times before
        raising :class:`.KinesisRequestFailed`.

    """
    __retries = retries

    def decorator(func: Callable) -> Callable:
        """Retry the decorated func on ClientErrors up to ``retries`` times."""
        _retries = __retries

        def inner(*args, **kwargs) -> Any:
            retries = _retries
            while retries > 0:
                try:
                    return func(*args, **kwargs)
                except ClientError as e:
                    code = e.response['Error']['Code']
                    logger.error('Caught ClientError %s, retrying', code)
                    retries -= 1
            raise KinesisRequestFailed('Max retries; last code: {code}')
        return inner
    return decorator


class CheckpointManager(object):
    """Provides on-disk loading and updating of consumer checkpoints."""

    def __init__(self, base_path: str, stream_name: str, shard_id: str) \
            -> None:
        """Load or create a new file for checkpointing."""
        if not os.path.exists(base_path):
            raise ValueError(f'Path does not exist: {base_path}')
        self.file_path = os.path.join(base_path,
                                      f'{stream_name}__{shard_id}.json')
        if not os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'w') as f:
                    f.write('')
            except Exception as e:   # The containing path doesn't exist.
                raise ValueError(f'Could not use {self.file_path}') from e

        with open(self.file_path) as f:
            position = f.read()
        self.position = position if position else None

    def checkpoint(self, position: str) -> None:
        """Checkpoint at ``position``."""
        try:
            with open(self.file_path, 'w') as f:
                f.write(position)
            self.position = position
        except Exception as e:
            raise CheckpointError('Could not checkpoint') from e


class BaseConsumer(object):
    """
    Kinesis stream consumer.

    Consumes a single shard from a single stream, and checkpoints on disk
    (to reduce external dependencies).
    """

    def __init__(self, stream_name: str, shard_id: str, access_key: str,
                 secret_key: str, region: str, checkpointer: CheckpointManager,
                 back_off: int = 5, batch_size: int = 50,
                 endpoint: Optional[str] = None, verify: bool = True,
                 duration: Optional[int] = None) -> None:
        """Initialize a new stream consumer."""
        logger.info(f'New consumer for {stream_name} ({shard_id})')
        self.stream_name = stream_name
        self.shard_id = shard_id
        self.checkpointer = checkpointer
        self.position = self.checkpointer.position
        self.duration = duration
        self.start_time = None

        logger.info(f'Getting a new connection to Kinesis at {endpoint}'
                    f' in region {region}, with SSL verification={verify}')
        self.client = boto3.client('kinesis',
                                   aws_access_key_id=access_key,
                                   aws_secret_access_key=secret_key,
                                   endpoint_url=endpoint,
                                   verify=verify,
                                   region_name=region)

        logger.info(f'Waiting for {self.stream_name} to be available')
        try:
            self.wait_for_stream()
        except (KinesisRequestFailed, StreamNotAvailable):
            logger.info('Could not connect to stream; attempting to create')
            self.client.create_stream(
                StreamName=self.stream_name,
                ShardCount=1
            )
            logger.info(f'Created; waiting for {self.stream_name} again')
            self.wait_for_stream()

        self.back_off = back_off
        self.batch_size = batch_size

        # Intercept SIGINT and SIGTERM so that we can checkpoint before exit.
        self.exit = False
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)
        logger.info('Ready to start')

    def stop(self, signal: int, frame: Any):
        """Set exit flag for a graceful stop."""
        logger.error(f'Received signal {signal}')
        self._checkpoint()
        logger.error('Done')
        raise StopProcessing(f'Received signal {signal}')

    @retry(5, 10)
    def wait_for_stream(self) -> None:
        """
        Wait for the stream to become available.

        If the stream becomes available, returns ``None``. Otherwise, raises
        a :class:`.StreamNotAvailable` exception.

        Raises
        ------
        :class:`.StreamNotAvailable`
            Raised when the stream could not be reached.

        """
        waiter = self.client.get_waiter('stream_exists')
        try:
            logger.error(f'Waiting for stream {self.stream_name}')
            waiter.wait(
                StreamName=self.stream_name,
                Limit=1,
                ExclusiveStartShardId=self.shard_id
            )
        except WaiterError as e:
            logger.error('Failed to get stream while waiting')
            raise StreamNotAvailable('Could not connect to stream') from e
        except (PartialCredentialsError, NoCredentialsError) as e:
            logger.error('Credentials missing or incomplete: %s', e.msg)
            raise ConfigurationError('Credentials missing') from e

    def _get_iterator(self) -> str:
        """
        Get a new shard iterator.

        If our position is set, we will start with the record immediately after
        that position. Otherwise, we start at the oldest available record
        (i.e. the "trim horizon").

        Returns
        -------
        str
            The sequence ID of the record on which to start.

        """
        params = dict(StreamName=self.stream_name, ShardId=self.shard_id)
        if self.position:
            params.update(dict(
                ShardIteratorType='AFTER_SEQUENCE_NUMBER',
                StartingSequenceNumber=self.position
            ))
        else:
            # Position is not set/known; start as early as possible.
            params.update(dict(ShardIteratorType='TRIM_HORIZON'))
        try:
            return self.client.get_shard_iterator(**params)['ShardIterator']
        except self.client.exceptions.InvalidArgumentException:
            # Iterator may not have come from this stream/shard.
            if self.position is not None:
                self.position = None
                return self._get_iterator()

    def _checkpoint(self) -> None:
        """
        Checkpoint at the current position.

        The current position is the sequence number of the last record that was
        successfully processed.
        """
        logger.debug('Attempting to checkpoint')
        if self.position is not None:
            self.checkpointer.checkpoint(self.position)
            logger.debug(f'Set checkpoint at {self.position}')

    @retry(retries=10, wait=5)
    def get_records(self, iterator: str, limit: int) -> Tuple[str, dict]:
        """Get the next batch of ``limit`` or fewer records."""
        logger.debug(f'Get more records from {iterator}, limit {limit}')
        response = self.client.get_records(ShardIterator=iterator,
                                           Limit=limit)
        iterator = response['NextShardIterator']
        return iterator, response

    def _check_timeout(self):
        if not self.start_time or not self.duration:
            return
        running_for = time.time() - self.start_time
        if running_for > self.duration:
            logger.info(f'Ran for {running_for} seconds; exiting')
            self._checkpoint()
            raise StopProcessing(f'Ran for {running_for} seconds; exiting')

    def process_records(self, start: str) -> Tuple[str, int]:
        """Retrieve and process records starting at ``start``."""
        logger.debug(f'Get more records, starting at {start}')
        processed = 0
        try:
            next_start, response = self.get_records(start, self.batch_size)
        except Exception as e:
            self._checkpoint()
            raise StopProcessing('Unhandled exception: %s' % str(e)) from e

        for record in response['Records']:
            self._check_timeout()

            # It is possible that Kinesis will replay the same message several
            # times, especially at the end of the stream. There's no point in
            # replaying the message, so we'll continue on.
            if record['SequenceNumber'] == self.position:
                continue

            self.process_record(record)
            processed += 1

            # Setting the position means that we have successfully
            # processed this record.
            if record['SequenceNumber']:    # Make sure it's set.
                self.position = record['SequenceNumber']
                logger.debug(f'Updated position to {self.position}')
        logger.debug(f'Next start is {next_start}')
        return next_start, processed

    def go(self) -> None:
        """Main processing routine."""
        self.start_time = time.time()
        logger.info(f'Starting processing from position {self.position}'
                    f' on stream {self.stream_name} and shard {self.shard_id}')

        start = self._get_iterator()
        while True:
            start, processed = self.process_records(start)
            if processed > 0:
                self._checkpoint()  # Checkpoint after every batch.
            if start is None:     # Shard is closed.
                logger.error('Shard closed unexpectedly; no new iterator')
                self._checkpoint()
                raise StopProcessing('Could not get a new iterator')
            self._check_timeout()

    def process_record(self, record: dict) -> None:
        """
        Process a single record from the stream.

        Parameters
        ----------
        record : dict

        """
        logger.info(f'Processing record {record["SequenceNumber"]}')
        logger.debug(f'Process record {record}')
        # raise NotImplementedError('Should be implemented by a subclass')
