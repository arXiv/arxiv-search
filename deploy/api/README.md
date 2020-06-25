# Deployment Instructions for search-api

To install `search-api` to the development namespace in the kubernetes cluster:

```bash
helm install ./ --set=image.tag=some_tag \
  --tiller-namespace=development --namespace=development  \
  --set=ingress.host=development.arxiv.org \
  --set=elasticsearch.host=foo.es.amazonaws.com \
  --set=elasticsearch.index=arxiv0.3 \
  --set=scaling.replicas=2
```


Notes:
- `image.tag`: this refers to the tag in [dockerhub](https://hub.docker.com/repository/docker/arxiv/search-api)
- `elasticsearch.host`: this is the hostname of our Elasticsearch endpoint. We have provisioned it in AWS.
- `elasticsearch.index`: this is the index identifier. As of this writing, `arxiv0.3` is the index associated with development.
