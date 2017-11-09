# arxiv-search

## Development quickstart

A ``docker-compose.yml`` configuration is included in the root of this
repository. It will start elasticsearch, using data in ``tests/data/es``,
and the search application.

```bash
docker-compose build
docker-compose up
```

The build step will take a little while to complete the first time around.

This uses ``Dockerfile-dev``, and mounts ``schema/``, ``search/``, ``tests/``,
and ``mappings/``.

This is mainly good for things that don't involve tearing down and rebuilding
the index. If you want to start up ES outside of the compose context, you can
use:

```bash
docker run -p 9200:9200 \
    -e "http.host=0.0.0.0" \
    -e "transport.host=127.0.0.1" \
    -v "$PWD/tests/data/es:/usr/share/elasticsearch/data" \
    docker.elastic.co/elasticsearch/elasticsearch:5.5.3
```
