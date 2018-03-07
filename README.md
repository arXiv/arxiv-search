# arxiv-search

## Testing & quality

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
mypy --ignore-missing-imports -p search
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

- Main service documentation: ``docs/``
- OpenAPI Documentation: [``api/search.yaml``](api/search.yaml)
- JSON Schema: [``schema/``](schema)
- Elasticsearch mappings: [``mappings/``](mappings)

To build the service documentation:

```bash
cd docs
pip install -r requirements.txt
make [format]
```

where [format] can be ``html``, ``latexpdf``. See the ``Sphinx documentation
<http://www.sphinx-doc.org/en/master/>`_.


## Development quickstart

### Running Elasticsearch

```bash
docker build -t "arxivsearch_elasticsearch" -f ./Dockerfile-elasticsearch .
docker run -it -e "http.host=0.0.0.0" -e "transport.host=127.0.0.1" \
  -p 9200:9200 -p 9300:9300 \
  arxivsearch_elasticsearch
```

### Alternatively: Running Elasticsearch with Kibana
**TODO::** docker-compose version
```bash
docker-compose up
```
Kibana will be available at http://127.0.0.1:5601/

### Create & populate the index

```bash
pip install -r requirements/dev.txt
FLASK_APP=app.py FLASK_DEBUG=1 ELASTICSEARCH_HOST=127.0.0.1 python create_index.py
FLASK_APP=app.py FLASK_DEBUG=1 ELASTICSEARCH_HOST=127.0.0.1 python populate_test_metadata.py
```

``populate_test_metadata.py`` without parameters populate the index with the
list of papers defined in ``tests/data/sample.json``. It take several minutes
to run. Individual paper IDs may be specified with the ``--paper_id``
parameter.

You'll need to do this any time you restart ES.

### Flask dev server

You can run the search app directly. Using virtualenv:

```bash
virtualenv ~/.venv/arxiv-search
source ~/.venv/arxiv-search/bin/activate
cd /wherever/you/put/arxiv-search
pip install -r requirements/dev.txt
FLASK_APP=app.py FLASK_DEBUG=1 ELASTICSEARCH_HOST=127.0.0.1 flask run
```

This will monitor any of the Python bits for changes and restart the server.
Unfortunately static files and templates are not monitored, so you'll have to
manually restart to see those changes take effect.

If all goes well... http://127.0.0.1:5000/ should render the basic search page.

## Concurrent populate

```bash
export SHARDS=4
mkdir /tmp/to_index
python shard_ids_for_index.py -l arxiv_id_dump.txt -n ${SHARDS} -o /tmp/to_index
for i in `seq 1 ${SHARDS}`; do
    docker run -d --network=arxivsearch_es_stack \
        -v /tmp/to_index:/to_index \
        -e ELASTICSEARCH_HOST=elasticsearch \
        -e METADATA_ENDPOINT="https://server-${i}.foo.org/metadata/" \
        arxiv/search-index /to_index/shard_${i}.txt;
done
```
