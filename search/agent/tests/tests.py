"""Integration tests for :mod:`search.agent` with Kinesis."""

from unittest import TestCase, mock
import os
import time
import subprocess
import tempfile
import boto3
import json
import threading

from search.agent import process_stream
from search.agent.base import StopProcessing
from search.services import metadata
from search.domain import DocMeta

BASE_PATH = os.path.join(os.path.split(os.path.abspath(__file__))[0],
                         '../../../tests/data/examples')


class TestKinesisIntegration(TestCase):
    """Test :class:`.MetadataRecordProcessor` with a live Kinesis stream."""

    @classmethod
    def setUpClass(cls):
        """Spin up ES and index documents."""
        os.environ['ELASTICSEARCH_SERVICE_HOST'] = 'localhost'
        os.environ['ELASTICSEARCH_SERVICE_PORT'] = "9201"
        os.environ['ELASTICSEARCH_PORT_9201_PROTO'] = "http"
        os.environ['ELASTICSEARCH_VERIFY'] = 'false'

        os.environ['KINESIS_STREAM'] = 'MetadataIsAvailable'
        os.environ['KINESIS_SHARD_ID'] = '0'
        os.environ['KINESIS_CHECKPOINT_VOLUME'] = tempfile.mkdtemp()
        os.environ['KINESIS_ENDPOINT'] = 'http://127.0.0.1:6568'
        os.environ['KINESIS_VERIFY'] = 'false'

        print('starting localstack')
        start_localstack = subprocess.run(
            "docker run -d -p 6568:4568 --name ltest atlassianlabs/localstack",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

        if start_localstack.returncode != 0:
            raise RuntimeError(
                f'Could not start localstack: {start_localstack.stdout}.'
                f' Is one already running? Is port 6568 available?'
            )
        cls.ls_container = start_localstack.stdout.decode('ascii').strip()
        print(f'localstack started as {cls.ls_container}')

        cls.client = boto3.client(
            'kinesis',
            region_name='us-east-1',
            endpoint_url="http://localhost:6568",
            aws_access_key_id='foo',
            aws_secret_access_key='bar',
            verify=False
        )
        print('creating stream ahead of time, to populate with records')
        cls.client.create_stream(
            StreamName='MetadataIsAvailable',
            ShardCount=1
        )
        time.sleep(5)
        print('created stream, ready to test')

    @classmethod
    def tearDownClass(cls):
        """Tear down Elasticsearch once all tests have run."""
        stop_es = subprocess.run(f"docker rm -f {cls.ls_container}",
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 shell=True)

    @mock.patch('search.agent.consumer.index')
    @mock.patch('search.agent.consumer.metadata')
    def test_process(self, mock_metadata, mock_index):
        """Add some records to the stream, and run processing loop for 5s."""
        to_index = [
            "1712.04442",    # flux capacitor
            "1511.07473",    # flux capacitor
            "1604.04228",    # flux capacitor
            "1403.6219",     # λ
            "1404.3450",     # $z_1$
            "1703.09067",    # $\lambda$
            "1408.6682",     # $\lambda$
            "1607.05107",    # Schröder
            "1509.08727",    # Schroder
            "1710.01597",    # Schroeder
            "1708.07156",    # w w
            "1401.1012",     # Wonmin Son
        ]
        for document_id in to_index:
            data = bytes(
                json.dumps({'document_id': document_id}),
                encoding='utf-8'
            )

            self.client.put_record(
                StreamName='MetadataIsAvailable', Data=data, PartitionKey='0'
            )

        def retrieve(document_id):
            with open(os.path.join(BASE_PATH, f'{document_id}.json')) as f:
                return DocMeta(**json.load(f))
        mock_metadata.retrieve.side_effect = retrieve

        # Preserve exceptions
        mock_metadata.RequestFailed = metadata.RequestFailed
        mock_metadata.SecurityException = metadata.SecurityException
        mock_metadata.ConnectionFailed = metadata.ConnectionFailed
        mock_metadata.BadResponse = metadata.BadResponse

        try:
            process_stream(duration=30)
        except StopProcessing:
            pass

        self.assertGreater(mock_metadata.retrieve.call_count, 0)
