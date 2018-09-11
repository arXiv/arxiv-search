# arxiv-search

## Development quickstart

### Running Elasticsearch + Kibana with docker-compose

The easiest way to spin up ES and Kibana is using the included
``docker-compose.yml`` file. This will start ES and Kibana on a custom network.
The ES service ports 9200 and 9300, and Kibana service port 5601, will be
mapped to localhost.

```bash
docker-compose up
```
Kibana will be available at http://127.0.0.1:5601/. The containers started by
docker-compose can be stopped with ``docker-compose down`` from the same
directory.

Make sure that you have a recent version of ``docker-compose``; this is
confirmed to work with version 1.18.

Note that connection configuration variables for the search service are set in
``search/config.py``, where they are read from the environment. The arXiv
search service expects the ES service to be available at http://localhost:9200
by default. Hence, you should be able to start ES using docker-compose as above
and make no configuration changes to the arXiv search service.

#### Running Elasticsearch without Kibana

Alternatively, you can start up ES on its own. Be sure to map port 9200 to
the host machine, so that arXiv search can find it.

```bash
docker build -t "arxiv/elasticsearch" -f ./Dockerfile-elasticsearch .
docker run -it \
    -e "http.host=0.0.0.0" \
    -e "transport.host=127.0.0.1" \
    -p 9200:9200 -p 9300:9300 arxiv/elasticsearch
```

### Create & populate the index

A couple of helper scripts are included to create and populate the search
index. Note that you will need to have access to the /docmeta endpoint, which
is only accessible from the CUL network.

```bash
pipenv install
FLASK_APP=app.py FLASK_DEBUG=1 ELASTICSEARCH_HOST=127.0.0.1 pipenv run python create_index.py
FLASK_APP=app.py FLASK_DEBUG=1 ELASTICSEARCH_HOST=127.0.0.1 pipenv run python bulk_index.py
```

``bulk_index.py`` without parameters populate the index with the
list of papers defined in ``tests/data/sample.json``. It take several minutes
to run. Individual paper IDs may be specified with the ``--paper_id``
parameter.

To check for missing records, use ``audit.py``:

```bash
ELASTICSEARCH_HOST=127.0.0.1 ELASTICSEARCH_INDEX=arxiv pipenv run python audit.py -l list_of_papers.txt -o missing.txt
```

### Reindexing

ElasticSearch can perform reindexing by copying documents from one index to
another index with a different mapping. ``reindex.py`` will initiate the
reindexing process, and poll for completion until all of the documents are
processed. If the destination index does not already exist, it will be created
using the current configured mapping.

```bash
FLASK_APP=app.py ELASTICSEARCH_HOST=127.0.0.1 pipenv run python reindex.py OLD_INDEX NEW_INDEX
```


### Flask dev server

You can spin up the search app directly.

```bash
FLASK_APP=app.py FLASK_DEBUG=1 ELASTICSEARCH_HOST=127.0.0.1 pipenv run flask run
```
This will monitor any of the Python bits for changes and restart the server.
Unfortunately static files and templates are not monitored, so you'll have to
manually restart to see those changes take effect.

If all goes well... http://127.0.0.1:5000/ should render the basic search page.


## Running the indexing agent.

