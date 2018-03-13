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
pip install -r requirements/dev.txt
FLASK_APP=app.py FLASK_DEBUG=1 ELASTICSEARCH_HOST=127.0.0.1 python create_index.py
FLASK_APP=app.py FLASK_DEBUG=1 ELASTICSEARCH_HOST=127.0.0.1 python populate_test_metadata.py
```

``populate_test_metadata.py`` without parameters populate the index with the
list of papers defined in ``tests/data/sample.json``. It take several minutes
to run. Individual paper IDs may be specified with the ``--paper_id``
parameter.

### Flask dev server

You can spin up the search app directly. You may want to do this in a
virtualenv.

```bash
pip install -r requirements/dev.txt
FLASK_APP=app.py FLASK_DEBUG=1 ELASTICSEARCH_HOST=127.0.0.1 flask run
```
This will monitor any of the Python bits for changes and restart the server.
Unfortunately static files and templates are not monitored, so you'll have to
manually restart to see those changes take effect.

If all goes well... http://127.0.0.1:5000/ should render the basic search page.

## Testing & quality

Install testing tools with...

```bash
pip install -r requirements/test.txt
```

### Test suite
Run the main test suite with...

```bash
nose2 --with-coverage
```

### Static checking
Goal: zero errors/warnings.

Use `# type: ignore` to disable mypy messages that do not reveal actual
programming errors, and that are impractical to fix. If ignoring without
verifying, insert a `# TODO: recheck`.

If there is an active `mypy` GitHub issue (i.e. it's a bug/limitation in mypy)
relevant to missed check, link that for later follow-up.

```bash
mypy -p search
```

### Documentation style
Goal: zero errors/warnings.

```bash
pydocstyle --convention=numpy --add-ignore=D401 search
```

### Linting
Goal: 9/10 or better.

```bash
pylint search
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
