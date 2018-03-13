"""Test integration with Kinesis for the indexing agent."""

from unittest import TestCase
import os
import subprocess
import time
import json
from datetime import datetime

import boto3
from botocore.exceptions import ClientError
from botocore.vendored.requests.exceptions import ConnectTimeout
from botocore.client import Config

from search.factory import create_ui_web_app
from search.services import index
from search.agent.consumer import MetadataRecordProcessor
from search.domain import Document

import urllib3


class TestKinesisIntegration(TestCase):
    """Verifies indexing agent behavior against local Kinesis system."""

    # Set __test__ = False to disable this TestCase.
    __test__ = int(os.environ.get('TEST_LEVEL', '1')) >= 2

    @classmethod
    def setUpClass(cls):
        """Spin up localstack and search agent."""
        # We disable certificate validation for testing.
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        os.environ['ELASTICSEARCH_SERVICE_HOST'] = 'localhost'
        os.environ['ELASTICSEARCH_SERVICE_PORT'] = "9202"
        os.environ['ELASTICSEARCH_PORT_9202_PROTO'] = "http"
        os.environ['ELASTICSEARCH_VERIFY'] = 'false'
        os.environ['METADATA_ENDPOINT'] = 'http://search-metadata:8000/docmeta/'
        os.environ['METADATA_CACHE_DIR'] = os.path.abspath('tests/data/examples')

        cls.app = create_ui_web_app()

        print('Build indexing agent')
        # Use docker compose to build and start the indexing agent, along with
        # localstack (which provides Kinesis, Elasticsearch Service, DynamodB).
        build_agent = subprocess.run(
            "docker-compose build", stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, shell=True, cwd="agent/"
        )
        print('Start indexing agent and ES stack')
        start_agent = subprocess.run(
            "docker-compose up -d", stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, shell=True, cwd="agent/"
        )

        print('Waiting for localstack and indexing agent to be available...')
        print(start_agent.stdout.decode('utf-8'))
        print(start_agent.stderr.decode('utf-8'))
        time.sleep(12)      # Give localstack a chance to spin up.

        # When ES is available, create the index.
        with cls.app.app_context():
            while True:
                time.sleep(5)
                if index.cluster_available():
                    time.sleep(2)
                    index.create_index()
                    break

        # Get a connection to the Kinesis stream.
        config = Config(read_timeout=1, connect_timeout=1)
        cls.client = boto3.client(
            'kinesis', region_name='us-east-1',
            endpoint_url="https://localhost:5568",
            aws_access_key_id='foo', aws_secret_access_key='bar',
            verify=False, config=config
        )

        # Wait for the agent to have started. The agent will create the stream
        #  if it does not already exist (which is always the case for the test
        #  stack).
        print('Waiting for indexing agent to start...')
        while True:
            try:
                cls.client.describe_stream(StreamName='MetadataIsAvailable')
                time.sleep(2)
                break
            except (ClientError, ConnectTimeout):
                print('Still waiting')
                time.sleep(5)   # Wait for the agent to create the stream.
        print('Indexing agent has started')


    @classmethod
    def tearDownClass(cls):
        """Tear down Elasticsearch once all tests have run."""
        stop_agent = subprocess.run(
            "docker-compose kill", stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, shell=True, cwd="agent/"
        )
        del cls.app

    def test_verify_notification_results_in_indexing(self):
        """Agent indexes documents for which notifications are produced."""
        # We disable certificate validation for testing.
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
        time.sleep(5)    # Give a few seconds for messages to propagate.
        with self.app.app_context():
            for document_id in to_index:
                try:
                    doc = index.get_document(document_id)
                except index.DocumentNotFound:
                    self.fail('Document {document_id} not indexed')
                self.assertIsInstance(doc, Document)