The indexing agent is responsible for updating the search index as new papers
are published. By default, docker-compose will also start the search index
and a service called [Localstack](https://github.com/localstack/localstack)
that provides a local Kinesis stream for testing/development purposes.

To disable the agent and localstack, just comment out those services in
``docker-compose.yml``.

The agent takes a little longer than the other services to start. Early in the
startup, you'll see something like:

```bash
agent            | application 12/Apr/2018:15:43:13 +0000 - search.agent.base - None - [arxiv:null] - INFO: "New consumer for MetadataIsAvailable (0)"
agent            | application 12/Apr/2018:15:43:13 +0000 - search.agent.base - None - [arxiv:null] - INFO: "Getting a new connection to Kinesis at https://localstack:4568 in region us-east-1, with SSL verification=False"
agent            | application 12/Apr/2018:15:43:13 +0000 - search.agent.base - None - [arxiv:null] - INFO: "Waiting for MetadataIsAvailable to be available"
agent            | application 12/Apr/2018:15:43:13 +0000 - search.agent.base - None - [arxiv:null] - ERROR: "Waiting for stream MetadataIsAvailable"
```

A little while later, when localstack and the indexing agent are running, you
should see something like:

```bash
agent            | application 12/Apr/2018:15:44:14 +0000 - search.agent.base - None - [arxiv:null] - ERROR: "Failed to get stream while waiting"
agent            | application 12/Apr/2018:15:44:14 +0000 - search.agent.base - None - [arxiv:null] - INFO: "Could not connect to stream; attempting to create"
agent            | application 12/Apr/2018:15:44:14 +0000 - search.agent.base - None - [arxiv:null] - INFO: "Created; waiting for MetadataIsAvailable again"
agent            | application 12/Apr/2018:15:44:14 +0000 - search.agent.base - None - [arxiv:null] - ERROR: "Waiting for stream MetadataIsAvailable"
localstack       | Ready.
agent            | application 12/Apr/2018:15:44:24 +0000 - search.agent.base - None - [arxiv:null] - INFO: "Ready to start"
agent            | application 12/Apr/2018:15:44:24 +0000 - search.agent.base - None - [arxiv:null] - INFO: "Starting processing from position 49583482132750299344823207796409748205413425533752967170 on stream MetadataIsAvailable and shard 0"
```

Note that Kinesis will be mounted locally on port 5586. It will be using SSL,
but with an invalid certificate. You can connect to this local Kinesis using:

```python
import boto3

client = boto3.client(
    'kinesis',
    region_name='us-east-1',
    endpoint_url="https://localhost:5568",
    aws_access_key_id='foo',
    aws_secret_access_key='bar',
    verify=False
)
```

To verify that the agent is working correctly, try adding some records to
the stream.

```python
import json

to_index = [
    "1712.04442",
    "1511.07473",
    "1604.04228",
    "1403.6219",
    "1404.3450",
    "1703.09067",
    "1408.6682",
    "1607.05107",
    "1509.08727",
    "1710.01597",
    "1708.07156",
    "1401.1012",
]

for document_id in to_index:
    data = bytes(json.dumps({'document_id': document_id}), encoding='utf-8')
    client.put_record(
        StreamName='MetadataIsAvailable',
        Data=data,
        PartitionKey='0'
    )

```

You should see these records being processed in the agent log output almost
immediately. For example:

```bash
agent            | application 12/Apr/2018:15:49:18 +0000 - search.agent.consumer - None - [arxiv:null] - INFO: "Processing record 49583482484923667520018808447528512983060659815298629634"
agent            | application 12/Apr/2018:15:49:19 +0000 - search.agent.consumer - None - [arxiv:null] - INFO: "Processing record 49583482484923667520018808447529721908880274444473335810"
agent            | application 12/Apr/2018:15:49:20 +0000 - search.agent.consumer - None - [arxiv:null] - INFO: "Processing record 49583482484923667520018808447530930834699889073648041986"
agent            | application 12/Apr/2018:15:49:20 +0000 - search.agent.consumer - None - [arxiv:null] - INFO: "Processing record 49583482484923667520018808447532139760519503702822748162"
agent            | application 12/Apr/2018:15:49:21 +0000 - search.agent.consumer - None - [arxiv:null] - INFO: "Processing record 49583482484923667520018808447533348686339118400716931074"
agent            | application 12/Apr/2018:15:49:22 +0000 - search.agent.consumer - None - [arxiv:null] - INFO: "Processing record 49583482484923667520018808447534557612158733029891637250"
agent            | application 12/Apr/2018:15:49:23 +0000 - search.agent.consumer - None - [arxiv:null] - INFO: "Processing record 49583482484923667520018808447535766537978347659066343426"
agent            | application 12/Apr/2018:15:49:24 +0000 - search.agent.consumer - None - [arxiv:null] - INFO: "Processing record 49583482484923667520018808447536975463797962288241049602"
agent            | application 12/Apr/2018:15:49:24 +0000 - search.agent.consumer - None - [arxiv:null] - INFO: "Processing record 49583482484923667520018808447538184389617576917415755778"
agent            | application 12/Apr/2018:15:49:25 +0000 - search.agent.consumer - None - [arxiv:null] - INFO: "Processing record 49583482484923667520018808447539393315437191546590461954"
agent            | application 12/Apr/2018:15:49:25 +0000 - search.agent.consumer - None - [arxiv:null] - INFO: "Processing record 49583482484923667520018808447540602241256806175765168130"
agent            | application 12/Apr/2018:15:49:25 +0000 - search.agent.consumer - None - [arxiv:null] - INFO: "Processing record 49583482484923667520018808447541811167076420804939874306"
```

## Deploying static assets to S3

Assets in search/static can be deployed to S3 using the included
``upload_static_assets.py`` script that leverages the ``Flask-S3 plugin``
<https://flask-s3.readthedocs.io/en/latest/>`_. Note that this requires AWS
credentials that have appropriate permissions for the specified bucket.

To enable the S3-based URLs for the static assets in the templates, simply
set ``FLASKS3_ACTIVE=1`` when starting the Flask dev server.

## Testing & quality

Install testing tools with...

```bash
pipenv install --dev
```

### Test suite
Run the main test suite with...

```bash
pipenv run nose2 --with-coverage
```

To include integration tests, the environment variable ``WITH_INTEGRATION``.
E.g.

```bash
WITH_INTEGRATION=1 pipenv run nose2 --with-coverage
```

### Static checking
Goal: zero errors/warnings.

Use `# type: ignore` to disable mypy messages that do not reveal actual
programming errors, and that are impractical to fix. If ignoring without
verifying, insert a `# TODO: recheck`.

If there is an active `mypy` GitHub issue (i.e. it's a bug/limitation in mypy)
relevant to missed check, link that for later follow-up.

```bash
pipenv run mypy -p search | grep -v "test.*" | grep -v "defined here"
```

Note that we filter out messages about test modules, and messages about a known
limitation of mypy related to ``dataclasses`` support.

### Documentation style
Goal: zero errors/warnings.

```bash
pipenv run pydocstyle --convention=numpy --add-ignore=D401 search
```

### Linting
Goal: 9/10 or better.

```bash
pipenv run pylint search
```

## Documentation

The latest version of the documentation is available at
https://cul-it.github.com/arxiv-search.

The source files for the arXiv search service documentation is located in
[``docs/``](docs/).

To build the service documentation locally:

```bash
cd docs
pip install -r requirements.txt
make [format]
```

where [format] can be ``html``, ``latexpdf``. See the ``Sphinx documentation
<http://www.sphinx-doc.org/en/master/>`_.
