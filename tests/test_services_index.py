"""Tests for :mod:`search.services.index`."""

import unittest
from search.services import index
from search import transform
import json
import time
from elasticsearch import Elasticsearch
from elasticsearch.connection import Urllib3HttpConnection
import shlex
import subprocess
import requests
from datetime import datetime

DOCKER_IMAGE = "docker.elastic.co/elasticsearch/elasticsearch:5.5.3"


class IntegrationWithElasticsearch(unittest.TestCase):
    """Elasticsearch is running locally at port 9200."""

    @classmethod
    def setUpClass(cls):
        """Start up an ES instance using Docker."""
        pull = """docker pull %s""" % DOCKER_IMAGE
        pull = shlex.split(pull)
        start = """docker run -p 9200:9200 -e "http.host=0.0.0.0" -e "transport.host=127.0.0.1" %s""" % DOCKER_IMAGE
        start = shlex.split(start)
        subprocess.run(pull, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.Popen(start, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        time.sleep(10)   # Give ES a chance to start.
        start_time = datetime.now()
        while True:
            try:
                r = requests.get('http://localhost:9200/arxiv/')
            except IOError as e:
                continue
            if r.status_code == 401:
                break
            # Try for a minute, then bail.
            if datetime.now() - start_time > datetime.timedelta(seconds=60):
                raise RuntimeError('Failed to start ES in reasonable time')



    def setUp(self):
        """Create a direct connection to ES; wipe test index if it exists."""
        self.es = Elasticsearch(connection_class=Urllib3HttpConnection,
                                http_auth='elastic:changeme')
        self.es.indices.delete('test_arxiv', ignore=404)

    def test_can_connect(self):
        """The SearchSession can create a connection to Elasticsearch."""
        with open('mappings/DocumentMapping.json') as f:
            mappings = json.load(f)
        try:
            index.SearchSession('127.0.0.1', 'test_arxiv', mappings,
                                http_auth='elastic:changeme')
        except IOError as e:
            self.fail('Failed to initialize SearchSession: %s' % e)

    def test_can_index(self):
        """The SearchSession can add a document to the index."""
        with open('mappings/DocumentMapping.json') as f:
            mappings = json.load(f)
        try:
            search = index.SearchSession('127.0.0.1', 'test_arxiv', mappings,
                                         http_auth='elastic:changeme')
        except IOError as e:
            self.fail('Failed to initialize SearchSession: %s' % e)

        with open('tests/data/docmeta.json') as f:
            self.metadata = json.load(f)
        with open('tests/data/fulltext.json') as f:
            self.fulltext = json.load(f)
        document = transform.to_search_document(self.metadata, self.fulltext)

        try:
            search.add_document(document)
        except (ValueError, IOError) as e:
            self.fail('Could not add search document: %s' % e)

        self.assertTrue(self.es.exists('test_arxiv', 'arxiv',
                                       document['metadata_id']))

    def test_can_retrieve(self):
        """The SearchSession can retrieve a document from the index."""
        with open('mappings/DocumentMapping.json') as f:
            mappings = json.load(f)
        try:
            search = index.SearchSession('127.0.0.1', 'test_arxiv', mappings,
                                         http_auth='elastic:changeme')
        except IOError as e:
            self.fail('Failed to initialize SearchSession: %s' % e)

        with open('tests/data/docmeta.json') as f:
            self.metadata = json.load(f)
        with open('tests/data/fulltext.json') as f:
            self.fulltext = json.load(f)
        document = transform.to_search_document(self.metadata, self.fulltext)
        search.add_document(document)

        retrieved = search.get_document(document['metadata_id'])
        self.assertIsInstance(retrieved, dict)
        for key, value in document.items():
            self.assertEqual(retrieved.get(key), value)

    def test_can_search(self):
        """The SearchSession can perform a query."""
        with open('mappings/DocumentMapping.json') as f:
            mappings = json.load(f)
        try:
            search = index.SearchSession('127.0.0.1', 'test_arxiv', mappings,
                                         http_auth='elastic:changeme')
        except IOError as e:
            self.fail('Failed to initialize SearchSession: %s' % e)

        with open('tests/data/docmeta.json') as f:
            self.metadata = json.load(f)
        with open('tests/data/fulltext.json') as f:
            self.fulltext = json.load(f)
        document = transform.to_search_document(self.metadata, self.fulltext)
        search.add_document(document)

        time.sleep(1)    # Search results are not immediately available!

        results = search.search(msc_class='41A25')
        self.assertEqual(len(results['results']), 1)
        self.assertEqual(results['results'][0]['title'], document['title'])

        results = search.search(msc_class='41A2')
        self.assertEqual(len(results['results']), 0)

    def tearDown(self):
        """Remove the test index."""
        self.es.indices.delete('test_arxiv', ignore=404)

    @classmethod
    def tearDownClass(cls):
        """Spin down ES."""
        ps = "docker ps | grep %s | awk '{print $1;}'" % DOCKER_IMAGE
        container = subprocess.check_output(["/bin/sh", "-c", ps]) \
            .strip().decode('ascii')
        stop = """docker stop %s""" % container
        stop = shlex.split(stop)
        subprocess.run(stop, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
